# (SCAR) Special Contributions Artificial RPC

A tool that mimics an Ethereum Execution RPC endpoint in order to implement Special Contributions to the Ethereum KZG Ceremony without having to change the [Sequencer Code](https://github.com/ethereum/kzg-ceremony-sequencer), nor that of the [clients interacting with it](https://github.com/ethereum/kzg-ceremony#client-implementations).


## What it does

It replaces the Ethereum RPC endpoint that the sequencer normally talks to so that we can effectively only allow certain addresses to contribute at certain times, which is the functionality required for the Special Contribution period of the KZG Ceremony.

SCAR maintains a database of whitelisted addresses and time-span they are whitelisted for and returns a specified nonce if an address is in the DB and has a valid time-stamp, otherwise 0. This way, we repurpose the existing sequencer logic for only allowing people to log-in when their nonce is "high enough" and use it to allow or deny whitelisted participants.

## Rationale

The primary design goal was to require as few changes to the existing code-bases as possible when supporting Special Contributions, and this method doesn't require any other changes.

## Running it

Install requirements:

```bash
pip3 install -r requirements.txt
```

Create the DB:

```bash
python server.py create-db
```

Import Calendly CSV into whitelist DB:

```bash
python server.py import-csv --csv-file ./path/to/events-export.csv
```

Run the server:

```bash
python server.py run
```
