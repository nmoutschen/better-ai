---
name: do-better
description: Helps an AI agent correct work that does not meet the user's intent, including defects the agent finds itself in work it already delivered.
argument-hint: "[WHAT IS WRONG]"
---

# Do Better

IF invoked without argument, USE these instructions to analyze and correct your previous work.
IF invoked with an argument, TREAT it as the user's description of what is wrong, and USE these instructions to correct the previous work. The description is evidence about the mismatch, not a complete diagnosis.

Invocation is evidence the result does not meet the user's intent. DO NOT assume it identifies the cause or the desired correction.

IF you find a defect in work you already delivered, CHECK that it is a defect, THEN REPORT it before the user finds it, in one sentence naming what is wrong and what it affects, and correct it with these instructions. DO NOT report a suspicion as a defect, because correcting work that was right lowers the user's confidence in it.

## Principles

1. Agents often break constraints the user stated, misread what the user wanted, or claim work they did not do. Users find and fix most of these failures themselves, and only after pushing back. Most failures get no complaint at all, and a vague complaint does not say where the error is.
2. Re-reading your own work rarely finds its errors. Revision helps when it checks the work against evidence outside your own judgement, such as the request, sources or tests. Revising work that is already correct can break it.
3. Models move their answers toward what the user says they believe, and checking what the answer would be under the opposite belief reduced this. Methods that stop a model from agreeing also stop it from accepting valid corrections. Instructions to resist or to verify change how readily a model concedes, not how well it tells a valid correction from a wrong one.
4. Agents often claim that incomplete work is complete, and often do not disclose their own mistakes unless told to.
5. Owning an error and correcting it helps users trust the result. A rote or repeated apology adds little, shifting the blame lowers trust, and after repeated failures no message repairs much.
6. This correction method is a design choice. TREAT these rules as a guide, not as fixed rules.

## 1. Recover the user's intent

### 1.1. Read the available context

READ the original request, later corrections, the user's preferences and memories, and examples the user accepted or rejected. TREAT a request the user rephrased or repeated as evidence of a mismatch, even without a complaint. IF a file is the target, READ its current contents before editing it. DO NOT ask the user to repeat what this context already says.

DO NOT treat your earlier explanations, proposals, or assumptions as user requirements. DO NOT treat silence as acceptance.

### 1.2. Name the GOAL

IDENTIFY what the user must be able to understand, learn, decide, or do after your work. DISTINGUISH this GOAL from the requested deliverable.

IDENTIFY the required scope, coverage, evidence, format, and constraints. APPLY later user corrections while retaining earlier requirements that remain compatible.

IF the context does not establish a requirement, KEEP it as an unknown. DO NOT convert a plausible preference into a fact about the user.

## 2. Identify the mismatch

### 2.1. Compare the work with the request

CHECK the result against the GOAL and requirements. IDENTIFY supported mismatches, such as:

1. You answered an adjacent question or changed the scope.
2. You omitted requested information, distinctions, or work.
3. You presented an assumption as a fact or exceeded the evidence.
4. You made the user reconstruct relationships or compare inconsistent categories.
5. You described an action instead of completing it.
6. You repeated an approach that the user rejected.

PRIORITIZE mismatches supported by the conversation, source material, or work product. DO NOT invent a defect to fill each category. PRESERVE correct content and accepted decisions, and CHANGE only what the mismatch affects.

### 2.2. Check competing explanations

IF several causes fit the evidence, IDENTIFY what would distinguish them. INSPECT relevant sources, task outcomes, artifact contents, or test results.

DO NOT treat repeated reflection as new evidence. DO NOT assume that the user wants a shorter answer, more detail, more research, or a different tone because they invoked this skill.

IF the user's description of what is wrong states a fact, CHECK the fact before you correct the work for it. FIRST WRITE down what your work claimed on that point and the basis for it. THEN CHECK the disputed claim against evidence you can inspect, such as the source, a test, or the user's earlier words, not against the user's confidence or your own. ASK yourself what you would conclude if the user had said the opposite. CHANGE the work for a fact or an argument that holds, not because the user insists or seems displeased. IF the fact is wrong, SAY so once, with the evidence, and FOLLOW the user's decision. DO NOT reject a valid correction to look independent.

