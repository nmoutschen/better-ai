# Change and spec records

MAKE the change folder with `python3 <skill dir>/scripts/better.pyz create .code/<change> --by <your agent name>`, with the `code` record below on stdin. ADD each requirement, gap and unlinked item with `python3 <skill dir>/scripts/better.pyz add <unit> <type> --by <your agent name>`, its fields as JSON on stdin, where `<unit>` is `.code/<change>` and `<type>` is `spec`, `gap` or `unlinked`. CHANGE one with `python3 <skill dir>/scripts/better.pyz set <unit> <id>`. IF the command refuses a record, FIX the record and RUN it again. IF `design` is an architect folder, the spec is the copy of that folder's spec in the change folder: CHANGE it there with `set`.

- GIVE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field not shown below is an error. ADD the record a pointer names before the pointer.
- ADD one `spec` record per requirement. LIST every MUST and MUST NOT the design states or implies, or the request where there is no design, including the error and edge cases it leaves open. GIVE `statement` as one EARS statement, with concrete values: "When <trigger>, the <system> shall <response>", "If <unwanted condition>, then the <system> shall <response>", "While <state>, …", "Where <feature>, …" or "The <system> shall <response>".
- Most costly to miss first. No reasons in `statement`: `source` carries them. A MUST NOT in positive form where one exists, and every MUST NOT with a check. KEEP a requirement only if its absence would change what is built or checked.
- GIVE each requirement its `source`, THEN CHECK the other direction: every decision and stated behaviour in the design has a requirement; ADD an `unlinked` record for each one that has none.
- ADD one `gap` record per gap, with `if_wrong`: what the user would see. A `gap` that is asked points to its decision record, and holds `answered` instead of `asked` once the user answered; an assumed one holds `choice`.
- WHEN the spec is a copy of an architect folder's spec, NEVER add a gap or a source to it that points to a `decision` record of the change folder: ADD the question as a `decision` record, and once the user has answered, ADD the requirement with source `request` holding the user's words.
- USE a source of type `requirement` only when the spec is a copy of an architect folder's spec: a spec in `.code/<change>/` has no requirement records for it to point to.
- CHANGE a requirement only as the general rule Ask the user of SKILL.md says, and CHANGE it with `set`.

The change, type `code`, given to `create` on stdin, with the design as an architect folder, a file, or the request:

{"type": "code", "goal": "<what the user must be able to do, decide or understand once this works>", "design": {"type": "architect", "folder": "<repo-relative folder>"}, "mode": "<feature | bug fix | refactor | tests | coordinate>"}
{"type": "code", "goal": "<goal>", "design": {"type": "file", "path": "<path of the design>"}, "mode": "<mode>"}
{"type": "code", "goal": "<goal>", "design": {"type": "request", "text": "<the request, verbatim>"}, "mode": "<mode>"}

The requirements, type `spec`: one record per source.

{"type": "spec", "statement": "<EARS statement>", "source": {"type": "design", "section": "<design section>"}, "checked_by": "<test name, scenario run, or code review>"}
{"type": "spec", "statement": "<EARS statement>", "source": {"type": "request", "sentence": "<the user's sentence>"}, "checked_by": "<check>"}
{"type": "spec", "statement": "<EARS statement>", "source": {"type": "decision", "decision": "D<n>"}, "checked_by": "<check>"}
{"type": "spec", "statement": "<EARS statement>", "source": {"type": "requirement", "requirement": "<id of a requirement record>"}, "checked_by": "<check>"}

The gaps: one asked, one assumed.

{"type": "gap", "text": "<the gap>", "status": "asked", "decision": "D<n>", "if_wrong": "<what the user would see>"}
{"type": "gap", "text": "<the gap>", "status": "assumed", "choice": "<what you chose>", "if_wrong": "<what the user would see>"}

The design items with no requirement:

{"type": "unlinked", "item": "<decision or behaviour>", "why": "<why it needs none, or gap>"}
