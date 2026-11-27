# Design: <short name of the change>

Request: <link to the change folder, or the request in words>
Requirements: <agreed requirement IDs, observable scenarios, constraints and sources>
Diagrams: <link to design JSON>

## Goals and non-goals

- Goal: <what the change must achieve>
- Non-goal: <what is outside this change>

## Context

<System in scope, its users, external systems and constraints relevant to the change.>

## Containers and components

<Design JSON reference to the affected boxes and relationships, with their responsibilities before and after.>

## Main flows

### <Flow name>

<Design JSON flow reference, with the main path and relevant failure paths.>

## Data

- <Data model, schema or file format>: <changes and what happens to existing data>

## Perspectives

| Perspective | Applies | Why |
|---|---|---|
| <perspective or repo standard> | <yes or no> | <reason based on what the change touches> |

## Decisions summary

- <Choice>: <recommendation> (<link to the decision record, once written>)
  - Drivers: <requirement IDs>
  - Rejected: <alternative>: <reason>
  - Drawback: <main cost, risk or maintenance burden of the chosen option>
  - Assumes: <what must stay true for this choice to hold>, <confirmed by a proof of concept, with what was observed; contradicted, with what was observed; or untested>

## Departures from existing patterns

- <Pattern not followed>: <why>

## Unresolved questions

- <Question>: <what the answer would change>
