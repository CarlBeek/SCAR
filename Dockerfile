FROM python:3.11.2-alpine

### Setup
ADD requirements.txt .
ADD server.py .

RUN pip install -r requirements.txt

### Run

VOLUME /data
ENV SCAR_DB_PATH="/data/whitelist.sqlite"
ENV SCAR_CREATE_DB=1

CMD ["python", "./server.py"]
