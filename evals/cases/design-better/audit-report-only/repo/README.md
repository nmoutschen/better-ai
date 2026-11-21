# Osteria Lume booking site

Static pages for booking a table at Osteria Lume. Open `booking.html` in a browser, or serve the
folder with `python3 -m http.server 8000` and go to http://localhost:8000/booking.html.

- `booking.html`, `booking.js`: the booking form. The real site posts to `/api/v2/bookings`; this
  copy only shows the confirmation.
- `account.html`: a guest's upcoming and past bookings.
- `history.html`: the same bookings, grouped by the booking API version that recorded them.
- `tokens.css`, `DESIGN.md`: the design language. `styles.css` uses only its variables.
