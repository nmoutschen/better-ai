# Kade Street shifts

Staff app for Molen Coffee's Kade Street store. Baristas see their week; the store manager also sees the whole rota.

Run it with `python3 -m http.server 8000` in this folder and open http://localhost:8000. The "Signed in as" menu
stands in for the login of the real deployment.

`shifts.json` is exported nightly from the scheduling system. Swaps in it have a status: `offered` (waiting for a
colleague), `taken` (a colleague took it, waiting for the manager), `approved` or `declined`.

The design language is `tokens.css`.
