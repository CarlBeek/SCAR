import csv
import click
import json
import re
import sqlite3
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

def verify_table_exists(db_path: str) -> bool:
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    result = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whitelist'")
    if len(result.fetchall()) != 1:
        click.echo('Error: The database schema is incorrect. Run the create-db to create a new database.')
        sys.exit()

def insert_whitelist_record(connection: sqlite3.Connection, address: str, nonce: str, start_time: str, end_time: str) -> None:
    cursor = connection.cursor()
    cursor.execute(
        '''INSERT OR IGNORE INTO whitelist (address, nonce, start_time, end_time)
           VALUES (?, ?, ?, ?)''',
        (address, nonce, start_time, end_time)
    )
    connection.commit()

def is_valid_eth_address(address: str) -> bool:
    pattern = r'^0x[0-9a-fA-F]{40}$'
    return bool(re.match(pattern, address))


def add_from_csv(csv_file: str, db_path: str) -> None:
    connection = sqlite3.connect(db_path)
    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            project_name = row['Response 1'].strip()
            address = row['Response 2'].strip()
            backup_address = row['Response 3'].strip()
            start_time = row['Start Date & Time']
            end_time = row['End Date & Time']

            start_time_utc = datetime.strptime(start_time, '%Y-%m-%d %I:%M %p').strftime('%Y-%m-%dT%H:%M:%SZ')
            end_time_utc = datetime.strptime(end_time, '%Y-%m-%d %I:%M %p').strftime('%Y-%m-%dT%H:%M:%SZ')

            nonce = '0x4000'

            if not (is_valid_eth_address(address) and is_valid_eth_address(backup_address)):
                click.echo(f"Warning: Invalid Ethereum address '{address}' found in CSV. Please check with {project_name}")
            else:
                insert_whitelist_record(connection, address, nonce, start_time_utc, end_time_utc)
                insert_whitelist_record(connection, backup_address, nonce, start_time_utc, end_time_utc)


def get_valid_nonce(cursor: sqlite3.Cursor, address: str) -> str:
    result = cursor.execute(
        "SELECT nonce, start_time, end_time FROM whitelist WHERE UPPER(address) LIKE UPPER('%s')" % address)
    row = result.fetchone()
    if row is not None:
        nonce, start_time, end_time = row
        now = datetime.utcnow().isoformat()
        if start_time <= now <= end_time:
            return nonce
    return '0x0'


# Define the HTTP request handler
class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.db_path = kwargs.pop("db_path")
        super().__init__(*args, **kwargs)

    def do_POST(self) -> None:
        # Connect to the database
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

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
        self.wfile.write(json.dumps({'jsonrpc': '2.0', 'id': 1,'result': nonce}).encode())


@click.command()
@click.option('--db-path', type=str, default='./whitelist.sqlite', help='Path to the SQLite database.')
def create_db(db_path: str):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS whitelist (
            address TEXT PRIMARY KEY,
            nonce TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        )'''
    )

@click.command()
@click.option('--csv-file', type=str, default='events-export.csv', help='Path to the Calendly CSV file.')
@click.option('--db-path', type=str, default='./whitelist.sqlite', help='Path to the SQLite database.')
def import_csv(csv_file: str, db_path: str) -> None:
    verify_table_exists(db_path)
    add_from_csv(csv_file, db_path)
    click.echo('Imported records from CSV file.')


@click.command()
@click.option('--port', type=int, default=8000, help='Port for the HTTP server to listen on.')
@click.option('--db-path', type=str, default='./whitelist.sqlite', help='Path to the SQLite database.')
def main(port: int, db_path: str) -> None:
    verify_table_exists(db_path)
    server = HTTPServer(('', port), lambda *args, **kwargs: RequestHandler(*args, db_path=db_path, **kwargs))
    click.echo(f'Starting server on port {port}...')
    server.serve_forever()

if __name__ == '__main__':
    cli = click.Group()
    cli.add_command(main, name='run')
    cli.add_command(create_db, name='create-db')
    cli.add_command(import_csv, name='import-csv')
    cli(auto_envvar_prefix='SCAR')
