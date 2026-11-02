---
name: research-better
description: Helps an AI agent researchg better. Avoids common bias and prior laundering when doing research to find more novel sources.
argument-hint: "TOPIC"
---

# Research Better

Guidance and instructions on how to perform a better research for the user.

IF invoked without arguments, use these instructions to restart a research.

## Principles

1. Large Language Models (LLMs) use a large training data set to both understand text and know facts. The user wants to use the AI agent for its ability to understand text, but not its training data.
2. AI agents have a training cut-off date and are not trained on the entirety of text available in the world. Relying too heavily on training data may lead to blind spots.
3. Knowing facts can lead to leading research questions with tools such as `WebSearch`. Results of those researches are highly susceptible to confirmation bias and blind spots.

## Methodology

### 1. Topic confirmation

Identify the TOPIC provided by the user and list all possible MEANINGs. Use context clues (previous prompts from the user, previous discussions, local repository, context, etc.) to identify reasonable meanings.

IF the topic is ambiguous (multiple possible meanings, even with context), explain the different meanings to the user and then ASK (using `AskUser`/`AskUserQuestion`) which one they meant. Use this structure when explaining the meaning:

```
## Meaning

[Definition as you understand it]

> Worked example when relevant.
```

### 2. Broadening searches

Write different ways to express the MEANING for the research. Use these (AND ONLY THESE) in a first set of `WebSearch`es. Use the results of those searches to **identify new search terms** and expand beyond the direction implied by the initial queries.

### 3. Create a register of open questions

Create a register of **open questions** that came from the user's question/research TOPIC, the identified MEANING, and the broadening searches. You will add new questions there as you continue to research.

Here are a set of starter questions:

1. What terms do sources use for this topic, and what does each term refer to?
2. Which cases, contexts, populations, or periods do the sources address?
3. What claims or examples bear on the question, and where do they originate?
4. How do sources explain, interpret, or classify the topic?
5. Where do sources agree or disagree?

### 4. Iterative searches

Use the **open questions** register to shape your next `WebSearch`es. Use the output of each search to find potential questions within the confines of the TOPIC and MEANING. When evaluating the output, mark both (1) new information, including their source and the source trustworthiness, and (2) new questions that emerge from that output. Add those new questions to your **open questions** register.

Keep iterating until the **open questions** register is empty.

### 5. Present your findings

Use the `/write-better` skill to present your research findings to the user.