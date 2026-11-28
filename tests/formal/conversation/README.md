# Formal models of the conversation thread

TLA+ models of how one thread of a live page's conversation changes state when the user and the agent act at the
same time. TLC checks each model against the invariants named in its config.

## Models

- `conversation.tla`: the per-item rules as they were built before this change (page.js `pageThread` and an earlier
  `all_items`, both since replaced by the one thread machine, `pageThreads` and `threads`). `Root = "item"` is the user's own
  comment or message; `Root = "agent"` is a message the agent posted, with each user note an item of its own.
  `CloseAnyTime` is whether the page offers Close on every open thread; `StaleGuard` is whether a status that
  predates the user's latest event is ignored.
- `thread.tla`: the designed thread machine, one state per thread (Your turn, Agent's turn, Done), read from the log
  by one fold. `Root` is `user`, `question` or `report`.

Assumptions (also at the top of each `.tla`): A1 appends are whole and ordered; A2 the agent reads what it was shown
before it acts, and the `read` of its status is the last line it was shown, which `--read` now makes explicit: the
agent passes it (the `_i` of the last line `wait` or `serve` printed, or the number on `pending`'s last line), and the
CLI refuses the status when the user wrote in the thread after that line; A3 the page shows the user the log as it is
when they act. A user acting on an older drawing is not modelled. The runs are bounded by `MaxLog` (and `MaxItems`),
so a pass means no violation within that bound.

## Where the code differs from `thread.tla`

The model is one thread with the events above. The fold in the code (`threads` in `src/better_ai/page/__init__.py`,
`pageThreads` in `page.js`) also handles, outside the model:

- A status with no `read`, from a log written before `read`: it counts as fresh, and a `done` one closes the thread as
  the user's ✓ does (D13). In the model every status has a `read`.
- Reopen: the model offers it only on a done thread; the code takes it in any state, and it acts as a note from the
  user (the thread is the agent's turn, not seen).
- Edits and deletes: a comment sent again with its id replaces the thread's first message, and a delete hides the
  thread. Neither is modelled.
- Threads that start closed by the user: an action of the user that is no message to the agent, such as a verdict or a
  confirmation (D8), a worker's report that it closed a question (D10), and a thread an old log marked done (D13). The
  model's roots all start open.
- Order: on the pages with decisions (the research board, the discover page, the code dashboard), `page.js` folds the
  events in time order, as `pageDecisionEvents` merges the decisions into the log by time, while Python folds them in
  log order. Both index an event by its line in the log, so `read` means the same in both.

Invariants: `NoLostWrite` (a user event the agent has not read puts the thread in the agent's turn), `CloseSticks`
(in `conversation.tla`, a close the agent has not read stays closed; in `thread.tla`, a thread the user closed stays
closed until the user acts on it again, whatever the agent does), `NoDeadThread` (every open thread can move), `AskedAfterReading`
(Your turn only for a question asked after reading the user's latest message), `SeenIsTrue` (Not seen yet only
while the agent has not read the user's latest event), `TypeOK`. `thread.tla` also states S4 and `InOpen` (S6) as comments: no config checks them.

## Configs

Must fail, with the invariant named in the trace. TLC searches breadth first and checks the invariants in the order
the config lists them, so it reports the shortest violation of the first one: `as-built-item` also breaks
`CloseSticks` (one step deeper), and `thread-without-stale-guard` also breaks `AskedAfterReading` (in the same
state, listed after `NoLostWrite`).

| Config | Fails with | Shows |
| --- | --- | --- |
| `as-built-item` | `NoLostWrite` | as built, a user write is lost when a stale status lands after it |
| `as-built-agent` | `NoDeadThread` | as built, a thread under an agent message can get stuck |
| `without-stale-guard-lost` | `NoLostWrite` | with Close anywhere but no stale guard, writes are still lost |
| `without-stale-guard-close` | `CloseSticks` | with no stale guard, an unread close is undone |
| `without-close-any-time` | `NoDeadThread` | with the guard but Close only on done items, a thread can get stuck |
| `thread-without-stale-guard` | `NoLostWrite` | the thread machine needs the stale guard |

Must pass:

| Config | Shows |
| --- | --- |
| `fix-item`, `fix-agent` | the fix (guard and Close on every open thread) holds for both roots |
| `thread-question` | the designed machine holds for a thread that starts with an agent question |
| `fix-item-larger`, `fix-agent-larger` | the same with bigger bounds (slow) |
| `thread-user`, `thread-report` | the designed machine for the other two roots (slow) |

## Run

The test is `tests/test_formal_conversation.py`:

    TLA2TOOLS=<path to tla2tools.jar> TLA_JAVA=<java> python3 tests/run.py test_formal_conversation

Without `TLA2TOOLS` every test is skipped as "not proven": nothing was checked. The fast configs take a few minutes
together. The slow configs (up to 15 minutes and 18 million states each) run only with `BETTER_AI_SLOW_TLA=1` also
set. By hand: `java -cp tla2tools.jar tlc2.TLC -deadlock -config fix-item.cfg conversation.tla` in this directory.
