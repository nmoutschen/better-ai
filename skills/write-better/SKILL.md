---
name: write-better
description: Helps an AI agent write or rewrite text the user understands and acts on, such as an answer, a report, a message or a document. Use it for any text the user reads; use show-better to add visual panels before a dense document, and the user's own write-for-NAME guide, if they have one, with it.
---

# Write Better

IF invoked without argument, USE these instructions to rewrite your previous output.
IF invoked with a document or artifact as argument, USE these instructions to rewrite that document.

Being invoked does NOT mean the text needs large changes. A text that already meets these instructions keeps its length and structure, and a rewrite can end with few edits.

## Principles

1. Readers rate text as clear without understanding it better. Length and polish raise a reader's confidence without making them more accurate.
2. Simpler wording helps readers new to a topic. Readers who know the topic skipped limitations in overly plain summaries.
3. Headings, signals of structure, and graphics that show relations improve comprehension. Emphasis helps the emphasised parts and lowers recall of the rest.
4. Models treat users differently by how they write and by what the user discloses about themselves, using stereotypes. What the user states about the output is a better guide.
5. First-person uncertainty made readers rely less on wrong AI answers.
6. Models assume the user shares their context instead of checking. Trying to imagine what a reader knows does not improve the estimate; checking what the reader has seen does.
7. TREAT these rules as a guide, not as fixed rules for every reader.

## 1. Before writing

### 1.1. Identify the reader

LOOK UP what the context says about the reader: the conversation, project files, and memories. IF the user or project has its own writing guide or writing skill, such as `write-for-<name>`, FOLLOW it as well. These instructions give the general method; the user's guide adjusts it for that reader, and overrides these rules where the two conflict.
IF the user stated how they prefer to read, FOLLOW that preference over the general rules below. IF a stored preference changes the output, SAY so in one sentence.
DO NOT infer the user's ability, education, or background from their dialect, spelling, or fluency. Models give less accurate and more condescending answers to users who write non-standard English, and guess demographics from stereotyped cues.
IF the user disclosed a diagnosis or condition, DO NOT change the content or advice because of it. ADAPT the format only as the user asks. Models that tailor answers to a disclosed diagnosis apply stereotypes, and some readers find the result patronising.

### 1.2. Name the GOAL

IF the user specified a personal GOAL, USE it as the ultimate outcome of your output.
OTHERWISE, IDENTIFY the main GOAL of your writing:

1. The user UNDERSTANDS something new.
2. The user LEARNS to do something later without AI.
3. The user DOES something thanks to the output.
4. The user DECIDES something thanks to the output.

IF the context does not show the GOAL, CHOOSE the most plausible one and STATE it in one sentence next to the result, so the user can correct it. ASK only when a wrong GOAL would waste a large amount of the user's work. FOLLOW `/ask-better` for the question if available, THEN CONTINUE with section 1.3. OTHERWISE, ASK one question with these options, using a structured question tool such as `AskUserQuestion` if available, or in plain text at the end of your response:

```
[question] How will you use this writing?
[option] I understand something new.
[option] I learn to do this myself.
[option] I can take the right action.
[option] I can make a decision.
```

### 1.3. Assume your draft is unclear

Your context holds what the user does not: research, tool output, files you read, your own reasoning, and earlier turns they may not remember. Expertise makes the writer more abstract, more technical, and more passive.

IDENTIFY what this audience already knows from what they wrote and read, and PROVIDE the context they are missing, so they can understand everything you write. FOR each plan, result, or file you refer to that the user has not just written or read, SAY what it is: "the plan to split the parser into two files", not "the plan". EXPLAIN or REPLACE file names, function names, and labels you made up. KEEP a technical name only when the user must type or find it, and EXPLAIN it on first use. DO NOT restate what the user just said.

WHEN the user comes back after a break, START with the last thing done and the next step.

## 2. Include only what the user needs

### 2.1. Cut interesting but irrelevant material

DELETE anecdotes, unsupported conclusions, research details, dead-ends, and trivia that do not serve the user's GOAL. Length and polish raise a reader's confidence without making them more accurate, so DO NOT add either for reassurance.

DELETE padding: a restated question, a preamble, generic caveats, formatting around a short answer, and a list of possible answers given to cover the right one.

DO NOT cut content the reader uses: the correction of a false premise in the request, the context that explains a result, and your first-person statements of uncertainty. Instructions to be brief made models worse at correcting false premises.

### 2.2. Repair reasoning gaps

STATE causal and logical links between propositions. EXPLAIN new concepts when they first appear.

### 2.3. Separate additional details

MOVE details that do not directly support the user's GOAL to appendices. KEEP each limit, condition, and exception next to the claim it qualifies, even when the claim is in a list.

### 2.4. Add nothing new when rewriting

WHEN rewriting, DO NOT add steps, facts, advice, options, recommendations, calculations, or sections that the original does not contain. DO NOT add a note about what you removed. WHEN the original is already short and clear, KEEP it about the same length.

## 3. Structure your writing

### 3.1. Give context before detail

START your output with one or two sentences that state the main point itself. A reader who stops there must still know the key result and why it matters. DO NOT announce what the text will cover.

ADD a descriptive title before those sentences only when the output is long enough to need headings. A reply of a few sentences gets no title, because a title restates its point and adds length.

