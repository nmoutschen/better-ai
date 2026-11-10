# Pre-questions, for an AI agent that teaches one user

Research register · Search date: 10 November 2026

**Scope.** What evidence shows that asking learners questions before they study the material helps them learn, under what conditions, and whether an AI agent that teaches one user (the `teach-better` skill) should use it. Sources call this prequestioning or pretesting.

**Status.** 6 questions closed, all answered. One preregistered meta-analysis and one review cover the main effect. Evidence on LLM tutors comes from one lab's small studies and one study of LLM-written questions.

Asking learners to guess answers before they study raises their later scores on those same questions, g = 0.54 across 97 effects. It does almost nothing for material that was not asked about, g = 0.04 (St. Hilaire et al., 2024). The benefit is larger when learners write a guess than when they only read the question (g = 0.65 against 0.22). Questions written by ChatGPT worked as well as questions written by people (Pan et al., 2025). Learners believe that reading works better, even after experiencing both (Pan & Rivers, 2023).

## 1. What the technique is

- Pan and Carpenter (2023) group prequestioning, pretesting, errorful generation and failed testing under "pre-instruction testing". The learner attempts questions on material not yet studied, then studies the material, then is tested.
- Variants differ in timing. Some ask all questions before a text, video or lecture. Others ask item by item with the answer shown at once. Others pause after each segment (Pan & Carpenter, 2023).
- Productive failure and invention activities are related. They use complex problems instead of factual questions, often in groups (Pan & Carpenter, 2023). `teach-better` already asks for an attempt before the worked example on complex problems (section 3.1).

## 2. Evidence, with how strong it is

### 2.1. Size of the effect

**Evidence: moderate, from a preregistered meta-analysis; narrow in scope.**

- "This preregistered meta-analysis demonstrated a moderate specific effect (g = 0.54, k = 97) but a virtually nonexistent general effect (g = 0.04, k = 91)" (St. Hilaire et al., 2024). The specific effect is on the questions asked in advance. The general effect is on other material in the same lesson.
- 85% of the specific effects were positive, 15 studies showed negative effects, and heterogeneity was high (I² = 80%) (St. Hilaire et al., 2024).
- Guessing mattered: the specific effect was g = 0.65 when learners guessed, against 0.22 when they only read the questions (St. Hilaire et al., 2024).
- Factual pre-questions gave a larger effect (g = 0.58) than conceptual ones that required inference (g = 0.28). The difference was marginal, p = .073 (St. Hilaire et al., 2024).

### 2.2. Conditions

**Evidence: from one review and one meta-analysis.**

- The benefit appears most clearly for facts stated directly in the material, when the learner then studies the correct answers (Pan & Carpenter, 2023).
- Most studies used undergraduates with little prior knowledge, in labs. Evidence on adults outside university and on prior knowledge as a moderator is thin (Pan & Carpenter, 2023).
- In a classroom study, a question asked at the start of class and repeated at the end gave no extra benefit over a new question at the end. The authors suggest placing such questions "at the end of class" (Geller et al., 2017).
- For children aged 5 to 6, pre-questions helped only with immediate feedback (Yu et al., 2025).

### 2.3. Delivery with AI

**Evidence: small studies, mostly from one lab.**

- In small randomized classroom studies, students who attempted a problem before getting ChatGPT's help scored 91.85 on a later test, against 78.59 for students who got help at once (Akgun & Toker, 2024, preprint).
- Pre-questions that an AI adapted to each student beat fixed questions on an exploratory regression task (76.87 against 69.65). They did not on a computational task (Akgun & Toker, 2025, preprint).
- "AI-generated questions and human-generated questions were equally effective at promoting learning." Questions from a basic prompt worked as well as questions from an elaborate one (Pan et al., 2025).
- An LLM tutor built for productive failure was tested with 17 students for 15 minutes. It measured how faithfully the tutor followed the method, not learning. Students rated it less helpful than a plain tutor (Puech et al., 2024, preprint).

### 2.4. How learners judge it

**Evidence: consistent.**

- Learners "are predisposed to believing that reading is more effective even after repeatedly experiencing both techniques, and need support before they recognize that pretesting is more beneficial" (Pan & Rivers, 2023).

## 3. Where the evidence disagrees

