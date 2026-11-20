const label = (p) => p.charAt(0).toUpperCase() + p.slice(1);
const time = (iso) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

fetch("tickets.json")
  .then((response) => response.json())
  .then((tickets) => {
    document.getElementById("count").textContent = `${tickets.length} tickets`;
    document.getElementById("rows").innerHTML = tickets
      .map(
        (t) => `<tr>
          <td>#${t.id}</td>
          <td>${t.subject}</td>
          <td class="secondary">${t.customer}</td>
          <td><span class="badge ${t.priority}">${label(t.priority)}</span></td>
          <td class="secondary">${t.channel}</td>
          <td class="secondary">${time(t.created)}</td>
          <td>${t.assignee ?? "Unassigned"}</td>
        </tr>`,
      )
      .join("");
  });
