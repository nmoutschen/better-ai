------------------------------- MODULE thread -------------------------------
(***************************************************************************)
(* The one state machine every thread of a live page follows               *)
(* (.design/conversation-panel/states.md), with the user and the agent     *)
(* acting at the same time, each on what it last read.                     *)
(*                                                                         *)
(* A thread is in one state: "you" (Your turn), "agent" (Agent's turn,     *)
(* with step new, seen or working) or "done". It is read back from the log *)
(* by one fold, the same in the page and in `pending`.                     *)
(*                                                                         *)
(* Root = "user": you started the thread. "question": the agent posted a   *)
(* question on its own. "report": the agent posted a report on its own.    *)
(* StaleGuard: an agent status counts only if the agent had read the       *)
(* user's latest event in the thread when it decided (`read`).             *)
(*                                                                         *)
(* Assumptions: A1 appends are whole and ordered (model `talk`). A2 the    *)
(* agent's read sees the whole log at that moment. A3 the page shows the   *)
(* user the log as it is when they act.                                    *)
(***************************************************************************)
EXTENDS Naturals, Sequences, TLC

CONSTANTS Root, MaxLog, StaleGuard

VARIABLES log, snap
vars == <<log, snap>>

Ev(t, by, s, read) == [t |-> t, by |-> by, s |-> s, read |-> read]

Init ==
  /\ log = CASE Root = "user" -> <<Ev("new", "user", "", 0)>>
             [] Root = "question" -> <<Ev("msg", "agent", "", 0), Ev("status", "agent", "asked", 1)>>
             [] Root = "report" -> <<Ev("msg", "agent", "", 0)>>
  /\ snap = Len(log)

UserEvents == {"new", "note", "accept", "reopen"}

\* The fold: the thread's state after the first n events. userAt is the index of the user's latest event; byUser says
\* the user closed it; seenTo is how far the agent had read, the highest `read` of its statuses so far.
RECURSIVE Fold(_)
Fold(n) ==
  IF n = 0 THEN [state |-> "done", step |-> "new", userAt |-> 0, byUser |-> FALSE, seenTo |-> 0] ELSE
  LET f == Fold(n - 1)
      e == log[n]
      fresh == ~StaleGuard \/ e.read >= f.userAt
      g == CASE e.t = "new" -> [f EXCEPT !.state = "agent", !.step = "new", !.userAt = n, !.byUser = FALSE]
             [] e.t = "msg" -> [f EXCEPT !.state = "done"]
             [] e.t \in {"note", "reopen"} -> [f EXCEPT !.state = "agent", !.step = "new", !.userAt = n, !.byUser = FALSE]
             [] e.t = "accept" -> [f EXCEPT !.state = "done", !.userAt = n, !.byUser = TRUE]  \* closes, or confirms a done thread
             [] e.t = "status" /\ fresh /\ ~f.byUser ->
                  LET h == [f EXCEPT !.seenTo = IF e.read > f.seenTo THEN e.read ELSE f.seenTo] IN
                  CASE e.s = "asked" -> [h EXCEPT !.state = "you"]
                    [] e.s = "done" -> [h EXCEPT !.state = "done"]
                    [] e.s \in {"seen", "working"} /\ f.state = "agent" -> [h EXCEPT !.step = e.s]
                    [] OTHER -> h
             [] e.t = "status" -> [f EXCEPT !.seenTo = IF e.read > f.seenTo THEN e.read ELSE f.seenTo]
             [] OTHER -> f
  IN \* Once the agent has read the user's latest event, the thread shows at least Seen.
     IF g.state = "agent" /\ g.step = "new" /\ g.seenTo >= g.userAt /\ g.userAt > 0 THEN [g EXCEPT !.step = "seen"] ELSE g

Now == Fold(Len(log))
State == Now.state

\* ---------- The user: the buttons states.md gives each state ----------
Answer == log' = Append(log, Ev("note", "user", "", 0))
Close == ~Now.byUser /\ log' = Append(log, Ev("accept", "user", "", 0))  \* ✓: on every thread you have not closed
Reopen == State = "done" /\ log' = Append(log, Ev("reopen", "user", "", 0))

\* ---------- The agent ----------
Read == snap # Len(log) /\ snap' = Len(log) /\ UNCHANGED log
Status == \E s \in {"seen", "working", "asked", "done"} : log' = Append(log, Ev("status", "agent", s, snap))

Next ==
  /\ Len(log) < MaxLog
  /\ \/ (Answer \/ Close \/ Reopen) /\ UNCHANGED snap
     \/ Read
     \/ Status /\ UNCHANGED snap

Spec == Init /\ [][Next]_vars

\* ---------- Properties ----------
LastUser == IF Now.userAt = 0 THEN 0 ELSE Now.userAt
\* S1: a message or reopen from the user that the agent has not read leaves the thread with the agent, not seen yet.
NoLostWrite == (LastUser > snap /\ log[LastUser].t \in {"new", "note", "reopen"}) => (State = "agent" /\ Now.step = "new")
\* S2: a thread the user closed stays closed until the user acts on it again, whatever the agent does.
CloseSticks == (LastUser > 0 /\ log[LastUser].t = "accept") => State = "done"
\* S3: "Your turn" shows only for a question the agent asked after reading the user's latest message.
AskedAfterReading == State = "you" => snap >= LastUser
\* S6: a thread is in Open until you close it: open means not closed by you.
InOpen == ~Now.byUser
\* S4: every state has a way on: Answer or Reply and Close while open, Reopen when done; and the agent sees its turn.
\* S5: "Not seen yet" shows only while the agent has not read the user's latest event.
SeenIsTrue == (State = "agent" /\ Now.step = "new" /\ Now.userAt > 0) => Now.seenTo < Now.userAt
TypeOK == State \in {"you", "agent", "done"} /\ Now.step \in {"new", "seen", "working"}
=============================================================================
