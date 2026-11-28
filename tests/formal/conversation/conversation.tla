---------------------------- MODULE conversation ----------------------------
(***************************************************************************)
(* The state of one thread of a live page's conversation, as the user and *)
(* the agent change it at the same time, by the per-item rules built     *)
(* before the thread machine: page.js `pageThread` and an earlier         *)
(* `all_items`, both since replaced by `pageThreads` and `threads`, which *)
(* thread.tla models.                                                      *)
(*                                                                         *)
(* The log is `conversation.jsonl`: every action appends one event, and   *)
(* an item's state is read back from the whole log. Each side acts on     *)
(* what it last read: the agent runs `pending`, works, then runs `status`;*)
(* the user acts on the page as last drawn. So an event can land after    *)
(* one its author never saw. What the model assumes:                      *)
(*  A1. Appends are whole and ordered (the `talk` model checks this).     *)
(*  A2. The agent's read (`pending`) sees the whole log at that moment.   *)
(*  A3. The page shows the user the log as it is when they act: the page  *)
(*      streams events within seconds. A user acting on an older drawing  *)
(*      is not modelled.                                                  *)
(*                                                                         *)
(* Root = "item": the thread is the user's own comment or message, item 1.*)
(* Root = "agent": the thread is a message the agent posted on its own;   *)
(* each note the user writes under it is an item of its own.              *)
(* CloseAnyTime: the page offers Close on every open thread, closing every *)
(* item in it (#172); otherwise Accept shows only on a done item of its   *)
(* own entry, as built.                                                   *)
(* StaleGuard: a status carries what the agent had read; a status that    *)
(* predates the user's latest event on the item does not change its state.*)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS Root, MaxItems, MaxLog, CloseAnyTime, StaleGuard

Statuses == {"seen", "working", "asked", "done"}
Finished == {"done", "accepted"}
\* The states in which the item is the agent's to act on: `pending` lists them.
AgentTurn == {"new", "seen", "working", "replied", "followup", "reopened"}

VARIABLES log, snap
vars == <<log, snap>>

\* An event: t is its type, by "user" or "agent", to the item it is about (0: the agent's own message), seen the length
\* of the log the agent had read (status only).
Ev(t, by, to, s, seen) == [t |-> t, by |-> by, to |-> to, s |-> s, seen |-> seen]

Init ==
  /\ log = IF Root = "item" THEN <<Ev("new", "user", 1, "", 0)>> ELSE <<Ev("msg", "agent", 0, "", 0)>>
  /\ snap = 0

Created(L) == {L[k].to : k \in {k \in 1..Len(L) : L[k].t = "new"}}

\* The index of the user's latest event about item i among the first n events of L; 0 when none.
LastUser(L, i, n) ==
  LET ks == {k \in 1..n : L[k].by = "user" /\ L[k].to = i /\ L[k].t \in {"new", "note", "accept", "reopen"}}
  IN IF ks = {} THEN 0 ELSE CHOOSE k \in ks : \A j \in ks : j <= k

\* The state of item i after the first n events: the rules both implementations share.
RECURSIVE StateAt(_, _, _)
StateAt(L, i, n) ==
  IF n = 0 THEN "none" ELSE
  LET e == L[n]
      s == StateAt(L, i, n - 1)
  IN IF e.to # i THEN s
     ELSE CASE e.t = "new" -> "new"
            [] e.t = "status" ->
                 IF StaleGuard /\ e.seen < LastUser(L, i, n - 1) THEN s ELSE e.s
            [] e.t = "accept" -> "accepted"
            [] e.t = "reopen" -> "reopened"
            [] e.t = "note" ->
                 IF s = "asked" THEN "replied" ELSE IF s \in Finished THEN "followup" ELSE s
            [] OTHER -> s

State(i) == StateAt(log, i, Len(log))
Items == Created(log)
\* The user closed the agent's own message before answering it.
RootClosed == \E k \in 1..Len(log) : log[k].t = "accept" /\ log[k].to = 0

\* ---------- What the page shows ----------
\* Open, as the removed page.js `pageThread` counted it: an item not closed, or the agent's own message no one answered yet.
ThreadOpen ==
  \/ \E i \in Items : State(i) # "accepted"
  \/ (Root = "agent" /\ Items = {} /\ ~RootClosed)
\* The user can close the thread from the page.
UserCanClose ==
  IF CloseAnyTime THEN ThreadOpen
  ELSE Root = "item" /\ State(1) = "done"
\* The thread waits on the user: the agent asked, or its own message has no answer yet.
WaitsOnUser == (\E i \in Items : State(i) = "asked") \/ (Root = "agent" /\ Items = {} /\ ~RootClosed)
\* The agent has work on it: `pending` lists an item.
AgentHasWork == \E i \in Items : State(i) \in AgentTurn

\* ---------- The user ----------
NextItem == IF Items = {} THEN 1 ELSE (CHOOSE m \in Items : \A j \in Items : j <= m) + 1

\* A message: under the user's own item it joins that item; under the agent's message it is a new item.
UserWrite ==
  IF Root = "item" THEN log' = Append(log, Ev("note", "user", 1, "", 0))
  ELSE /\ NextItem <= MaxItems
       /\ log' = Append(log, Ev("new", "user", NextItem, "", 0))

UserClose ==
  /\ UserCanClose
  /\ IF CloseAnyTime
     THEN \/ \E i \in Items : State(i) # "accepted" /\ log' = Append(log, Ev("accept", "user", i, "", 0))
          \/ Root = "agent" /\ Items = {} /\ log' = Append(log, Ev("accept", "user", 0, "", 0))
     ELSE log' = Append(log, Ev("accept", "user", 1, "", 0))

UserReopen == \E i \in Items : State(i) = "accepted" /\ log' = Append(log, Ev("reopen", "user", i, "", 0))

\* ---------- The agent ----------
AgentRead == snap # Len(log) /\ snap' = Len(log) /\ UNCHANGED log

\* The agent sets a status on an item it has read about, from what it read.
AgentStatus ==
  \E i \in Created(SubSeq(log, 1, snap)), s \in Statuses :
    log' = Append(log, Ev("status", "agent", i, s, snap))

Next ==
  /\ Len(log) < MaxLog
  /\ \/ (UserWrite \/ UserClose \/ UserReopen) /\ UNCHANGED snap
     \/ AgentRead
     \/ AgentStatus /\ UNCHANGED snap

Spec == Init /\ [][Next]_vars

\* ---------- Properties ----------
\* S1: a message, comment or reopen from the user that the agent has not read yet leaves the item with the agent.
NoLostWrite ==
  \A i \in Items :
    LET k == LastUser(log, i, Len(log)) IN
      (k > snap /\ log[k].t # "accept") => State(i) \in AgentTurn
\* S2: a close the agent has not read yet stays closed.
CloseSticks ==
  \A i \in Items :
    LET k == LastUser(log, i, Len(log)) IN
      (k > snap /\ log[k].t = "accept") => State(i) = "accepted"
\* S3: every open thread can move: the agent has work on it, it waits on the user, or the user can close it.
NoDeadThread == ThreadOpen => (AgentHasWork \/ WaitsOnUser \/ UserCanClose)
\* Every item is in one of the states the page draws.
TypeOK == \A i \in Items : State(i) \in AgentTurn \cup Finished \cup {"asked"}
=============================================================================
