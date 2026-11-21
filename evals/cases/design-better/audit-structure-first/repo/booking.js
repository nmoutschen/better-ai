// Booking form: checks the fields, then holds the table (the real request goes to /api/v2/bookings).

function showBanner(message) {
  const banner = document.getElementById("banner");
  banner.textContent = message;
  banner.hidden = false;
}

function parseDate(text) {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(text.trim());
  if (!match) return null;
  const date = new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1]));
  return isNaN(date.getTime()) ? null : date;
}

function submitBooking() {
  const form = document.getElementById("booking");
  const guests = form.guests.value;
  const date = parseDate(form.date.value);
  const time = form.time.value;
  const name = form.name.value.trim();
  const phone = form.phone.value.replace(/\s+/g, "");

  if (!date || !name || !/^\+?\d{9,12}$/.test(phone)) {
    showBanner("Invalid input");
    return;
  }

  document.getElementById("banner").hidden = true;
  const day = date.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
  document.getElementById("confirmation-text").textContent =
    `A table for ${guests} on ${day} at ${time}, under the name ${name}. We will text ${form.phone.value} to confirm.`;
  document.getElementById("booking-step").hidden = true;
  document.getElementById("confirmation-step").hidden = false;
}
