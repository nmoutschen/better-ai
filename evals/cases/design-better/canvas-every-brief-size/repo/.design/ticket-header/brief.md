# Brief: ticket header

## Goal

An agent opening a ticket sees at once who it is from, how urgent it is and how long they have to reply, and can take it.

Fewer missed first-reply targets on Enterprise tickets.

## Audience

- Who: Harbour Desk support agents. The field team works from phones between customer visits; the desk team uses the
  24-inch screens in the office.
- Device and input: mostly phones, 375x760, touch. Sometimes desktop, 1280x800, mouse and keyboard.
- Conditions: a minute or two between visits; they open a ticket from a push notification.
- Source: user, 2026-11-18

## Scenarios

### Take an urgent ticket from a notification

- Who: field agent on a phone
- Comes to: decide whether to take #4821 (Enterprise, High, reply due in 2 h 10 min) now
- Starts at: the ticket page, opened from the notification
- Done when: the ticket is assigned to them
- Source: user

## Structure

| Page or main part | What it holds | Scenario it serves | Stay, merge or go |
|---|---|---|---|
| Ticket header | subject, customer, plan, priority, reply target, Take button | Take an urgent ticket | Stay |

## Versions

- A.html: subject first, then a row of badges and the reply target as text.
- B.html: reply target as a bar above the subject, customer and plan below.
