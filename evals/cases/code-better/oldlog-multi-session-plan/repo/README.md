# services

Request handlers for the back office, one module per service in `services/`.

Logging: `oldlog` is deprecated. Services use the standard `logging` module with a module logger,
`logger = logging.getLogger(__name__)`, and keep the same messages and levels.

Run the tests with `python -m unittest discover tests`.
