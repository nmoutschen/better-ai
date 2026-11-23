# Spec records

ADD each with `python3 <skill dir>/scripts/better.pyz add <unit> <type> --by <your name>`, its fields as JSON on stdin, where `<unit>` is the change folder `.architect/<change>` and `<type>` is `spec`, `gap` or `unlinked`. CHANGE one with `python3 <skill dir>/scripts/better.pyz set <unit> <id>`. Leave out `at`, `by` and `id`: the command adds them. IF the command refuses a record, FIX the record and RUN it again.

- GIVE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the record does not name is an error. ADD the record a pointer names before the pointer.
- ADD one `spec` record per requirement. LIST every MUST and MUST NOT the design and its decisions state or imply, including the error and edge cases they leave open. GIVE `statement` as one EARS statement, with concrete values: "When <trigger>, the <system> shall <response>", "If <unwanted condition>, then the <system> shall <response>", "While <state>, …", "Where <feature>, …" or "The <system> shall <response>".
- Most costly to miss first. No reasons in `statement`: `source` carries them. A MUST NOT in positive form where one exists, and every MUST NOT with a check. KEEP a requirement only if its absence would change what is built or checked.
- GIVE each requirement its `source`, THEN CHECK the other direction: every decision and stated behaviour in the design has a requirement; ADD an `unlinked` record for each one that has none.
- ADD one `gap` record per gap, with `if_wrong`: what the user would see. A gap that is asked or answered points to its `decision` record and holds no `choice`; an assumed one holds `choice` and no `decision`.
- CHANGE a requirement only as the general rule Ask the user of SKILL.md says, and CHANGE its record in place with `set`.

The requirements, type `spec`: one record per source.

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

`python3 <skill dir>/scripts/better.pyz specs <unit>` prints the table a person reads, starting with a generated marker, for a repo with no spec format or tool: write its output to `<spec location>/specs.md` only if that file is missing or its first line is that marker.
