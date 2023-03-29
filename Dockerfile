FROM python:3.11.2-alpine

# Setup
WORKDIR /app
COPY requirements.txt .
COPY server.py .

RUN pip install --no-cache-dir -r requirements.txt

# Create the database
VOLUME /data
ENV SCAR_DB_PATH="/data/whitelist.sqlite"
# RUN python server.py create-db --db-path $SCAR_DB_PATH

# Run the server
CMD ["python", "./server.py", "run", "--db-path", "/data/whitelist.sqlite", "--auto-create-db"]
