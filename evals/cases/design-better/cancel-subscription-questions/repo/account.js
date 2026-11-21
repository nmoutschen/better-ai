// Fills the account page with the signed-in member's data.
const euro = (cents) => `€${(cents / 100).toFixed(0)}`;
const date = (iso) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });

fetch("/api/member", { credentials: "include" })
  .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
  .then((m) => {
    document.getElementById("plan").textContent = `${m.plan.name} · ${euro(m.plan.monthly_cents)} per month`;
    document.getElementById("since").textContent = date(m.joined);
    document.getElementById("next-payment").textContent = `${euro(m.plan.monthly_cents)} on ${date(m.next_payment)}`;
    document.getElementById("home-gym").textContent = m.home_gym;
    document.getElementById("iban").textContent = `SEPA direct debit from ${m.iban_masked}`;
    document.getElementById("name").textContent = m.name;
    document.getElementById("email").textContent = m.email;
    document.getElementById("phone").textContent = m.phone;
  })
  .catch(() => {
    document.querySelector(".account").insertAdjacentHTML(
      "afterbegin",
      '<p class="notice" role="alert">We could not load your account. Refresh the page or try again later.</p>',
    );
  });
