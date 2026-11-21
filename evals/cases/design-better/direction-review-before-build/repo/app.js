// Kade Street shifts: shows the signed-in person's shifts, and the whole rota for managers.
// Data comes from shifts.json, exported nightly from the scheduling system.

const state = { data: null, personId: "lena" };

const dayFormat = new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long" });

function person(id) {
  return state.data.staff.find((p) => p.id === id);
}

function describeShift(shift) {
  const date = dayFormat.format(new Date(shift.date + "T00:00:00"));
  return { when: `${date}, ${shift.start} to ${shift.end}`, where: `${shift.station}, Kade Street` };
}

function shiftItem(shift, showName) {
  const item = document.createElement("li");
  item.className = "shift";
  item.dataset.shiftId = shift.id;
  const text = describeShift(shift);
  const when = document.createElement("div");
  when.className = "when";
  when.textContent = showName ? `${person(shift.staffId).name}: ${text.when}` : text.when;
  const where = document.createElement("div");
  where.className = "where";
  where.textContent = text.where;
  item.append(when, where);
  return item;
}

function render() {
  const me = person(state.personId);
  const mine = state.data.shifts.filter((s) => s.staffId === me.id);
  const list = document.getElementById("my-shifts");
  list.replaceChildren(...mine.map((s) => shiftItem(s, false)));
  if (mine.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "You have no shifts this week.";
    list.append(empty);
  }

  const isManager = me.role === "Store manager";
  document.getElementById("rota-section").hidden = !isManager;
  if (isManager) {
    document.getElementById("rota").replaceChildren(...state.data.shifts.map((s) => shiftItem(s, true)));
  }
}

function fillPeople() {
  const select = document.getElementById("person");
  for (const p of state.data.staff) {
    const option = document.createElement("option");
    option.value = p.id;
    option.textContent = `${p.name} (${p.role})`;
    select.append(option);
  }
  select.value = state.personId;
  select.addEventListener("change", () => {
    state.personId = select.value;
    render();
  });
}

fetch("shifts.json")
  .then((response) => response.json())
  .then((data) => {
    state.data = data;
    fillPeople();
    render();
  });
