# Design: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- Write a design only when there is none and the change adds structure, such as a module, data model, dependency or migration. Save it in .code/<change>/design.md.
- Show only the parts the change touches. Follow the codebase's existing patterns; say why where you depart from them.
- Ask the user about each decision, as the general rule Ask the user of SKILL.md says. A gap the design reveals, such as what happens when a step fails halfway, is a gap to ask about, not a design choice.>

Spec: <path or link to the spec>

## Approach

<How the change produces the behaviour in the requirements, in a few sentences.>

## Context (C4 level 1)

<Diagram: the system, its users, and the external systems it talks to. Include only if the change adds or changes one of them.>

## Containers and components (C4 levels 2 and 3)

<Diagram: the containers or components the change adds or changes, and the ones they talk to.>

- <Container or component>: <responsibility, new or changed>

## Main flows

### <Flow name>

<Sequence diagram: the participants and messages of one main flow the change adds or changes, including its main failure path.>

## Data

- <Data model, schema, or file format>: <new or changed fields, and migration of existing data>

## Decisions

### <Decision>

- Chosen: <option>
- Rejected: <options considered>
- Main reason: <tied to the spec or the codebase>
- Main drawback: <cost, risk or maintenance burden of the chosen option>
- Assumes: <what must stay true for this choice to hold>

## Departures from existing patterns

- <Pattern not followed>: <why>

## Gaps found

- <Gap found during design>: <status: asked | assumed | open>
