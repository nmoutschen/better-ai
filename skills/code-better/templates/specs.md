# Spec: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- List every MUST and MUST NOT the design states or implies, or the request where there is no design, including the error and edge cases it leaves open.
- One EARS statement per requirement, with concrete values: "When <trigger>, the <system> shall <response>", "If <unwanted condition>, then the <system> shall <response>", "While <state>, …", "Where <feature>, …" or "The <system> shall <response>".
- Most costly to miss first. No reasons: the Source column carries them. A MUST NOT in positive form where one exists, and every MUST NOT with a check. Keep a requirement only if its absence would change what is built or checked.
- Link each requirement to its source. THEN check the other direction: every decision and stated behaviour in the design has a requirement; list the rest under "Design items with no requirement".
- Save it as .code/<change>/specs.md. Change a requirement only as the general rule Send up of SKILL.md says.>

Goal: <what the user must be able to do, decide or understand once this works>
Design: <path or link to the design, or "request" with its text>
Mode: <feature | bug fix | refactor | tests | coordinate>

| ID | Requirement | Source | Checked by |
|---|---|---|---|
| <R1> | <EARS statement> | <design section, recorded decision, or request> | <test name, scenario run, or code review> |

## Gaps

- <Gap>: <sent up | assumed: <choice>> — if wrong, the user would see: <observable effect>

## Design items with no requirement

- <Decision or behaviour>: <why it needs none, or "gap">
