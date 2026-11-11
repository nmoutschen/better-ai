# Keeping developers' understanding when AI writes code

Research findings · Search date: 11 November 2026

AI coding help can raise speed while lowering what the developer understands of the code. The one randomized trial that measured both found lower comprehension with AI and no significant average speedup. How the developer used the AI mattered more than whether they used it: asking for explanations or conceptual answers kept understanding, while delegating the code or the debugging lost it. No study has tested an agent behaviour, such as change summaries or asking the developer to predict, on working developers in their own codebase. The evidence is a handful of small studies, mostly of students and short sessions.

**Scope.** How an AI coding agent can work with a developer so the developer keeps or gains understanding of, and skill in, their own codebase. Covers what the agent does at runtime: explanations, involving the user, handing work back, and summaries of changes. General tutoring on a new topic is covered by the `teach-better` reports and not repeated here. These findings are input for a `code-better` skill. This report does not design it.

**Status.** All 9 high- and medium-priority questions are answered, two of them contested (sections 1 and 6). One low-priority question on non-English studies is still open. 23 sources, 60 claims. I checked each claim's quote against its source page: 59 are on the page; one, from a news report, could not be checked and is marked below. Two of the 23 sources are pages about other sources: a newsletter and a vendor guide. Neither is used as evidence.

## Findings at a glance

| Finding | Evidence | Evidence boundary |
|---|---|---|
| AI help lowered comprehension when learning a new library | One RCT, 52 developers: quiz 50% vs 67% | Immediate test, one library |
| Other lab studies found no average effect; use decided it | Two pre-registered experiments; small Copilot studies | Students; abstracts |
| Asking for explanations or concepts kept understanding; delegating lost it | Same RCT (pattern groups of 2–7) and one lab study | Correlational |
| Developers who verified code (write, then view) understood more | One study, 15 graduate students | Small |
| Questioning the developer about decisions cut misunderstandings of their own code by 79% | One preprint, N = 14 | Single study |
| Forcing deliberate thought cut over-reliance, but users disliked it | One study, N = 199, not coding | Off-domain |
| Experienced developers believed AI sped them up when it slowed them down | One RCT | Speed only, not comprehension |
| Speed gains are largest for less experienced developers | Field RCTs, thousands of developers | **Contested** against the RCT above |
| "Comprehension debt" and "cognitive surrender" | Essays | Concepts, not measured in codebases |

## 1. Effect on comprehension and skill (contested)

In a randomized trial, developers learning a new asynchronous Python library with AI help scored 50% on a comprehension quiz, against 67% for those who coded by hand. The largest gap was on debugging questions (Shen & Tamkin, 2026a). The AI group got no significant average speedup (Shen & Tamkin, 2026b). Learning was lower with AI at every level of prior experience (1–3, 4–6, and 7+ years) (Shen & Tamkin, 2026b).

Other studies found no average loss.

- Two pre-registered lab experiments found no overall effect of LLM access on learning. The effect depended on use: using the LLM in place of the work reduced understanding, and asking it for explanations increased it (Lehmann et al., 2024). The domain may not be programming only.
- Novices given Codex during a structured course did not do worse on later manual code modification, and did slightly, not significantly, better on a one-week retention test (Kazemitabaar et al., 2023). In that course each AI-aided task was followed by a manual modification task, which the AI never wrote. Debugging, where the trial above found its largest gap, was not tested. No paper explains the disagreement; this design comparison is mine.
- In an unfamiliar codebase, 15 graduate students with Copilot performed better but did not comprehend more (Qiao et al., 2025). Ten students on brownfield tasks were 35% faster with Copilot but "reported concerns about not understanding how or why Copilot suggestions work" (Shihab et al., 2025).

## 2. Which ways of using AI keep understanding

The trial in section 1 classified how each participant used the AI (Shen & Tamkin, 2026b).

| Pattern | What the developer did | Quiz score |
|---|---|---|
| Generation then comprehension | Generated code, then asked follow-up questions | High (65%+) |
| Hybrid code and explanation | Asked for code with explanations | High |
| Conceptual inquiry | Asked only conceptual questions, fixed errors alone | High; second fastest overall |
| AI delegation | Had the AI write the code | Low (under 40%); fastest |
| Progressive reliance | Started alone, handed over more and more | Low |
| Iterative AI debugging | Had the AI fix errors instead of explaining them | Low; also slow |

"Generation then comprehension" differs from delegation only in the follow-up questions. Typing the AI's code by hand instead of pasting it made no notable difference. **The pattern groups have 2 to 7 people each, and the authors state the link is not causal.**

Two other studies agree in direction. Participants who verified more often, writing code then viewing it, did so "4.7 times more often than participants with lower comprehension" (Qiao et al., 2025). Novices who already knew what code they intended used AI to go faster; those who struggled had their metacognitive difficulties compounded and an "illusion of competence" (Prather et al., 2024).

## 3. Agent behaviours and tool designs tested

