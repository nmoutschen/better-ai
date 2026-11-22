# Spec: <short name of the change>

<HOW TO FILL THIS IN — you write the `spec`, `gap` and `unlinked` records, not this file. Delete this block when done.
- Conventions: WRITE each line below as the JSON on the standard input of the command in SKILL.md, without `at`, `by` and `id`. WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the record does not name is an error. WRITE the record a pointer names before the pointer.
- One `spec` record per requirement. LIST every MUST and MUST NOT the design and its decisions state or imply, including the error and edge cases they leave open. WRITE `statement` as one EARS statement, with concrete values: "When <trigger>, the <system> shall <response>", "If <unwanted condition>, then the <system> shall <response>", "While <state>, …", "Where <feature>, …" or "The <system> shall <response>".
- Most costly to miss first. No reasons in `statement`: `source` carries them. A MUST NOT in positive form where one exists, and every MUST NOT with a check. KEEP a requirement only if its absence would change what is built or checked.
- GIVE each requirement its `source`, THEN CHECK the other direction: every decision and stated behaviour in the design has a requirement; WRITE each one that has none as an `unlinked` record.
- One `gap` record per gap, with `if_wrong`: what the user would see. A gap that is asked or answered points to its decision in `decisions.jsonl` and holds no `choice`; an assumed one holds `choice` and no `decision`.
- Save it where step 7 of the design mode says. CHANGE a requirement only as the general rule Ask the user of SKILL.md says, and REVISE its line in place.>

The requirements, `spec.jsonl`: one line per source.

{"type": "spec", "statement": "<EARS statement>", "source": {"type": "design", "section": "<design section>"}, "checked_by": "<test name, scenario run, or code review>"}
{"type": "spec", "statement": "<EARS statement>", "source": {"type": "request", "sentence": "<the user's sentence>"}, "checked_by": "<check>"}
{"type": "spec", "statement": "<EARS statement>", "source": {"type": "decision", "decision": "D<n>"}, "checked_by": "<check>"}
{"type": "spec", "statement": "<EARS statement>", "source": {"type": "requirement", "requirement": "<requirement id>"}, "checked_by": "<check>"}

The gaps: one asked, one assumed, one answered.

{"type": "gap", "text": "<the gap>", "status": "asked", "decision": "D<n>", "if_wrong": "<what the user would see>"}
{"type": "gap", "text": "<the gap>", "status": "assumed", "choice": "<what you chose>", "if_wrong": "<what the user would see>"}
{"type": "gap", "text": "<the gap>", "status": "answered", "decision": "D<n>", "if_wrong": "<what the user would see>"}

The design items with no requirement:

{"type": "unlinked", "item": "<decision or behaviour>", "why": "<why it needs none, or gap>"}

`python3 <skill dir>/scripts/better.pyz specs <unit>` prints the table a person reads, starting with a generated marker, for a repo with no spec format or tool: WRITE it to `<spec location>/specs.md` only if that file is missing or its first line is that marker.
