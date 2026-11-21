# Brief: shift swaps in the Kade Street shifts app

## Goal

Baristas and shift leads can hand a shift they cannot work to a colleague, and the store manager can approve or
decline the swap, without the WhatsApp group and the paper rota on the back-office door.

The operations team wants every swap recorded and approved, so the rota the scheduling system exports is the rota
people actually work.

## Audience

- Who: baristas and shift leads at Kade Street (about 14 people), and the store manager
- Device and input: staff use their own phones, mostly between customers or on a break; the manager uses the
  back-office laptop with a keyboard and mouse
- Conditions: staff have a minute or two; they know their own shifts and their colleagues by first name
- Source: user

## Scenarios

### A barista offers a shift

- Who: Lena Vos, barista
- Comes to: give away her Saturday 12 December shift, 07:00 to 15:00 on the bar, because of a family visit
- Starts at: the app's home screen, signed in as Lena, on her phone
- Done when: her Saturday shift shows that it is offered and waiting for a colleague, and the shift appears for
  her colleagues as one they can take
- Source: user

### A manager approves a swap

- Who: Ruben Claes, store manager
- Comes to: approve the swap in which Tom Peeters takes Sam Okafor's Sunday 13 December shift, 08:00 to 16:00 on
  the bar (Sam's note: "Exam on Monday, need Sunday to study")
- Starts at: the app's home screen, signed in as Ruben, on the back-office laptop
- Done when: the rota shows Tom on the Sunday 13 December 08:00 shift, and the swap no longer waits for Ruben
- Source: user

## Structure

| Page or main part | What it holds | Scenario it serves | Stay, merge or go |
|---|---|---|---|
| Your shifts this week | the signed-in person's shifts, each with its swap status and the way to offer it | A barista offers a shift | stay |
| Shifts you can take | colleagues' offered shifts | A barista offers a shift (its end state) | stay, under "Your shifts" |
| Waiting for your approval | taken swaps, manager only | A manager approves a swap | stay, above the rota |
| Store rota | every shift, manager only | A manager approves a swap (its end state) | stay |

## Content

- Shifts, staff and swaps from shifts.json (exported nightly from the scheduling system)

## Constraints

- Design language: tokens.css (Molen Coffee staff tools)
- No new pages: the app stays one page (source: user)

## Direction

The user chose B: offer a shift from its card in "Your shifts", with an optional note, and approve swaps in a
"Waiting for your approval" list above the rota. They said A hides the offer behind a second "Swap board" page
that staff would not find between customers.

Review of the direction: settled. A reviewer walked both scenarios in B.html on 3 December and confirmed no
finding that stops or slows a scenario; the user accepted B as it is.

## Out of scope

- Notifications to colleagues; the real login

## Assumptions

- Any barista or shift lead at Kade Street may take any offered shift — if wrong, staff would see shifts they are
  not allowed to take
