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

### 1.2. Name the GOAL

IF the user specified a personal GOAL, USE this as the ultimate outcome of your output.
IDENTIFY what is the main GOAL of your writing:

1. The user UNDERSTANDS or LEARNS something new.
2. The user TAKES AN ACTION thanks to the output.
3. The user MAKES A DECISION thanks to the output.

IF you cannot IDENTIFY the main GOAL, ASK the user, using `AskUser`:

```
[question] How will you use this writing?
[option] I understand something new.
[option] I can take the right action.
[option] I can make a decision.
```

### 1.3. Assume your draft is unclear

IF you are doing research on a particular topic, you are loading your context with specialized information not available to the user. Expertise makes the writer more abstract, more technical, and more passive.

## 2. Include only what the user needs

### 2.1. Cut interesting but irrelevant material

DELETE anecdotes, unsupported conclusions, research details, dead-ends, and trivia that do not serve the user's GOAL.

### 2.2. Repair reasoning gaps

STATE causal and logical links between propositions. EXPAND/EXPLAIN new concepts when they first appear.

### 2.3. Separate additional details

MOVE additional details that do not directly support the GOAL of the user to appendices.

## 3. Structure your writing

### 3.1. Give context before detail

START your output with (1) a descriptive title, and (2) one or two sentences explaining what the text is about and why it matters to the user's GOAL.

### 3.2. State the answer first

WHEN the GOAL is to UNDERSTAND or LEARN: provide a high-level summary of the topic.
WHEN the GOAL is to TAKE AN ACTION: provide clear and simple step-by-step instructions.
WHEN the GOAL is to MAKE A DECISION: provide the recommendations or decision criteria upfront.

IN ALL CASES, provide this in a simplified format, that does not require knowledge of concepts in the rest of the document.

## 4. Word choices

### 4.1. Use words the user already knows

Replace a long or rare word with a common one when the meaning stays exact. If this is not possible, explain the word on first-use.

### 4.2. State the limits

Name what experts disagree on, where the evidence is weak, and whom to consult. Report limitations and conflicting results where real disagreement exists; state consensus only when agreement is high 

### 4.3. Prefer coherence

Shorter sentences and words do not simplify comprehension. Use a coherent terminology throughput your output. AVOID synonyms, paraphrases, etc.

### 4.4. Choose active or passive voice by what the user needs

Use the active voice when the actor matters. Use the passive voice when the actor is unknown or irrelevant, or to keep the topic at the start of the sentence.

### 4.5. Use concrete examples

Provide worked examples in your outputs when relevant. Prefer a narrative sequence throughput the output. Use different examples when it provides different perspectives or boundary conditions. Use a single continuous case study otherwise.

### 4.6. Use a neutral tone

AVOID aggressive and enthusiastic language.