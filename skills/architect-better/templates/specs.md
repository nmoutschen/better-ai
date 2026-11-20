# Spec: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- List every MUST and MUST NOT the design and its decisions state or imply, including the error and edge cases they leave open.
- One EARS statement per requirement, with concrete values: "When <trigger>, the <system> shall <response>", "If <unwanted condition>, then the <system> shall <response>", "While <state>, …", "Where <feature>, …" or "The <system> shall <response>".
- Most costly to miss first. No reasons: the Source column carries them. A MUST NOT in positive form where one exists, and every MUST NOT with a check. Keep a requirement only if its absence would change what is built or checked.
- Link each requirement to its source: a design section, a decision ID or a request sentence. THEN check the other direction: every decision and stated behaviour in the design has a requirement; list the rest under "Design items with no requirement".
- Save it where step 7 of the design mode says. Change a requirement only as the general rule Ask the user of SKILL.md says.>

Goal: <what the user must be able to do, decide or understand once this works>
Design: <path or link to design.md in the change folder>

| ID | Requirement | Source | Checked by |
|---|---|---|---|
| <R1> | <EARS statement> | <design section, decision ID, or request sentence> | <test name, scenario run, or code review> |

## Gaps

- <Gap>: <asked | assumed: <choice>> — if wrong, the user would see: <observable effect>

## Design items with no requirement

- <Decision or behaviour>: <why it needs none, or "gap">
