# Harbour Desk

Internal support tool for the Harbour invoicing product. Support agents work tickets from email, chat and phone.

Run it locally with `python3 -m http.server 8000` and open http://localhost:8000/.

- `index.html` and `app.js`: the ticket list, every ticket in a table.
- `tickets.json`: a snapshot of this morning's queue, used until the API is wired in.
- `DESIGN.md` and `tokens.css`: the design language. Use its tokens and components on every page.

First-reply targets by priority: urgent 30 minutes, high 2 hours (1 hour on Enterprise), normal 8 hours, low 24 hours.
