# Orchard

A small service for tracking orchard harvests.

## Running the service

    pip install -r requirements.txt
    python -m orchard

## Running the tests

The tests live in `tests/` and use pytest. They cover the harvest models, the API handlers and the CSV import.

    pip install -r requirements.txt
    python -m pytest tests
