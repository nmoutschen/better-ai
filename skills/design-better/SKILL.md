---
name: design-better
description: Helps an AI agent design and audit an interface or page, such as a web page, an app screen or a rendered report, so that the people who use it can do what they came for, and create, apply and audit the design language behind it. Agrees the audience and their tasks with the user, shows rough directions before anything is built, hands a design to code-better to build, and accepts the result only once a reviewer has walked each task in the built interface. Use show-better to introduce a document with visual panels, and write-better for the words in the interface.
argument-hint: "[INTERFACE OR TASK]"
metadata:
  kind: procedural
---

# Design Better

IF invoked with an interface or a design task as argument, FOLLOW the instructions below for that task.
IF invoked without argument and the current conversation builds or changes an interface, AUDIT that interface with [modes/audit.md](modes/audit.md), THEN continue or correct the work.
IF invoked without argument and there is no such interface, ASK the user which interface or design language to work on, and whether to design, audit or change it.
IF the task changes neither which screens exist, what they hold, their layout or flow, nor the design language, such as a clearer label or a fix inside one screen, FOLLOW only the [Design rules](#design-rules) for it, and USE `/code-better` to make the change, or IF it is not available, CHANGE only what the task needs and RUN the project's existing checks. In both cases, SKIP the Instructions.

Being invoked does NOT mean a redesign, and does NOT mean anything gets built now. The work can end with a brief and questions for the user, or with a report that the interface already lets people do what they came for.

This skill uses two words for people. The user is the person you work for. The AUDIENCE is the people who will use the interface. They can be the same person.

## Principles

1. People judge an interface that looks good as easy to use, whether or not it is. Approval of how an interface looks, from the user or from you, does not show that the AUDIENCE can use it.
2. Generated interfaces do well on what automated checkers measure, such as contrast and the presence of alt text. They fail on meaning: what a control is called, what an image description says, whether headings and labels describe the content.
3. Every check finds only part of the problems: an automated checker, a review against a list of rules, a model looking at a screenshot, a test with a few people. Two reviewers of the same interface report largely different problems, and reviews report many problems that people do not have.
4. People judge more critically and more precisely when they compare concrete versions than when they see one version or describe what they want in words.
5. Few layout and type rules hold for every task and every AUDIENCE, and taste differs between people, including trained designers.
6. People overlook removing something as a way to improve it unless prompted to consider removal.
7. The brief, the hand-off of building to `/code-better`, and the acceptance review of every built interface are design choices. Each mode file names its own design choices.

## Instructions

FOLLOW these steps in order.

### 1. Understand the work

NAME the GOAL: what the AUDIENCE must be able to do with the interface, and what the user wants to achieve by providing it. DISTINGUISH it from the requested page. "A dashboard" is a request. "See which orders are late and open one" is a GOAL.

READ the existing interface, its components, styles and design files, the content it must show, the project's instruction files, and the earlier conversation. DO NOT ask the user what these sources answer.

TREAT an existing design language, its colours, typefaces, type sizes, spacing values and components, as a requirement the user owns. A change to any value it defines is a change to the design language, however small: DO NOT make it as a fix. WHEN it conflicts with a [Design rule](#design-rules), such as text contrast, REPORT the conflict once, with its effect on the AUDIENCE and one alternative, THEN WAIT for the user's decision. IF no design language exists and the work covers more than one screen, ASK the user whether to create one first.

### 2. Write the brief

WRITE `.design/<slug>/brief.md` with [templates/brief.md](templates/brief.md): the GOAL, the AUDIENCE, their scenarios, the structure, the content, the constraints, and your assumptions. IF a brief exists, UPDATE it in place.

DESCRIBE the AUDIENCE by what they do and the conditions they do it in: the device and screen sizes, the input method, how much time they have, what they already know. DO NOT invent a fictional person, and DO NOT assign the AUDIENCE traits you guessed.

WRITE each scenario as one task from its start to an end the person can observe, with concrete data: who comes, what they came to do, and what they see or have when it is done. KEEP the scenarios few: a scenario earns its place only if a wrong guess on it would change the design. Every mode checks the interface against them.

WRITE the structure: which pages exist, what each holds, and how they link. FOR each page and each main part of a page, NAME the scenario it serves, THEN ASK whether it should stay, merge with another, or go (Principle 6). A page or part that serves no scenario, repeats another, or follows how its content was produced instead of what the AUDIENCE comes to do, is a candidate to merge or remove: SETTLE it with the user, because organising by task beats organising by subject in some studies and not in others.

### 3. Ask a few questions

ASK the user, as the general rule [Ask the user](#ask-the-user) says, what only they know and what changes the design. KEEP building the brief while you wait.

### 4. Pick the mode

PICK the one mode that fits the work. READ its file: it is MANDATORY, and the next step cannot run without it. IF the user agreed in step 1 to create a design language first, RUN [modes/language.md](modes/language.md), THEN the mode the task needs.

| Mode | When | File |
|---|---|---|
| Design | a new interface, or a change to which screens exist, what they hold, their layout or their flow | [modes/design.md](modes/design.md) |
| Audit | the user asks for a review of an interface or a design language, theirs or someone else's, or what to improve | [modes/audit.md](modes/audit.md) |
| Language | create, extend or change a design language | [modes/language.md](modes/language.md) |

### 5. Run the mode

FOLLOW every step of the mode's file, in order.

### 6. Hand back

LEAD with the result, THEN report, USING `/write-better` for the wording if available:

1. In one sentence, which scenarios were walked in the built interface, and how. Each scenario that fails or that was not walked, and why.
2. The decisions the user owns: each conflict between the design language and a rule, and each assumption that changed the design.
3. The open and unconfirmed findings of the review.

WHEN the work changed how an interface looks and you can render, SHOW each changed screen before and after, by [Show versions on one page](#show-versions-on-one-page). WHEN it goes into a pull request, PUT screenshots of each changed screen in its description, before and after, at the screen sizes in the brief.

DISTINGUISH three things, and DO NOT claim one from another: the scenarios can be completed, the checks pass, and the AUDIENCE can use the interface. Only a test with people shows the third.

WHEN the interface is new or its main flow changed, and people other than the user will use it, OFFER a short test: the user watches three to five people from the AUDIENCE try the scenarios without help, worded without the interface's labels, and notes where each one hesitates or fails. IF the AUDIENCE has distinct groups, SUGGEST a few people from each. WHEN the change is to which pages exist, how they are grouped or what they are called, OFFER a tree test instead: people look for items in a text-only list of the structure. DO NOT count on an agent finding every item: agents find paths far more often than people do. SAY that such a test finds the common problems, not all of them, and WHEN a test leads to changes, OFFER a second short round on the changed flow, because fixes can create new problems. IF the user has said they do not want this, DO NOT offer it.

IF the user rejects the result, USE `/do-better` if available. OTHERWISE, FIND what the result misses from the user's feedback and the brief, and CORRECT it.

## General rules

FOLLOW these rules in every step and every mode.

### Ask the user

USE `/ask-better` if available. OTHERWISE, ASK at most about three questions, all in one message, each answerable in a few words or by choosing. COUNT a question a mode asks, such as the design mode's question about the user's direction, among them. ASK what only the user knows and what changes the design: what happens to the AUDIENCE's data, money or work, and what they are told. The first questions carry most of the value; many or generic questions cost the user more than they give.

WHEN a question is about how something looks, such as a colour, a layout or a component, SHOW the versions by [Show versions on one page](#show-versions-on-one-page), and ASK the user to choose. DO NOT ask from a text description when you can render.

FOR every other gap, including a technical fact the project does not state, such as an API's address, CHOOSE the most plausible option, PROCEED, and STATE the assumption in the brief and next to the result it affects.

### Add the records

ADD each record of the unit with `python3 <skill dir>/scripts/better.pyz add <unit> <type> --by <your name>`, or CHANGE it with `set`. IF it refuses the record, FIX the record and RUN it again. IF it reports busy, RUN it again. DO NOT get past a refusal by editing the records by hand.

### Show versions on one page

WHEN you show the user versions to choose between, or a change before and after, PUT them on one rendered page, side by side, because people judge a version more critically among others.

1. WRITE each version as its own HTML file in `.design/<slug>/`, with the same real content and the project's styles. FOR a before and after, SAVE a copy of the page before it changes. WHEN versions differ in only part of a page, WRITE that part with enough of its surroundings to place it, LABEL under each version what differs, and IF the change is small, MARK where it is, with the same mark in every version, outside the interface itself.
2. RUN `python3 <skill dir>/scripts/better.pyz create .design/<slug> --by <your name>` at the repo root, with the head record, type `canvas`, on stdin, IF the unit does not exist; OTHERWISE CHANGE it with `python3 <skill dir>/scripts/better.pyz set .design/<slug> canvas`. The head record holds: a `title`, the `question` (what the user decides), the `widths` and the `versions`, each with its label and its HTML file or an address the user's browser can reach. GIVE a width for every screen size in the brief, the size most of the AUDIENCE uses first: the page opens on it, and the user switches to the others. FOR a before and after, LABEL the versions `Before` and `After`. TELL the user to switch between versions in place WHEN they differ in a small detail. RUN `python3 <skill dir>/scripts/better.pyz render .design/<slug>`. DO NOT commit the page unless the user asks.
3. LOOK at the rendered page before you show it, and FIX each version that does not load, overlaps or is cut off.
4. FOLLOW the page handoff rule below. The user comments on any part of a version by clicking it, gives thumbs up or down when there are three or more versions, and approves with Approve…. A comment names the version, the element's selector and text, the sentence under the pointer, an image's source, the nearest heading and the parents: WORK OUT what the user pointed at from all of these.
5. ASK the question in your reply too, so the user can answer in the page or in the chat.
6. TREAT feedback from the page as the user's reply. WHILE the user works in the page, PUT everything for them in the page, and DO NOT answer each page action in the chat.
   - TRACK each thread with `python3 <skill dir>/scripts/better.pyz status .design/<slug> seen|working <id> --read <n>`: `seen` when you read it, `working` only while you change something for it. PASS `--read <n>` to every `status` and `reply --to`: n is the number on the last line of the last `pending` output or turn prompt you read. IF the command refuses because the user wrote in the thread since, READ what they wrote, THEN send it again.
   - REPLY in the user's thread, under the item you answer, with `python3 <skill dir>/scripts/better.pyz reply .design/<slug> --to <id> --read <n>`, your words on stdin, in one or two short sentences. The reply sets the thread's state: `done` by default, `--state asked` when you ask the user something about it, `--state working` when you reply before you have made the change. ONCE an answer leads to a change, REPLY done, THEN ASK any next question about it in the same thread, with `python3 <skill dir>/scripts/better.pyz reply .design/<slug> --to <id> --read <n> --state asked`.
   - ASK one question per message. POST a message without `--to` only to start a new subject: with `--state asked` when it is a question, without `--state` when it is a report, which needs no answer. IF a question you posted no longer needs an answer, REPLY done under it with `python3 <skill dir>/scripts/better.pyz reply .design/<slug> --to <its id> --read <n>`.
   - The user closes a thread with ✓. A thread you replied done stays in the user's Open list until they close it. Any message from the user in a thread gives it back to you: READ it as part of that thread.
   - IF you cannot tell whether a note under an item answers your question, ASK in one sentence, in that thread, with `python3 <skill dir>/scripts/better.pyz reply .design/<slug> --to <id> --read <n> --state asked`.
   - TO show new versions while the page is served, UPDATE the versions of the `canvas` record with `python3 <skill dir>/scripts/better.pyz set .design/<slug> canvas`: the open page loads them on the same view and screen size.
   - RUN `python3 <skill dir>/scripts/better.pyz pending .design/<slug>` after each batch of changes, after an interruption, and before you hand back, and FINISH or ANSWER what it lists. STOP the server only when the user has accepted the result.
   - DO NOT build from a version until the user approves. An approval names the open comments that come with it: APPLY them too.

IF you are in a session opened by the page, NEVER serve. WRITE what a step says to say or ask in the chat as a `reply` in the page. GIVE the skill's hand-back as one `reply` without `--to`. LET the user accept only with ✓ in the page, and ASK them to press it WHEN they accept in words. WHEN a step leads into a skill that serves its own page, REPLY that the step starts from the user's chat, with what to ask there, MARK the item `done`, and END the step. IF you are in the chat, your harness can run a background command, and the user's browser can reach this machine, RUN `python3 <skill dir>/scripts/better.pyz serve <unit>` in the background with the hand-off note on stdin: the step you reached and what was agreed in the chat. IF the unit already has a `.driver` file, PASS no hand-off note. READ the first `driver:` line. IF it is `driver: on` without `already`, SAY the page opened in the browser with its own agent, and END the turn. IF it is `driver: on` and the word `already`, SEND the user to the open page, and RUN `python3 <skill dir>/scripts/better.pyz link <unit>` IF they ask for a new tab. IF it is `driver: off`, or no `driver:` line comes within 40 seconds, SHOW the problem in one line and FOLLOW the skill's Missing capabilities for a page that cannot be served. AFTER the hand-off, DO NOT edit the unit, and WORK in a worktree. WHEN the user asks in the chat about the page, ANSWER "ask it in the page".

### Design rules

FOLLOW these rules in every design, build and audit. TREAT those marked as guides as guides, because their effect depends on the task and the AUDIENCE.

Layout, as guides:

- WHEN a person must find one thing, REMOVE or reduce the elements that compete with it.
- KEEP the density of content even across the page.
- MAKE every control look like something that can be clicked or tapped, and everything else look like it cannot.
- ON touch screens, MAKE targets about 9 mm or larger.
- PUT an element where the task leads the person: people searching for something else miss elements made prominent by size or colour alone.
- JUDGE navigation by whether each step is obvious, not by counting clicks or menu levels.

Text and colour:

- DO NOT use small body text; larger text helps up to a point. AIM for about 55 to 70 characters per line of running text, aligned to the start, not justified (guide).
- KEEP the contrast between text and background at least 4.5 to 1 for normal text. PREFER dark text on a light background for small text.
- DO NOT use colour as the only signal: ADD text, an icon or a shape.
- GIVE each colour one meaning across a page. IF a second part of the page, such as a table under a diagram, needs its own encoding, USE shapes, outlines or labels instead of reusing a colour: readers carry a colour's meaning from one part of the page to the next.
- WRITE bylines, stat lines and metadata as a sentence or a plain phrase, such as "53 articles in 9 topics, last updated 14 Nov 2026", not as fragments joined by a middle dot. This is a design choice.
- TREAT the choice between ordinary serif and sans serif typefaces as taste, and FOLLOW the design language. DO NOT choose a special typeface on the claim that it helps a group of readers.

Forms and feedback:

- GIVE every field a visible label, in one position across the form, and MARK which fields are required.
- PUT each error message next to its field, and SAY what is wrong and what to enter instead.
- DO NOT validate a field before the person has finished typing in it. PICK validation on leaving the field or on submit, and KEEP it.
- WHEN an action takes time, SHOW that something is happening. DO NOT choose a loading pattern on the claim that it feels faster.

Without sight or a mouse, where generated interfaces fail most:

- USE native elements, such as buttons, links and inputs, before custom ones, and GIVE every control a name that says what it does.
- WRITE headings that describe their sections, in order, and MARK the main regions of the page. SET the page's language.
- TIE each label to its field in the markup.
- WRITE alt text that says what the image shows or does in this place, and empty alt text for decorative images. DO NOT add a description to every image.
- MAKE every action possible by keyboard, in an order that follows the task, with a visible focus.
- GIVE content that moves by itself for more than five seconds a way to pause it, and HONOUR the reduced-motion setting.

Words: USE `/write-better` for labels, button text and messages if available. OTHERWISE, USE the words the AUDIENCE uses, and NAME the action on the control that performs it. WRITE names, labels and descriptions from the scenarios: no checker can judge whether they mean anything.

### Missing capabilities

This skill names capabilities, not tools: reading and writing files, asking the user, running commands, rendering a page and viewing it, operating a page by pointer and keyboard, running an automated accessibility checker, sub-agents, and publishing a page. WHEN a step needs to render or operate a page, LOOK first for a way in the environment, such as a headless browser or a browser automation library, and USE it.

IF you cannot do a step, MARK the work **not finished**, and SAY which step, WHY, and what it leaves unchecked. DO NOT present that step as done, and DO NOT replace it with a weaker step of your own, such as describing how a page you could not operate behaves, or reviewing your own work where a separate reviewer is required. IF you cannot run commands, MARK the work **not finished** and NAME the records not added. IF the page cannot be served, PUBLISH the versions and GIVE the link IF you can publish a page: its Copy all button copies the feedback for the user to paste, and a version that links files by relative path needs their content put into it first. OTHERWISE, RENDER them and GIVE the path. THEN MARK the work **not finished**, and SAY that the page was not served. One exception: IF you cannot render, SHOW each version as a text outline and SAY that the choice may change once it is rendered.
