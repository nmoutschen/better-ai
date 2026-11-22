# Spec: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- SAVE `.code/<change>/code.json`, one JSON record, and `.code/<change>/spec.jsonl`, one record per line, in the formats of `schemas/code.schema.json` and `schemas/spec.schema.json`, which are the authority. IF `design` is an architect folder, the spec is that folder's `spec.jsonl`: UPDATE it there, and WRITE no copy.
- Conventions: START each record with `type`, `at` (UTC, ending in Z) and `by` (your agent name). WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the schema does not name is an error. WRITE one record per line, as ASCII JSON, and the record a pointer names before the pointer. AFTER each write, RUN `python3 <skill dir>/scripts/schema.py check <the file>` and FIX what it reports.
- One `spec` record per requirement. LIST every MUST and MUST NOT the design states or implies, or the request where there is no design, including the error and edge cases it leaves open. WRITE `statement` as one EARS statement, with concrete values: "When <trigger>, the <system> shall <response>", "If <unwanted condition>, then the <system> shall <response>", "While <state>, …", "Where <feature>, …" or "The <system> shall <response>".
- Most costly to miss first. No reasons in `statement`: `source` carries them. A MUST NOT in positive form where one exists, and every MUST NOT with a check. KEEP a requirement only if its absence would change what is built or checked.
- GIVE each requirement its `source`, THEN CHECK the other direction: every decision and stated behaviour in the design has a requirement; WRITE each one that has none as an `unlinked` record.
- One `gap` record per gap, with `if_wrong`: what the user would see. A `gap` that is asked points to its decision in `decisions.jsonl`, and holds `answered` instead of `asked` once the user answered; an assumed one holds `choice`.
- WHEN the spec is an architect folder's `spec.jsonl`, NEVER write a gap or a source in it that points to a decision of `.code/<change>/decisions.jsonl`: RECORD the question in that file, and once the user has answered, WRITE the requirement with source `request` holding the user's words.
- USE a source of type `requirement` only when the spec is an architect folder's `spec.jsonl`: a spec in `.code/<change>/` has no `requirements.jsonl` for it to point to.
- CHANGE a requirement only as the general rule Ask the user of SKILL.md says, and REVISE its line in place.>

Conventions and fields: `schemas/*.schema.json` of this skill.

The change: one JSON record in `code.json`, with the design as an architect folder, a file, or the request.

{"type": "code", "at": "<UTC time>", "by": "<agent>", "goal": "<what the user must be able to do, decide or understand once this works>", "design": {"type": "architect", "folder": "<repo-relative folder>"}, "mode": "<feature | bug fix | refactor | tests | coordinate>"}
{"type": "code", "at": "<UTC time>", "by": "<agent>", "goal": "<goal>", "design": {"type": "file", "path": "<path of the design>"}, "mode": "<mode>"}
{"type": "code", "at": "<UTC time>", "by": "<agent>", "goal": "<goal>", "design": {"type": "request", "text": "<the request, verbatim>"}, "mode": "<mode>"}

The requirements, `spec.jsonl`: one line per source.

{"type": "spec", "at": "<UTC time>", "by": "<agent>", "id": "S<n>", "statement": "<EARS statement>", "source": {"type": "design", "section": "<design section>"}, "checked_by": "<test name, scenario run, or code review>"}
{"type": "spec", "at": "<UTC time>", "by": "<agent>", "id": "S<n>", "statement": "<EARS statement>", "source": {"type": "request", "sentence": "<the user's sentence>"}, "checked_by": "<check>"}
{"type": "spec", "at": "<UTC time>", "by": "<agent>", "id": "S<n>", "statement": "<EARS statement>", "source": {"type": "decision", "decision": "D<n>"}, "checked_by": "<check>"}
{"type": "spec", "at": "<UTC time>", "by": "<agent>", "id": "S<n>", "statement": "<EARS statement>", "source": {"type": "requirement", "requirement": "<requirement id in requirements.jsonl>"}, "checked_by": "<check>"}

The gaps: one asked, one assumed.

{"type": "gap", "at": "<UTC time>", "by": "<agent>", "id": "G<n>", "text": "<the gap>", "status": "asked", "decision": "D<n>", "if_wrong": "<what the user would see>"}
{"type": "gap", "at": "<UTC time>", "by": "<agent>", "id": "G<n>", "text": "<the gap>", "status": "assumed", "choice": "<what you chose>", "if_wrong": "<what the user would see>"}

The design items with no requirement:

{"type": "unlinked", "at": "<UTC time>", "by": "<agent>", "item": "<decision or behaviour>", "why": "<why it needs none, or gap>"}
