import click
import json
import sqlite3
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

def get_db_cursor(path: str) -> sqlite3.Cursor:
    connection = sqlite3.connect(path)
    return connection.cursor()

def create_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS whitelist (
            address TEXT PRIMARY KEY,
            nonce TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        )'''
    )

def check_table_exists(cursor: sqlite3.Cursor) -> bool:
    result = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whitelist'")
    return len(result.fetchall()) == 1


def get_valid_nonce(cursor: sqlite3.Cursor, address: str) -> int:
    result = cursor.execute(
        "SELECT nonce, start_time, end_time FROM whitelist WHERE UPPER(address) LIKE UPPER('%s')" % address)
    row = result.fetchone()
    if row is not None:
        nonce, start_time, end_time = row
        now = datetime.utcnow().isoformat()
        if start_time <= now <= end_time:
            return nonce
    return 0


# Define the HTTP request handler
class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.db_path = kwargs.pop("db_path")
        super().__init__(*args, **kwargs)

    def do_POST(self) -> None:
        # Connect to the database
        cursor = get_db_cursor(self.db_path)

        # Read the request body as JSON
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length).decode()
        request_data = json.loads(request_body)

        # Sanity check on request type
        if not request_data.get('method') == 'eth_getTransactionCount':
            self.send_response(404)
            self.end_headers()
            return

        # Extract the number from the JSON request data
        params = request_data.get('params')
        address = params[0]
        block = params[1]

        # If the address is not provided, return a 400 status code
        if not address:
            self.send_response(400)
            self.end_headers()
            return

        # Look up the nonce in the database
        nonce = get_valid_nonce(cursor, address)

        # Return nonce as json
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'jsonrpc': '2.0', 'id': 1,'result': hex(nonce)}).encode())

@click.command()
@click.option('--port', type=int, default=8000, help='Port for the HTTP server to listen on.')
@click.option('--db-path', type=str, default='./whitelist.sqlite', help='Path to the SQLite database.')
@click.option('--create-db', is_flag=True, help='Create the database if it does not exist.')
def main(port: int, db_path: str, create_db: bool) -> None:
    cursor = get_db_cursor(db_path)
    if create_db:
        create_table(cursor)
    elif not check_table_exists(cursor):
        click.echo('Error: The database schema is incorrect. Use --create-db to create a new database.')
        return

    server = HTTPServer(('', port), lambda *args, **kwargs: RequestHandler(*args, db_path=db_path, **kwargs))
    click.echo(f'Starting server on port {port}...')
    server.serve_forever()

if __name__ == '__main__':
    main(auto_envvar_prefix='SCAR')
