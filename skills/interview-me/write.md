# Interview: how the user reads (`write-for`)

FOLLOW the steps in [SKILL.md](SKILL.md) around this interview: prepare (section 1), how to ask (section 2), write the output (section 3) and report (section 4).

## 1. Material to collect

ASK for a document the user found easy to understand and act on, and one they found hard. Documents written for them by anyone count, including earlier AI output.

## 2. Walk through a real document

FOR each document, ASK the user to describe what happened when they read it: what they did first, where they slowed down, and what they did afterwards. LET them answer without interrupting, except for a short clarification.

THEN PROBE the points where they made a choice:

1. What they skipped, reread, or looked up, and why.
2. What they would have changed about the document, and what they would have kept.
3. Whether they could act on it without asking anyone, and what was missing if not.

## 3. Compare versions

WRITE two short versions of the same passage. TAKE it from the user's own material when possible. CHANGE one thing between the two versions, such as where the main point appears, the length, the use of a list, the technical terms, or the amount of context. This is a design choice, not a tested rule.

FOR each pair, ASK:

1. Which version they would rather receive.
2. Why, in their own words.
3. What they would do next after reading each one. IF they could act on one and not the other, RECORD that: it is stronger evidence than which one they liked.

DO NOT tell the user which version follows `write-better` or any rule. COVER the dimensions where the user's material and answers disagree, or where they gave no answer, first.

## 4. Check the scope

ASK when each rule found so far does not apply, such as for an urgent message or a topic the user knows well.

## 5. Output

FOLLOW [templates/write-for.md](templates/write-for.md). A rule earns its place only when it changes what an agent already following `/write-better` would do.

SAVE it as the skill `write-for-<name>`, in a folder where the user's harness loads personal skills, or in a project's skills folder if the guide is for one project.
