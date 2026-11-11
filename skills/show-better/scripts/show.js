
(() => {
  const pages = [...document.querySelectorAll(".page")];  // pages[0] is the cover
  const n = pages.length - 1;
  if (n < 2) return;
  const root = document.documentElement, ctrl = document.querySelector(".controls");
  const prev = ctrl.querySelector(".prev"), next = ctrl.querySelector(".next"), pos = ctrl.querySelector(".pos");
  const all = ctrl.querySelector(".all"), dots = ctrl.querySelector(".dots");
  const links = [...document.querySelectorAll("nav.toc a")];
  dots.innerHTML = pages.slice(1).map(() => "<span></span>").join("");
  let i = Math.max(0, pages.findIndex(p => p.id && "#" + p.id === location.hash));
  function show(k, focus) {
    i = Math.min(Math.max(k, 0), n);
    pages.forEach((p, j) => p.classList.toggle("current", j === i));
    root.classList.toggle("on-cover", i === 0);
    [...dots.children].forEach((d, j) => d.classList.toggle("on", j < i));
    prev.disabled = i === 0; next.disabled = i === n;
    next.textContent = i === 0 ? "Start →" : "Next →";
    pos.textContent = i === 0 ? `${n} panels` : `${i} / ${n}`;
    history.replaceState(null, "", i === 0 ? location.pathname : "#" + pages[i].id);
    window.scrollTo(0, 0);
    if (focus) pages[i].querySelector("h1, h2").focus({ preventScroll: true });
  }
  function paged(on) {
    root.classList.toggle("paged", on);
    all.textContent = on ? "Show all panels" : "One panel at a time";
    if (on) show(i); else root.classList.remove("on-cover");
  }
  prev.onclick = () => show(i - 1, true);
  next.onclick = () => show(i + 1, true);
  all.onclick = () => paged(!root.classList.contains("paged"));
  document.querySelector(".slim a").onclick = e => { e.preventDefault(); show(0, true); };
  links.forEach((a, k) => a.onclick = e => { if (root.classList.contains("paged")) { e.preventDefault(); show(k + 1, true); } });
  document.addEventListener("keydown", e => {
    if (!root.classList.contains("paged") || e.target.closest("input, textarea, summary")) return;
    // Space pages forward and Shift+Space back, except on a focused button, which Space already presses.
    const space = e.key === " " && !e.target.closest("button, a");
    if (e.key === "ArrowRight" || e.key === "PageDown" || (space && !e.shiftKey)) { e.preventDefault(); show(i + 1, true); }
    if (e.key === "ArrowLeft" || e.key === "PageUp" || (space && e.shiftKey)) { e.preventDefault(); show(i - 1, true); }
  });
  paged(true);
})();
