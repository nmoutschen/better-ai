// Membership sign-up: marks each invalid field in red, then shows the welcome message.

const rules = {
  "full-name": (value) => value.trim().length >= 2,
  email: (value) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value),
  phone: (value) => /^\+?[\d\s]{9,15}$/.test(value),
  "birth-date": (value) => /^\d{2}\/\d{2}\/\d{4}$/.test(value),
  plan: (value) => value !== "",
  password: (value) => value.length >= 8,
};

document.getElementById("signup").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.target;
  let valid = true;
  for (const [name, check] of Object.entries(rules)) {
    const field = form.elements[name];
    const ok = check(field.value);
    field.classList.toggle("invalid", !ok);
    if (!ok) valid = false;
  }
  if (!valid) return;
  form.hidden = true;
  document.getElementById("done").hidden = false;
});
