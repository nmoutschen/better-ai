# Spec: <short name of the change>

<HOW TO FILL THIS IN — you write the records of `spec.jsonl`, not this file. Delete this block when done.
- Conventions: START each record with `type`, `at` (UTC, ending in Z) and `by` (your agent name). WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the schema does not name is an error. WRITE one record per line, as ASCII JSON, and the record a pointer names before the pointer. AFTER each write, RUN `python3 <skill dir>/scripts/schema.py check <the file>` and FIX what it reports. `schemas/spec.schema.json` is the authority for the fields.
- One `spec` record per requirement. LIST every MUST and MUST NOT the design and its decisions state or imply, including the error and edge cases they leave open. WRITE `statement` as one EARS statement, with concrete values: "When <trigger>, the <system> shall <response>", "If <unwanted condition>, then the <system> shall <response>", "While <state>, …", "Where <feature>, …" or "The <system> shall <response>".
- Most costly to miss first. No reasons in `statement`: `source` carries them. A MUST NOT in positive form where one exists, and every MUST NOT with a check. KEEP a requirement only if its absence would change what is built or checked.
- GIVE each requirement its `source`, THEN CHECK the other direction: every decision and stated behaviour in the design has a requirement; WRITE each one that has none as an `unlinked` record.
- One `gap` record per gap, with `if_wrong`: what the user would see. A gap that is asked or answered points to its decision in `decisions.jsonl` and holds no `choice`; an assumed one holds `choice` and no `decision`.
- Save it where step 7 of the design mode says. CHANGE a requirement only as the general rule Ask the user of SKILL.md says, and REVISE its line in place.>

The requirements, `spec.jsonl`: one line per source.

{"type": "spec", "at": "<UTC time>", "by": "<agent>", "id": "S<n>", "statement": "<EARS statement>", "source": {"type": "design", "section": "<design section>"}, "checked_by": "<test name, scenario run, or code review>"}
{"type": "spec", "at": "<UTC time>", "by": "<agent>", "id": "S<n>", "statement": "<EARS statement>", "source": {"type": "request", "sentence": "<the user's sentence>"}, "checked_by": "<check>"}
{"type": "spec", "at": "<UTC time>", "by": "<agent>", "id": "S<n>", "statement": "<EARS statement>", "source": {"type": "decision", "decision": "D<n>"}, "checked_by": "<check>"}
{"type": "spec", "at": "<UTC time>", "by": "<agent>", "id": "S<n>", "statement": "<EARS statement>", "source": {"type": "requirement", "requirement": "<requirement id>"}, "checked_by": "<check>"}

The gaps: one asked, one assumed, one answered.

{"type": "gap", "at": "<UTC time>", "by": "<agent>", "id": "G<n>", "text": "<the gap>", "status": "asked", "decision": "D<n>", "if_wrong": "<what the user would see>"}
{"type": "gap", "at": "<UTC time>", "by": "<agent>", "id": "G<n>", "text": "<the gap>", "status": "assumed", "choice": "<what you chose>", "if_wrong": "<what the user would see>"}
{"type": "gap", "at": "<UTC time>", "by": "<agent>", "id": "G<n>", "text": "<the gap>", "status": "answered", "decision": "D<n>", "if_wrong": "<what the user would see>"}

The design items with no requirement:

{"type": "unlinked", "at": "<UTC time>", "by": "<agent>", "item": "<decision or behaviour>", "why": "<why it needs none, or gap>"}

`python3 <skill dir>/scripts/architect.py specs <folder> --out <spec location>/specs.md` writes the table a person reads, marked as generated, in a repo with no spec format or tool.