- **Effect beyond the questions asked.** The meta-analysis finds almost none. One study with ChatGPT-written questions found a benefit on untested questions as well (d = 0.78) (Pan et al., 2025).
- **Added value next to retrieval practice.** In the classroom study, pre-questions added nothing when the class already ended with retrieval questions (Geller et al., 2017).
- **Costs.** No study read here measured the time cost. The cost found is learners' dislike and their belief that the technique works worse.

## 4. What this means for `teach-better`

These are inferences from the evidence above, not tested rules. The report does not change the skill.

1. **Ask about what the GOAL needs.** The benefit is mostly limited to the questions asked. Pre-questions should target the key facts and rules of the chunk that a later quiz will test.
2. **Ask for a guess, not just a reading of the question.** Writing a guess roughly tripled the effect.
3. **Teach the answers in the same chunk.** The benefit depends on the learner studying the correct answers afterwards. Each pre-question needs its answer on a later card, and the agent can point back to the question there.
4. **Prefer factual questions.** Questions that need inference before the material helped less.
5. **Keep it separate from a quiz.** A pre-question is a guess about unseen material, so it gets no verdict, and the agent should say that wrong guesses are expected. Quizzes stay closed-book tests of what was taught.
6. **Expect the learner to doubt it.** Learners judge pre-questions as less useful than reading. A one-line explanation is a design choice; experience alone did not change their view.
7. **The agent can write the questions.** LLM-written pre-questions matched human-written ones, but the agent still needs to check them against the material, as for any card.
8. **It may add little on top of the skill's other practice.** In one classroom it added nothing when retrieval questions already ended the lesson, and the skill already uses practice problems and quizzes.

## 5. Method

- Research board: `.research/pre-questions/` (not committed). It holds every question, claim and source, with each source marked by how it was read.
- Workers on a cheaper model researched the questions. The coordinator checked every quote on the board against its source.
- Abstract-only sources are marked as such on the board. Akgun and Toker (2026) was read as an abstract only and is not used above.

## 6. Open questions

- **A second meta-analysis** (King-Shepard) and Chan et al. (2018) were not found or not read.
- **Pre-questions in a multi-turn LLM tutor**, against no pre-questions, with a delayed test. No such study was found.
- **Time cost.** No study measured it directly.
- **Adults outside university.** Evidence is thin.

## 7. Sources

Akgun, M., & Toker, S. (2024). *Evaluating the effect of pretesting with conversational AI on retention of needed information*. arXiv. https://arxiv.org/abs/2412.13487

Akgun, M., & Toker, S. (2025). *Struggle first, prompt later: How task complexity shapes learning with GenAI-assisted pretesting*. arXiv. https://arxiv.org/abs/2504.10249

Geller, J., Carpenter, S. K., Lamm, M. H., Rahman, S., Armstrong, P. I., & Coffman, C. R. (2017). Prequestions do not enhance the benefits of retrieval in a STEM classroom. *Cognitive Research: Principles and Implications, 2*, 42. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5655599/

Pan, S. C., & Carpenter, S. K. (2023). Prequestioning and pretesting effects: A review of empirical research, theoretical perspectives, and implications for educational practice. *Educational Psychology Review, 35*, 97. https://doi.org/10.1007/s10648-023-09814-5

Pan, S. C., & Rivers, M. L. (2023). Metacognitive awareness of the pretesting effect improves with self-regulation support. *Memory & Cognition, 51*(6), 1461–1480. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9839203/

Pan, S. C., Schweppe, J., Teo, A. Z. J., Indrajaya, A., & Wenzel, N. (2025). Using ChatGPT-generated prequestions to improve memory and text comprehension. *Journal of Applied Research in Memory and Cognition*. https://doi.org/10.1037/mac0000254

Puech, R., Macina, J., Chatain, J., Sachan, M., & Kapur, M. (2024). *Towards the pedagogical steering of large language models for tutoring: A case study with modeling productive failure*. arXiv. https://arxiv.org/abs/2410.03781

St. Hilaire, K. J., Chan, J. C. K., & Ahn, D. (2024). Guessing as a learning intervention: A meta-analytic review of the prequestion effect. *Psychonomic Bulletin & Review, 31*, 411–441. https://par.nsf.gov/servlets/purl/10511812

Yu, L., Heng, J. T., Arden-Gardner, L. S., Ding, X. P., & Pan, S. C. (2025). Prequestioning with feedback fosters learning in young children. *Learning and Instruction, 100*, 102187. https://sc-pan.github.io/pdf/YHADP_2025.pdf
