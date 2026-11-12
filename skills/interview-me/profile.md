# Interview: how the user wants agents to work (`profile`)

FOLLOW the steps in [SKILL.md](SKILL.md) around this interview: prepare (section 1), how to ask (section 2), write the output (section 3) and report (section 4).

This interview writes two files:

1. **Profile instructions**: a short text the user pastes into the always-on instructions of any AI tool, such as Claude's profile preferences, another assistant's custom instructions, or a user-level instructions file for a coding agent. The tool adds it to every conversation.
2. **Profile record**: a file that keeps each rule's scope, evidence and example. Updates read from it. The profile instructions are written from it.

The profile instructions are loaded into every conversation, whatever the task. Models follow fewer instructions as the number of instructions grows, mostly by leaving some out. So the profile holds only rules that matter in most conversations, and points to the `write-for` and `review-for` skills for the rest.

## 1. Material to collect

ASK for:

1. Two or three conversations or messages where the user corrected an AI agent's way of working, such as asking when it should have proceeded, proceeding when it should have asked, giving no source, stating a guess as a fact, or agreeing too quickly. Corrections the user made are the nearest record of what they need: users mispredict what they want from AI when asked in general.
2. Any always-on instructions the user already uses in any AI tool. TREAT each rule in them as **said**, not as shown.

## 2. Walk through a real correction

FOR each correction, ASK the user to describe what happened: what they asked for, what the agent did, what they expected instead, and what the difference cost them. LET them answer without interrupting.

THEN ASK what the agent could have done that would have needed no correction.

## 3. Cover the ways of working

COVER the following, first the ones the user's material and answers leave open. Users who share their always-on instructions ask for these, not only for style:

1. When to ask a question, and when to proceed and state the assumption.
2. Which sources to use and how to cite them.
3. How to state uncertainty, and when to say "I don't know".
4. When to disagree with the user, and how.
5. What to check before reporting work as done.
6. Which actions to confirm before taking, such as actions outside the conversation.

DO NOT ask about how text should read or how work is reviewed: the `write` and `review` interviews cover those. IF they have not run, OFFER to run them after this one.

## 4. Compare two responses

WRITE two short agent responses to the same request, taken from the user's material or current work when possible. MAKE them differ in one way of working only, such as one asking a question and the other proceeding with a stated assumption, or one disagreeing and the other complying.

ASK which response they would rather receive, why, and what they would do next after each one. IF one would have led them to correct the agent, RECORD that: it is stronger evidence than which one they liked.

## 5. Write the profile instructions

APPLY these rules on top of SKILL.md section 3.

### 5.1. Write behaviours, not a description of the user

WRITE each rule as something the agent does, with its scope. DO NOT describe the user's role, background, or views, even in one line. Context that lets a model infer the user's views made it agree more. IF a rule depends on what the user knows, WRITE it as a behaviour with its scope, such as "skip definitions of standard terms in <field>".

### 5.2. Keep it short, most important rule first

KEEP only rules that change what an agent would do in most conversations. MOVE a rule that applies to one kind of task to the `write-for` or `review-for` skill, or to a project's instructions, instead. PUT the rules whose omission would cost the user most first. Earlier rules held better as the number of rules grew.

### 5.3. Give each rule its own scope

WRITE the scope into the rule, such as "When a request has two plausible meanings, ask which one I mean". DO NOT write modes or commands that switch behaviour, such as "in mode X, do Y" or "if I type /short, …". Instructions that switch modes or verbosity were violated most often.

### 5.4. Point to the skills instead of copying them

IF `write-for-<name>` or `review-for-<name>` exists, ADD a line that tells the agent to use it when it writes text for the user or checks work before showing it to them. DO NOT copy their rules into the profile.

### 5.5. Write text any tool can use

WRITE plain text in the first person, as the user's own words. DO NOT use syntax that only one tool reads, such as file imports, front matter, or tool names. USE plain wording, not capitals or words such as "always" and "never" for emphasis: newer models respond more strongly to always-on instructions and may apply an emphatic rule where it does not fit.

ADD the lines from the template that say the latest explicit request wins and that the profile is not a reason to agree with the user. Tools rank always-on instructions against other instructions differently, and these lines keep the behaviour the same in each.

ASK which tools the user will paste the profile into. IF the user knows a tool's length limit, FIT the text to it. DO NOT state a limit you did not read in the tool or its documentation.

## 6. Output

FOLLOW [templates/profile-record.md](templates/profile-record.md) for the record, then WRITE the profile instructions from it with [templates/profile.md](templates/profile.md). They must contain the same rules in the same order.

SAVE both files together, as `profile-for-<name>.md` (the record) and `profile-for-<name>.txt` (the profile instructions), in a folder the user keeps across tools, such as their home directory or a dotfiles repository. GIVE the user the profile instructions in a code block, ready to paste. DO NOT change a tool's settings yourself: the user pastes the text.

IN the report, SAY that the profile is loaded into every conversation and can make agents agree more, and that the user can remove a rule at any time with `/interview-me <path of the record>`.