### 3.2. State the answer first

WHEN the GOAL is to UNDERSTAND: PROVIDE a high-level summary of the topic.
WHEN the GOAL is to LEARN: ASK a question the user can attempt first, then EXPLAIN the reasoning, rather than only giving the answer. FOR teaching over several turns, USE `/teach-better` if available.
WHEN the GOAL is to DO something: PROVIDE clear and simple step-by-step instructions.
WHEN the GOAL is to DECIDE: STATE your recommendation and its main reason straight after the opening, in one line, before any background. IF you cannot recommend an option, STATE the decision criteria there instead. WHEN rewriting, RECOMMEND an option only if the original does.

IN ALL CASES, WRITE this part so it does not require concepts from the rest of the document.

### 3.3. Make long outputs easy to navigate

USE descriptive headings, so the user can find a section without reading the others.
USE numbered lists for steps, with one instruction per step. USE tables for comparisons.

### 3.4. Show relations, not only describe them

WHEN the GOAL is to UNDERSTAND or DECIDE and the content describes how things relate, such as causes, overlaps, comparisons or changes, ADD a table, chart or diagram next to the prose. Graphics added to text improve comprehension for most readers. FOR a long, dense document, such as a report or a design doc, USE `/show-better` if available to introduce it with a short sequence of visual panels.

DO NOT add a visual that only decorates, or one that repeats the prose word for word. Irrelevant material and identical text in two places both lower learning.

### 3.5. Keep the format adjustable

WHEN you control the format, PUBLISH live text, so the user can change its size, spacing, and colours or have it read aloud.
DO NOT rely on dyslexia-specific fonts or Bionic Reading. Dyslexia fonts gave no gain in reading, even for dyslexic readers. The rule on Bionic Reading is a design choice.

### 3.6. Bold a few key ideas

WHEN the output is longer than a few paragraphs, BOLD the few phrases that carry its key ideas, so the user can find them on a quick scan. LIMIT bolding to those key ideas. Emphasis lowers recall of the parts that are not emphasised, so DO NOT bold whole sentences, labels, or every important term.

## 4. Word choices

### 4.1. Use words the user already knows

USE a common word instead of a long or rare one when the meaning stays exact. WHEN the rare word is needed, KEEP it and EXPLAIN it next to its first use, with a short common synonym. Showing a simple synonym next to a hard word helped readers more than replacing the word.

SIMPLIFY the language, not the substance. A simpler version KEEPS its conditions and limitations: readers who know the topic skipped limitations in overly plain summaries.

IF you do not know what the user knows about the topic, WRITE for a reader who knows less, and USE headings so others can skip ahead. Simpler text helps readers new to a topic. TREAT this as a guide, not a rule.

### 4.2. State the limits

NAME what experts disagree on, where the evidence is weak, and whom to consult. STATE consensus only when agreement is high.

STATE your own uncertainty in the first person, such as "I could not check X". First-person uncertainty made readers rely less on wrong AI answers; impersonal phrasing such as "it is not clear" had weaker effects.

### 4.3. Prefer coherence

Shorter sentences and words alone do not guarantee comprehension. USE one term for each concept throughout the output. DO NOT switch to synonyms or paraphrases.

### 4.4. Choose active or passive voice by what the user needs

USE the active voice when the actor matters. USE the passive voice when the actor is unknown or irrelevant, or to keep the topic at the start of the sentence.

### 4.5. Use concrete examples

PROVIDE worked examples when relevant. PREFER one continuous case study through the output. USE several examples only when they show different perspectives or boundary conditions.

### 4.6. Use a neutral tone

DO NOT use aggressive or enthusiastic language.

### 4.7. Keep sentence structure easy to follow

LIMIT sentence length, and PUT the main verb early in the sentence. DO NOT use double negatives or clauses nested inside other clauses.

### 4.8. Say what you mean literally

REPLACE metaphors, idioms, hints, and exaggeration with direct statements, or EXPLAIN them. WHEN you need the user to do something, STATE what and by when.

### 4.9. Be specific

USE exact numbers, dates, and names instead of vague terms such as "soon" or "a few", unless the exact value is unknown. KEEP what each number measured and what it was compared with. SEPARATE facts from opinions and feelings.

### 4.10. Write about people neutrally

USE gender-neutral words, such as "staff" or "humanity". USE "they" for a person whose gender is unknown or does not matter. USE a known person's own pronouns.

DESCRIBE people the way they describe themselves. IF that is unknown, LEAVE OUT labels the point does not need. Style guides disagree on default wording for disability, and the people concerned disagree among themselves.

REPLACE ableist words, such as "crazy", "lame" or "blind to", with a more accurate word. WHEN examples name people, VARY their names, genders, and cultures, and DO NOT default to a Western or affluent setting.

## 5. Check the result

WHEN rewriting, COMPARE the result with the original. CHECK that every number, name, condition, limit, and recommendation is still there and still says the same thing. RESTORE anything the rewrite dropped or changed.

CHECK the opening against section 3.1: a reader who stops after it knows the main point.

CHECK each reference against section 1.3: the user saw it, or the text says what it is.

REPORT only the checks you performed. DO NOT claim the text is clearer because it reads more fluently: readers' sense of clarity does not show that they understand more.
