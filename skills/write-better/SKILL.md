---
name: write-better
description: Helps an AI agent write better. Improves AI agents' structure and clarity.
---

# Write Better

IF invoked without argument, use these instructions to rewrite your previous output.
IF invoked with a document or artifact as argument, use these instructions to rewrite the document in question.

## 1. Before writing

### 1.1. Who is the reader?

IF AVAILABLE, use your local context, prior knowledge, and memories to identify the user and their preferences.
IF you know the user name, IDENTIFY skills such as `/review-for-{user}`, `/write-for-{user}` and READ their instructions.
IF the user stated how they prefer to read, FOLLOW that preference over the general rules below.
DO NOT infer the user's ability, education, or background from their dialect, spelling, or fluency. Models give less accurate and more condescending answers to users who write non-standard English, and guess demographics from stereotyped cues.

### 1.2. Name the GOAL

IF the user specified a personal GOAL, USE this as the ultimate outcome of your output.
IDENTIFY what is the main GOAL of your writing:

1. The user UNDERSTANDS something new.
2. The user LEARNS to do something later without AI.
3. The user TAKES AN ACTION thanks to the output.
4. The user MAKES A DECISION thanks to the output.

IF you cannot IDENTIFY the main GOAL, ASK the user, using `AskUser`:

```
[question] How will you use this writing?
[option] I understand something new.
[option] I learn to do this myself.
[option] I can take the right action.
[option] I can make a decision.
```

### 1.3. Assume your draft is unclear

Research fills your context with specialized information the user does not have. Expertise makes the writer more abstract, more technical, and more passive.

IDENTIFY what this audience already knows, and PROVIDE the context they are missing, so they can understand everything you write. EXPLAIN or REPLACE file names, function names, and internal labels they may not know. KEEP a technical name only when the user must type or find it, and explain it on first use.

## 2. Include only what the user needs

### 2.1. Cut interesting but irrelevant material

DELETE anecdotes, unsupported conclusions, research details, dead-ends, and trivia that do not serve the user's GOAL. Length and polish raise a reader's confidence without making them more accurate, so DO NOT add either for reassurance.

### 2.2. Repair reasoning gaps

STATE causal and logical links between propositions. EXPLAIN new concepts when they first appear.

### 2.3. Separate additional details

MOVE details that do not directly support the user's GOAL to appendices. KEEP each limit, condition, and exception next to the claim it qualifies, even when the claim is in a list.

### 2.4. Add nothing new when rewriting

WHEN rewriting, DO NOT add steps, facts, advice, options, recommendations, calculations, or sections that the original does not contain. DO NOT add a note about what you removed. WHEN the original is already short and clear, keep it about the same length.

## 3. Structure your writing

### 3.1. Give context before detail

START your output with one or two sentences that state the main point itself. A reader who stops there must still know the key result and why it matters. DO NOT announce what the text will cover.

ADD a descriptive title before those sentences only when the output is long enough to need headings. A reply of a few sentences gets no title, because a title restates its point and adds length.

### 3.2. State the answer first

WHEN the GOAL is to UNDERSTAND: provide a high-level summary of the topic.
WHEN the GOAL is to LEARN: ask a question the user can attempt first, then explain the reasoning, rather than only giving the answer. FOR teaching over several turns, USE `/teach-better` if available.
WHEN the GOAL is to TAKE AN ACTION: provide clear and simple step-by-step instructions.
WHEN the GOAL is to MAKE A DECISION: state your recommendation and its main reason straight after the opening, in one line, before any background. IF you cannot recommend an option, state the decision criteria there instead. WHEN rewriting, recommend an option only if the original does.

IN ALL CASES, WRITE this part so it does not require concepts from the rest of the document.

### 3.3. Make long outputs easy to navigate

USE descriptive headings, so the user can find a section without reading the others.
USE numbered lists for steps, with one instruction per step. USE tables for comparisons.

### 3.4. Show relations, not only describe them

WHEN the GOAL is to UNDERSTAND or MAKE A DECISION and the content describes how things relate, such as causes, overlaps, comparisons or changes, ADD a table, chart or diagram next to the prose. Graphics added to text improve comprehension for most readers. USE `/show-better` to choose and build it, if available.

DO NOT add a visual that only decorates, or one that repeats the prose word for word. Irrelevant material and identical text in two places both lower learning.

### 3.5. Keep the format adjustable

WHEN you control the format, publish live text, so the user can change its size, spacing, and colours or have it read aloud.
AVOID relying on dyslexia-specific fonts or Bionic Reading. Evidence does not show that they help.

### 3.6. Bold a few key ideas

WHEN the output is longer than a few paragraphs, BOLD the few phrases that carry its key ideas, so the user can find them on a quick scan. LIMIT bolding to those key ideas. Emphasis lowers recall of the parts that are not emphasised, so DO NOT bold whole sentences, labels, or every important term.

## 4. Word choices

### 4.1. Use words the user already knows

Replace a long or rare word with a common one when the meaning stays exact. If this is not possible, explain the word on first-use.

Simplify the language, not the substance. A simpler version KEEPS its conditions and limitations: readers who know the topic skipped limitations in overly plain summaries.

IF you do not know what the user knows about the topic, WRITE for a reader who knows less, and USE headings so others can skip ahead. Simpler text helps readers new to a topic. TREAT this as a guide, not a rule: the evidence that extra support costs experts little is indirect.

### 4.2. State the limits

NAME what experts disagree on, where the evidence is weak, and whom to consult. STATE consensus only when agreement is high.

STATE your own uncertainty in the first person, such as "I could not check X". First-person uncertainty made readers rely less on wrong AI answers; impersonal phrasing such as "it is not clear" had weaker effects.

### 4.3. Prefer coherence

Shorter sentences and words alone do not guarantee comprehension. USE one term for each concept throughout the output. DO NOT switch to synonyms or paraphrases.

### 4.4. Choose active or passive voice by what the user needs

Use the active voice when the actor matters. Use the passive voice when the actor is unknown or irrelevant, or to keep the topic at the start of the sentence.

### 4.5. Use concrete examples

PROVIDE worked examples when relevant. PREFER one continuous case study through the output. USE several examples only when they show different perspectives or boundary conditions.

### 4.6. Use a neutral tone

AVOID aggressive and enthusiastic language.

### 4.7. Keep sentence structure easy to follow

Limit sentence length, and put the main verb early in the sentence. AVOID double negatives and clauses nested inside other clauses.

### 4.8. Say what you mean literally

REPLACE metaphors, idioms, hints, and exaggeration with direct statements, or explain them. WHEN you need the user to do something, state what and by when.

### 4.9. Be specific

USE exact numbers, dates, and names instead of vague terms such as "soon" or "a few", unless the exact value is unknown. KEEP what each number measured and what it was compared with. SEPARATE facts from opinions and feelings.

### 4.10. Write about people neutrally

USE gender-neutral words, such as "staff" or "humanity". USE "they" for a person whose gender is unknown or does not matter. USE a known person's own pronouns.

DESCRIBE people the way they describe themselves. IF that is unknown, LEAVE OUT labels the point does not need. Style guides disagree on default wording for disability, and the people concerned disagree among themselves.

REPLACE ableist words, such as "crazy", "lame" or "blind to", with a more accurate word. WHEN examples name people, VARY their names, genders, and cultures, and DO NOT default to a Western or affluent setting.