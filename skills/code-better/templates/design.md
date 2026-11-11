# Design: <short name of the change>

Requirements: <path or link to the requirements>

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
- Alternatives: <options considered>
- Why: <reason, tied to the requirements or the codebase>
- Affects: <behaviour | cost | risk | maintenance>, <how>

## Departures from existing patterns

- <Pattern not followed>: <why>

## Requirement gaps found

- <Gap found during design>: <status: asked | assumed | open>
