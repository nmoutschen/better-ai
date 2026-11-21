# Spec: <short name of the change>

<HOW TO FILL THIS IN: you write the records of `spec.jsonl`, not this file. Delete this block when done.
- List every MUST and MUST NOT the design and its decisions state or imply, including the error and edge cases they leave open.
- One EARS statement per requirement, with concrete values: "When <trigger>, the <system> shall <response>", "If <unwanted condition>, then the <system> shall <response>", "While <state>, …", "Where <feature>, …" or "The <system> shall <response>".
- Most costly to miss first. No reasons: the source carries them. A MUST NOT in positive form where one exists, and every MUST NOT with a check. Keep a requirement only if its absence would change what is built or checked.
- Link each requirement to its source: a design section, a decision ID, a request sentence or a requirement ID. THEN check the other direction: every decision and stated behaviour in the design has a requirement; record the rest as `unlinked` records.
- Save it where step 7 of the design mode says. Change a requirement only as the general rule Ask the user of SKILL.md says.>

One line of `spec.jsonl` for each requirement:

{"type": "spec", "at": "<UTC time>", "by": "architect", "id": "<S1>", "statement": "<EARS statement>", "source": {"type": "<design | request | decision | requirement>", "<section | sentence | decision | requirement>": "<design section, request sentence, decision ID or requirement ID>"}, "checked_by": "<test name, scenario run, or code review>"}

One line for each gap the design leaves open, and each item with no requirement:

{"type": "gap", "at": "<UTC time>", "by": "architect", "id": "<G1>", "text": "<the gap>", "status": "<asked | assumed>", "decision": "<D1, when asked>", "choice": "<the assumption, when assumed>", "if_wrong": "<what the user would see>"}
{"type": "unlinked", "at": "<UTC time>", "by": "architect", "item": "<decision or behaviour>", "why": "<why it needs none, or gap>"}

`python3 scripts/architect.py specs <folder> --out <spec location>/specs.md` writes the table a person reads, marked as generated, in a repo with no spec format or tool.