- **Questioning the developer about decisions.** Aporia asks the programmer design questions and encodes the answers as tests. Mismatches between what programmers said their code did and what it did "were 79% less likely with Aporia" than with Claude Code: 4.7% against 12.1% of described policies (Kasibatla et al., 2026). N = 14, preprint.
- **Editing a summary instead of the code.** Having developers edit a generated summary of the code supported comprehension and control. Direct instructions were more flexible and easier. Developers chose by urgency and by whether they wanted to learn (Tang et al., 2025). 15 developers; comprehension was not tested.
- **Cognitive forcing.** Designs that make people think before seeing the AI's answer reduced over-reliance more than explanations did, but were rated least favourably. They helped people high in Need for Cognition most (Buçinca et al., 2021). This was a non-coding decision task, N = 199.
- **Guardrail tutors.** A tutor with staged hints, explain-first prompting and suppressed answers improved problem solving against a no-AI control (Sambetova & Zhaidakbayeva, 2026). It was not compared with unrestricted AI.

**Gap.** No controlled study tested change summaries, predict-before-reveal, or asking the developer to write a part, on working developers.

## 4. How developers review AI-written code

- Of 13 experienced developers observed using agents, 9 carefully reviewed every change and kept control by planning. They said strong comprehension and debugging skills are needed to use agents well, and that accountability made them review output themselves (Huang et al., 2026).
- In a qualitative study of vibe coding, heavy review of agent output was exhausting and undermined flow; some developers handed review back to the AI (Pimenova et al., 2026).
- In open-source repositories, AI-co-authored PRs from non-owners drew the least feedback, and about 80% were merged without explicit review (Gao et al., 2026).
- In a lab study, participants with an AI assistant wrote less secure code and were more likely to believe it was secure (Perry et al., 2023).

**Gap.** No controlled study of automation bias when people review AI-written code was found.

## 5. Comprehension debt and cognitive surrender

These terms come from essays, not measurements.

- Osmani (2026) defines comprehension debt as "the growing gap between how much code exists in your system and how much of it any human being genuinely understands."
- Storey (2026) defines cognitive debt as the erosion of shared understanding across a team, separate from technical debt and from intent debt (lost rationale). She separates cognitive offloading, a rational delegation of a discrete task, from cognitive surrender, adopting AI output with minimal scrutiny. Her motivating evidence is one student-team anecdote.
- The surrender evidence Storey cites is a logic-puzzle experiment, not coding. A news report gives accuracy of 71% when the AI was right and about 31% when it was wrong (Dolan, 2026). *Unverified*: the article text could not be checked, and the primary paper was not read.

No study measured comprehension debt or code ownership in a real codebase.

## 6. Productivity, experience, and the trade-off (contested)

- Pooled field RCTs at Microsoft, Accenture and a Fortune 100 company found 26.08% more completed tasks with an AI assistant. Less experienced developers adopted it more and gained more (Cui et al., 2025).
- Experienced developers working in their own mature repositories were 19% slower with AI, while believing it had made them about 20% faster (Becker et al., 2025). Comprehension was not measured.
- In the learning trial, only the fully delegating group was clearly faster, and it lost the most learning (Shen & Tamkin, 2026b).

No study measured productivity and comprehension on the same field tasks. LLM access widened the gap between students with low and high prior knowledge (Lehmann et al., 2024), so the developers who gain most speed may be the ones with most to learn.

## 7. What developers say they want

Developers want to hand off tedious work such as tests (Sergeyuk et al., 2024). They want to customize when suggestions and explanations appear, at what granularity, and with what content (Desolda et al., 2025). Some avoid LLMs to keep learning independently or because they worry about over-reliance (Akhoroz & Yildirim, 2025). Experienced agent users enjoy agents while they stay in control (Huang et al., 2026). These are self-reports from small or self-selected samples. No study tested whether these preferences cost productivity.

## 8. What the research could not find

- Any test of change summaries, predict-before-reveal, or "write this part yourself" on professional developers in their own codebase.
- Retention tests beyond one week, and any study of the usage patterns in section 2 on real work.
- A study comparing novices and professionals on comprehension in the same task.
- A measure of team-level comprehension debt or ownership.
- A primary paper for a 69-participant study reported by a newsletter; it was not used.
- Studies in languages other than English (low-priority question, open).

The research board is in `.research/code-better-elevation/`.

## References

Akhoroz, M., & Yildirim, C. (2025). *Conversational AI as a coding assistant: Understanding programmers' interactions with and expectations from large language models for coding*. arXiv. https://arxiv.org/abs/2503.16508

Becker, J., Rush, N., Barnes, B., & Rein, D. (2025). *Measuring the impact of early-2025 AI on experienced open-source developer productivity*. arXiv. https://arxiv.org/abs/2507.09089

Buçinca, Z., Malaya, M. B., & Gajos, K. Z. (2021). To trust or to think: Cognitive forcing functions can reduce overreliance on AI in AI-assisted decision-making. *Proceedings of the ACM on Human-Computer Interaction, 5*(CSCW1), Article 188. https://arxiv.org/abs/2102.09692

