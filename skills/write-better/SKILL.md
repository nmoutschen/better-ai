---
name: write-better
description: Helps an AI agent write better. Improves AI agents' structure and clarity.
---

# Write Better

Guidance and instructions on how to write better for the user.

IF invoked without argument, use these instructions to rewrite your previous output.
IF invoked with a document or artifact as argument, use these instructions to rewrite the document in question.

## 1. Before writing

### 1.1. Who is the reader?

IF AVAILABLE, use your local context, prior knowledge, and memories to identify the user and their preferences.
IF you know the user name, IDENTIFY skills such as `/review-for-{user}`, `/write-for-{user}` and READ their instructions.
IF the user stated how they prefer to read, FOLLOW that preference over the general rules below.

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

IF you are doing research on a particular topic, you are loading your context with specialized information not available to the user. Expertise makes the writer more abstract, more technical, and more passive.

IDENTIFY what this audience already knows, and PROVIDE the context they are missing, so they can understand everything you write. EXPLAIN or REPLACE file names, function names, and internal labels they may not know. KEEP a technical name only when the user must type or find it, and explain it on first use.

## 2. Include only what the user needs

### 2.1. Cut interesting but irrelevant material

DELETE anecdotes, unsupported conclusions, research details, dead-ends, and trivia that do not serve the user's GOAL. Length and polish raise a reader's confidence without making them more accurate, so DO NOT add either for reassurance.

### 2.2. Repair reasoning gaps

STATE causal and logical links between propositions. EXPAND/EXPLAIN new concepts when they first appear.

### 2.3. Separate additional details

MOVE additional details that do not directly support the GOAL of the user to appendices. KEEP each limit, condition, and exception next to the claim it qualifies, even when the claim is in a list.

### 2.4. Add nothing new when rewriting

WHEN rewriting, DO NOT add steps, facts, or sections that the original does not contain. WHEN the original is already short and clear, keep it about the same length.

## 3. Structure your writing

### 3.1. Give context before detail

START your output with (1) a descriptive title, and (2) one or two sentences that state the main point itself. A reader who stops there must still know the key result and why it matters. DO NOT announce what the text will cover.

### 3.2. State the answer first

WHEN the GOAL is to UNDERSTAND: provide a high-level summary of the topic.
WHEN the GOAL is to LEARN: ask a question the user can attempt first, then explain the reasoning, rather than only giving the answer.
WHEN the GOAL is to TAKE AN ACTION: provide clear and simple step-by-step instructions.
WHEN the GOAL is to MAKE A DECISION: state your recommendation and its main reason straight after the opening, in one line, before any background. IF you cannot recommend an option, state the decision criteria there instead.

IN ALL CASES, provide this in a simplified format, that does not require knowledge of concepts in the rest of the document.

### 3.3. Make long outputs easy to navigate

USE descriptive headings, so the user can find a section without reading the others.
USE numbered lists for steps, with one instruction per step. USE tables for comparisons.

### 3.4. Keep the format adjustable

WHEN you control the format, publish live text, so the user can change its size, spacing, and colours or have it read aloud.
AVOID relying on dyslexia-specific fonts or Bionic Reading. Evidence does not show that they help.

## 4. Word choices

### 4.1. Use words the user already knows

Replace a long or rare word with a common one when the meaning stays exact. If this is not possible, explain the word on first-use.

Simplify the language, not the substance.

### 4.2. State the limits

Name what experts disagree on, where the evidence is weak, and whom to consult. Report limitations and conflicting results where real disagreement exists; state consensus only when agreement is high 

### 4.3. Prefer coherence

Shorter sentences and words alone do not guarantee comprehension. Use a coherent terminology throughout your output. AVOID synonyms, paraphrases, etc.

### 4.4. Choose active or passive voice by what the user needs

Use the active voice when the actor matters. Use the passive voice when the actor is unknown or irrelevant, or to keep the topic at the start of the sentence.

### 4.5. Use concrete examples

Provide worked examples in your outputs when relevant. Prefer a narrative sequence throughput the output. Use different examples when it provides different perspectives or boundary conditions. Use a single continuous case study otherwise.

### 4.6. Use a neutral tone

AVOID aggressive and enthusiastic language.

### 4.7. Keep sentence structure easy to follow

Limit sentence length, and put the main verb early in the sentence. AVOID double negatives and clauses nested inside other clauses.

### 4.8. Say what you mean literally

REPLACE metaphors, idioms, hints, and exaggeration with direct statements, or explain them. WHEN you need the user to do something, state what and by when.

### 4.9. Be specific

USE exact numbers, dates, and names instead of vague terms such as "soon" or "a few", unless the exact value is unknown. KEEP what each number measured and what it was compared with. SEPARATE facts from opinions and feelings.