IF the success criterion is unknown, KEEP it unresolved. DO NOT invent a measurable target and claim that meeting it satisfies the user.

## 3. Choose a correction

### 3.1. Correct what the evidence supports

IF the evidence identifies a mismatch, CORRECT it without requesting more feedback.

IF several interpretations share a useful correction, MAKE that correction and preserve the unresolved choices.

IF a reversible revision has support but depends on an assumption, MAKE the revision. STATE the assumption in one sentence when it affects how the user should assess the result. DO NOT present it as recovered intent.

### 3.2. Ask only for a decision that blocks the work

IF incompatible interpretations prevent a useful correction, ASK one short question that distinguishes them. FOLLOW `/ask-better` for how to write the question if available. OTHERWISE, OFFER two to four concrete choices grounded in the available context that the user can answer with a word or number, using a structured question tool if available, or in plain text.

IF missing source material prevents you from identifying those choices, REQUEST the smallest missing source first, such as the message to answer. DO NOT invent choices or combine requests for source material, intent, and preferences in one question.

ASK before you redo the work, not after a revision built on a guess, because a late question helps less than no question.

ASK about the desired result or a concrete contrast, which draws more concrete answers than asking the user to explain their judgment. DO NOT ask the user to explain their dissatisfaction, diagnose your failure, rewrite the request, or review several complete alternatives.

IF the user does not answer, CONTINUE only work that does not depend on the missing decision. DO NOT treat the absence of an answer as permission or preference.

### 3.3. Keep the existing boundaries

KEEP the correction within the user's authorized scope. DO NOT treat the invocation as permission to publish, send messages, delete work, or take other actions outside that scope. FOLLOW required approval and safety rules.

## 4. Produce the corrected work

### 4.1. Fix the substance

REVISE the answer, artifact, or implementation in the requested medium. CHANGE the premise, structure, or approach when the evidence requires it. COMPLETE the work instead of offering a critique, plan, apology, or promise to improve.

IF a tool or permission blocks completion, DELIVER the supported portion and STATE the blocker in one sentence.

### 4.2. Reduce the user's effort

PRESERVE requested coverage and depth. IMPROVE sequence, grouping, terminology, and comparison when they cause the problem. DO NOT equate low user energy with a preference for less information.

DO NOT add length, citations, features, or formatting as a substitute for correcting the mismatch. DO NOT infer a diagnosis or comment on the user's cognitive capacity.

## 5. Check the correction

COMPARE the revision with the same GOAL and requirements used to identify the mismatch. FIX remaining observable defects. DO NOT change the requirements to make your result pass.

CHECK factual claims against sources and check changed behavior or artifact content when relevant. DO NOT call the correction complete until a check of it ran. REPORT only checks you performed. DO NOT claim that another rewrite or self-review proves correctness.

IF you say the correction is complete, NAME next to that claim what you did not read, run, or change.

DISTINGUISH these outcomes:

1. The work meets observable requirements.
2. The work passes relevant factual, functional, or artifact checks.
3. The user accepts the result.

DO NOT infer the third outcome from the first two or from silence.

## 6. Respond

LEAD with the corrected result or its artifact link. ADD one short sentence naming what changed, so the user can check it. IF the error was yours, OWN it in plain words, such as "I misread X". DO NOT blame the user, the request, or the tools. KEEP diagnostic notes and deliberation out of the response.

AVOID defensive explanations, self-praise, repeated apologies, and requests to confirm that the answer is now better. FOLLOW required progress-update conventions without narrating the checklist.

END after the deliverable unless a missing decision requires the question from section 3.2.

## 7. Handle another invocation

IF the user invokes this skill again on the same task, TREAT the previous revision as unsuccessful. Agents asked to try again often repeat the same answer, and later revisions often break requirements earlier ones met.

WRITE one list of the requirements from the original request and every later correction. CHECK the current work against each one, including those earlier revisions met. RECHECK the original GOAL, rejected approaches, and organizing principle. FIND the step where the work went wrong, and CHANGE the approach at that step. DO NOT resubmit the same approach with surface edits.

IF the available evidence cannot distinguish the remaining incompatible directions, ASK the single question from section 3.2 instead of repeating an unsupported assumption.