Cui, K. Z., Demirer, M., Jaffe, S., Musolff, L., Peng, S., & Salz, T. (2025). *The effects of generative AI on high-skilled work: Evidence from three field experiments with software developers* [Working paper draft]. MIT Economics. https://economics.mit.edu/sites/default/files/inline-files/draft_copilot_experiments.pdf

Desolda, G., Esposito, A., Greco, F., et al. (2025). *Understanding user mental models in AI-driven code completion tools: Insights from an elicitation study*. arXiv. https://arxiv.org/abs/2502.02194

Dolan, E. W. (2026, April 30). High trust in AI leaves individuals vulnerable to "cognitive surrender," study finds. *PsyPost*. https://www.psypost.org/high-trust-in-ai-leaves-individuals-vulnerable-to-cognitive-surrender-study-finds/

Gao, H., Banyongrakkul, P., Guan, H., Zahedi, M., & Treude, C. (2026). *On autopilot? An empirical study of human-AI teaming and review practices in open source*. arXiv. https://arxiv.org/abs/2601.13754

Huang, R., Reyna, A., Lerner, S., Xia, H., & Hempel, B. (2026). *Professional software developers don't vibe, they control: AI agent use for coding in 2025*. arXiv. https://arxiv.org/abs/2512.14012

Kasibatla, S. R., Rothkopf, R., Peleg, H., Pierce, B. C., Lerner, S., Goldstein, H., & Polikarpova, N. (2026). *Decision-oriented programming with Aporia*. arXiv. https://arxiv.org/abs/2604.05203

Kazemitabaar, M., Chow, J., Ma, C. K. T., Ericson, B. J., Weintrop, D., & Grossman, T. (2023). Studying the effect of AI code generators on supporting novice learners in introductory programming. In *Proceedings of the 2023 CHI Conference on Human Factors in Computing Systems*. https://arxiv.org/abs/2302.07427

Lehmann, M., Cornelius, P. B., & Sting, F. J. (2024). *AI meets the classroom: When do large language models harm learning?* arXiv. https://arxiv.org/abs/2409.09047

Osmani, A. (2026, March 14). *Comprehension debt – the hidden cost of AI generated code*. AddyOsmani.com. https://addyosmani.com/blog/comprehension-debt/

Perry, N., Srivastava, M., Kumar, D., & Boneh, D. (2023). Do users write more insecure code with AI assistants? In *Proceedings of the 2023 ACM SIGSAC Conference on Computer and Communications Security*. https://arxiv.org/abs/2211.03622

Pimenova, V., Fakhoury, S., Bird, C., Storey, M.-A., & Endres, M. (2026). *Good vibrations? A qualitative study of co-creation, communication, flow, and trust in vibe coding*. arXiv. https://arxiv.org/abs/2509.12491

Prather, J., Reeves, B., Leinonen, J., MacNeil, S., Randrianasolo, A. S., Becker, B., Kimmel, B., Wright, J., & Briggs, B. (2024). *The widening gap: The benefits and harms of generative AI for novice programmers*. arXiv. https://arxiv.org/abs/2405.17739

Qiao, Y., Shihab, M. I. H., Haque, S., & Hundhausen, C. (2025). *Faster but not wiser: GitHub Copilot decouples programming performance from code comprehension in brownfield tasks*. arXiv. https://arxiv.org/abs/2511.02922

Sambetova, R., & Zhaidakbayeva, L. (2026). A pedagogical model of generative AI tutoring in informatics education and its effects on problem-solving quality and academic independence. *STEM Education, 6*(5), 927–951. https://aimspress.com/aimspress-data/steme/2026/5/PDF/steme-06-05-037.pdf

Sergeyuk, A., Golubev, Y., & Bryksin, T. (2024). *Using AI-based coding assistants in practice: State of affairs, perceptions, and ways forward*. arXiv. https://arxiv.org/abs/2406.07765

Shen, J. H., & Tamkin, A. (2026a, January 29). *How AI assistance impacts the formation of coding skills*. Anthropic. https://www.anthropic.com/research/AI-assistance-coding-skills

Shen, J. H., & Tamkin, A. (2026b). *How AI impacts skill formation*. arXiv. https://arxiv.org/abs/2601.20245

Shihab, M. I. H., Hundhausen, C., Tariq, A., Haque, S., Qiao, Y., & Mulanda, B. (2025). *The effects of GitHub Copilot on computing students' programming effectiveness, efficiency, and processes in brownfield programming tasks*. arXiv. https://arxiv.org/abs/2506.10051

Storey, M.-A. (2026). *From technical debt to cognitive and intent debt: Rethinking software health in the age of AI*. arXiv. https://arxiv.org/abs/2603.22106

Tang, N., Smith, E., Huang, Y., McMillan, C., & Li, T. J.-J. (2025). *Exploring direct instruction and summary-mediated prompting in LLM-assisted code modification*. arXiv. https://arxiv.org/abs/2508.01523
