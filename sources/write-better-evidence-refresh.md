# Evidence refresh for write-better

Research findings for the better-ai skills  
Search date: 12 November 2026  
Updates: `writing-for-human-cognition.md` (open questions Q17 to Q22), `writing-for-neurodivergent-readers.md`, `llm-output-semantic-density.md`, `inclusivity.md`

**Most of write-better's rules hold, but three rest on claims the new evidence contradicts and should change: rule 4.1's reason (a synonym beside a hard word beats replacing it), rule 4.5 (prefer one continuous example), and Principle 3's wording (first-person beats impersonal uncertainty).** Several other rules rest on a single study that no later work has replicated, and none of the six open questions from the 2026-11-07 report has a full answer.

This run used the new research-better method. Workers added questions as they went, each key answer got a challenge question, and separate verifiers checked each claim against its source page. 50 questions were researched; 170 claims were recorded, 153 verified against the page and 17 not (mostly publisher blocks). Many sources were read only as abstracts, and each section says so where it matters.

## 1. Verdict for each rule

| Rule | Verdict | Change |
|---|---|---|
| P1 Length and polish raise confidence, not accuracy | Confirmed by two independent teams | None |
| P2 Structure helps; emphasis costs the rest | Structure: small gains. Emphasis cost: one paper, unreplicated | Soften the emphasis clause |
| P3 First-person uncertainty beats impersonal | One study; impersonal was not tested against first-person | Reword |
| P4 Imagining the reader does not help; checking does | First half confirmed; second half untested | None; note the gap |
| 1.1 Dialect and diagnosis | Confirmed | None |
| 1.3 Expertise makes writing abstract, technical, passive | Only "technical" is supported | Reword the reason |
| 2.1 Brevity instructions hurt false-premise correction | One benchmark, unreplicated | None; single-study |
| 2.3 / 3.1 Details in appendices; main point first | No support for layering; limits next to claims is consistent with the evidence | Consider dropping "move details to appendices" |
| 3.4 No decoration, no repeated text | Confirmed, effect small, depends on prior knowledge | None |
| 3.5 No dyslexia fonts or Bionic Reading | Confirmed for both | Bionic Reading now has evidence, not just design choice |
| 3.6 Bold a few key ideas | Supported when the writer chooses; dyslexia result is one small study | None |
| 4.1 Synonym beside a hard word beats replacing | **Contradicted** by one RCT | Change the reason; prefer replacing |
| 4.1 Experts skip limitations in plain text | Confirmed, one study | None |
| 4.3 Coherence over shorter sentences | Supported | Add that coherence mainly helps readers new to the topic |
| 4.4 Active or passive by need | No comprehension difference found | None |
| 4.5 Prefer one continuous example | **Contradicted** for transfer | Change the rule |
| 4.8 Say it literally | Gap is small once language skill is matched; no test of the fix | None |
| 4.9 Exact numbers | Confirmed for probabilities only | None |
| 5 Fluency is not understanding | Confirmed | None |
| 4.10 Inclusive wording | Not researched (low priority) | — |

## 2. Rules to change

### 2.1 Rule 4.1: replacing a hard word did better than explaining it beside the text

Rule 4.1 says "showing a simple synonym next to a hard word helped readers more than replacing the word". The only randomized test found points the other way. In a trial with 1,026 readers of plain-language summaries, replacing technical terms gave the most correct knowledge answers (68.84%), against 63.60% with no explanation and 62.03% with a glossary. The glossary raised readers' **perceived** understanding but not their knowledge (Kerwer et al., 2021). The replacement effect was p = .051 two-tailed; the authors tested it one-tailed.

Limits: Kerwer's glossary sat below the text, not next to the word. No study compared an inline synonym with replacement. A thesis on second-language readers found no difference between replacing a verb, adding a parenthetical definition, and leaving it unchanged, but measured only self-rated comprehension (Brewer, 2008).

**Suggested change:** prefer replacing the rare word with a common one when meaning stays exact. When the term must stay, explain it at first use, and drop the claim that a synonym beside it beats replacement.

The second claim in 4.1 holds. Readers familiar with a topic skipped details in overly plain summaries, most often the study limitations, while readers new to the topic did best with the simplest text (August et al., 2024). The outcome was skipping and self-rated understanding, not a test. None of the 20 works citing it tests the claim again.

### 2.2 Rule 4.5: two varied examples transferred better than one

Rule 4.5 says to prefer one continuous case study. In problem solving, two analogous examples gave 80% solutions on a new problem against 53% for one, and 45% against 21% before a hint (Gick & Holyoak, 1983, read in full). Students who studied varied worked examples transferred best (Paas & van Merriënboer, 1994, abstract). A meta-analysis of 57 experiments on comparing cases found d = .50 (Alfieri et al., 2013, abstract).

These are puzzles and problem-solving tasks, not explanatory prose. In the one text-based study found, three different examples gave no benefit over one repeated example, and the quality of the example mattered more (Funkhouser & Nicoladis, 2023, abstract).

**Suggested change:** when the user must apply the idea to new cases (GOAL LEARN or DO), give at least two examples that differ on the surface. One well-chosen running example is fine when the GOAL is to UNDERSTAND one situation.

### 2.3 Principle 3: first-person uncertainty was tested against no hedge, not against impersonal

Principle 3 says first-person uncertainty made readers rely less on wrong answers "than impersonal phrasing". In the study (404 people, medical questions), first-person hedges lowered agreement from 80.9% to 74.8% and raised accuracy from 63.9% to 72.8%, both significant against no hedge. Impersonal hedges moved the same way (77.6% agreement, 67.9% accuracy) but not significantly (Kim et al., 2024). The paper does not report first-person as significantly better than impersonal.

Challenge result: of 253 works citing it, 22 were screened and none repeats the comparison. Related work is mixed. Across languages, people rely more on confident wording, and Japanese participants relied more on all epistemic markers (Rathi et al., 2025). A study of 156 users found medium uncertainty beat high or low, which bears on how much to hedge, not on wording.

**Suggested change:** "First-person uncertainty, such as 'I'm not sure', lowered reliance on AI answers and raised accuracy in one study; impersonal phrasing moved the same way but less clearly." The rule itself (4.2, state uncertainty in the first person) can stay.

## 3. Rules to reword or soften

**P2, emphasis.** Signaling gains are small to medium (r = .17 for comprehension and transfer, larger for readers new to the topic), but the meta-analysis covers text-and-picture material (Richter et al., 2019, a dataset record carrying the meta-analysis abstract). Headings helped recall only for unfamiliar topics (Lorch & Lorch, 1996, abstract). The cost of emphasis to the rest of the text rests on Jansen (2014): lists improved recall of listed items in three of five studies and lowered recall of surrounding text in two. That paper could not be read at its source, and none of the 9 works citing it repeats the test. **Suggested:** keep the clause, but say it rests on one paper.

**1.3, expertise.** No study measured whether expertise makes a writer's own text more abstract or passive. Experts do mispredict what novices know (Hinds, 1999, abstract; Tullis & Feder, 2022), and jargon raised laypeople's satisfaction while lowering how understandable they found the text, in 6,698 participants (Cruz & Lombrozo, 2025, abstract). In corpora, experienced writers used more nominalisations than novices (Sarani & Talati, 2015), but passives and nominalisations did not separate skilled from weak legal writers (Hartig & Lu, 2014). **Suggested:** "Writers who know a topic misjudge what readers know, and jargon lowers lay readers' understanding."

**2.3 and 3.1, layering.** Two studies of layered or collapsible formats, both privacy notices, found no gain. Layered policies were answered faster but less accurately than natural-language ones (McDonald et al., 2009, 749 people, abstract). Collapsible layouts gave no comprehension advantage and more skipping (Xiao et al., 2026, 48 people, preprint). In consent forms, a medium-length form beat both a long form and a short summary form (Emanuel et al., 2026), which tests length, not layering. No study measured whether readers reach caveats placed in a lower layer. This supports the second half of 2.3 (keep each limit next to its claim) and gives no support to the first (move details to appendices).

**4.3, coherence.** In 181 adolescents, only lowering cohesion hurt multiple-choice comprehension; harder syntax and vocabulary hurt recall and reading rate by less (Spencer et al., 2018). Readability formulas explain about 6% (Flesch-Kincaid) to 10% (New Dale-Chall) of comprehension variance in adults (Crossley et al., 2023), though across 330 passages Flesch-Kincaid correlated r = −.76 with cloze scores (Cunningham et al., 2018). Coherence helped low-knowledge readers, while high-knowledge readers did better with a less coherent text in some tests (McNamara et al., 1996, abstract); a 2020 preprint with 511 students found no overall cohesion effect (McCarthy et al., 2020). **Suggested:** add that explicit links matter most for readers new to the topic.

**3.5, Bionic Reading.** It now has evidence: no reading-time gain (Snell, 2024, abstract) and no change in fixations or speed in 53 fluent readers (Beelders, 2025). Neither tested dyslexic readers. Dyslexia fonts gave no gain in two small studies of children (Wery & Diliberto, 2016; Kuster et al., 2018). Read-aloud tools gave a small-to-moderate comprehension gain for students with reading disabilities, d = .35 over 22 studies (Wood et al., 2018), which supports publishing live text.

## 4. Rules confirmed

**P1, length and polish.** Longer explanations raised users' confidence even when the extra length did not improve accuracy, and users told right from wrong answers near chance (AUC 0.54) (Steyvers et al., 2025). An independent team found explanations raised reliance on correct and incorrect answers alike, while sources and inconsistencies lowered reliance on wrong ones (Kim et al., 2025, abstract). Challenge result: nothing contradicts it, but a 24-person study found medium-length explanations helped people catch errors when the model was wrong (Friedman et al., 2026). Of 27 works citing Steyvers, none replicates the length effect.

**P4, the reader's knowledge.** Learning facts made people overestimate what novices know (Tullis & Feder, 2022). Instructions to take the other's perspective did not reduce the bias (Damen et al., 2018, 2020, abstracts). Feedback describing what the other person knew reduced it in one study (Damen et al., 2021, abstract), while Tullis and Feder found feedback worsened calibration. No study tests LLM writers or a "has the reader seen this?" check, so the second half of P4 rests on nearby evidence. **Correction to `agent-messages-and-user-context.md` line 6:** Tullis and Feder did not test people "told or paid" to ignore their knowledge; they cite earlier work for the payment result (line 26 of that file states this correctly).

**1.1, dialect and diagnosis.** ChatGPT's answers to non-standard English varieties were worse for stereotyping (19%), demeaning content (25%) and condescension (15%) (Fleisig et al., 2024, abstract). Accuracy, truthfulness and refusals were worse for users with lower English proficiency, lower education or from outside the US (Poole-Dayan et al., 2025, abstract). LLMs inferred personal attributes from text (Staab et al., 2024, abstract). When autism was disclosed, six LLMs shifted advice toward avoidance; Claude-3.5-Haiku advised declining a social invitation 74.4% of the time against 15.5% without disclosure, and the 11 autistic people interviewed were split on the result (Wohn et al., 2026).

**2.1, brevity and false premises.** System prompts asking for concise answers lowered resistance to misinformation in 11 of 17 models, by up to 20%. A manual check found 3 judge errors in 50 answers per condition, equal with and without the instruction (Le Jeune et al., 2025). The cause (brevity suppresses the justification needed to reject false content) is the authors' suggestion, not tested. Challenge result: no study repeats it on other models or with human scoring; none of the 7 works citing it varies conciseness. On reasoning tasks, brevity raised large models' accuracy (Hakim, 2026, abstract), so the effect depends on the task.

**3.4, decoration and repetition.** Seductive details lowered learning, g = −0.16 over 50 studies (Wu et al., 2026, abstract), with larger harm for learners without prior knowledge in an earlier meta-analysis read only through a summary. Redundancy harms most when identical information is given twice and for readers who know the topic (Trypke et al., 2023).

**3.6, bolding.** Bold keywords raised comprehension for readers with dyslexia (31 readers, p = .022) and not for controls; readers read only two 158-word Spanish texts (Rello et al., 2014, read in full). Highlighting chosen by an instructor improved comprehension (0.44), while highlighting chosen by learners did not (Ponce et al., 2022, abstract). No study replicates Rello or tests recall of the text left unbolded.

**4.4, voice.** No comprehension difference was found between active and passive voice in scientific reports (Rhodes, 1997, abstract), or for nominalisations, which cost eye-movement time but not accuracy (Venagli et al., n.d., abstract). The rule already leaves the choice to need.

**4.8, literal wording.** Autistic readers understood figurative language less well than peers (g = −0.57, 41 studies), but the gap was small and not significant when groups were matched on language ability (Kalandadze et al., 2018). An adaptation tool that replaced idioms among many other changes raised correct answers from 10.0 to 11.2 in 243 autistic readers (Cerga-Pashoja et al., 2019); the figurative step was not isolated. No study tests the literal rewrite alone.

**4.9, numbers.** Readers judged verbal probability terms higher than equivalent numbers (Büchter et al., 2014), and adding numeric ranges raised agreement with the intended meaning from 32% to 66% (Wintle et al., 2019). Less numerate people used a percentage better than verbal formats in a decision task (Dieckmann et al., 2009). No study of "a few" or "soon" was found.

**5, fluency.** LLM plain-language summaries rated as clear as human ones led to worse comprehension (Guo et al., 2025, preprint). A glossary raised perceived understanding without raising knowledge (Kerwer et al., 2021). LLM readability scores have been checked only against human ratings, not measured comprehension (Trott & Rivière, 2024; Cachola et al., 2025, abstracts), so no metric can replace a reader in the check step.

## 5. The six open questions from the 2026-11-07 report

| Question | Status now |
|---|---|
| Q17 Optimal length, heading depth, density | Still open. One 24-person study favours medium length for catching errors (Friedman et al., 2026). |
| Q18 Combined revisions | Contested. Bundled LLM simplification raised comprehension 3.9 points in 4,563 people (Guidroz et al., 2025); a human plain-language bundle gave no significant gain in youths (Stallwood et al., 2023); a GPT-4 rewrite of clinical guidelines omitted content in 20% and changed meaning in 12% of 153 subsections (Jones et al., 2026). The last supports rule 5's check against the original. |
| Q19 Effects over weeks of use | Still open. One five-session study of 12 people found trust dipped after a novelty phase and recovered (Kuang et al., 2026). |
| Q20 Language, expertise, accessibility | Partly answered. Simplification helped 37 adult L2 readers understand but slowed first reading (Rets & Rogaten, 2021); an older L2 study found no recall gain (Young, 1999). Simplification had no main effect for adults with intellectual disability (Buell et al., 2020). No study compares dyslexic, autistic, ADHD or low-literacy readers with others on one manipulation. |
| Q21 Progressive disclosure | Answered negatively for privacy notices (section 3). Untested for answers and reports. |
| Q22 Metrics that predict comprehension | Answered: readability formulas predict weakly to moderately; no LLM score is validated against comprehension. |

## 6. A rule write-better does not have

Explanations that give arguments for and against an answer lowered false trust and raised accuracy, the only one of several formats to do both (Palod et al., 2026, preprint, 125 people). In fact-checking, contrastive explanations cut over-reliance on wrong answers but did not beat a search engine (Si et al., 2023). Samples are small and tasks narrow. This could support a rule for high-stakes answers: give the main reason against your answer next to the reasons for it.

## 7. Limits and open questions

- **Single studies.** P1's length effect, P3, rule 2.1, the expert-skipping part of 4.1, and the dyslexia part of 3.6 each rest on one study that no citing work repeats.
- **Abstract-only reads.** Many sources were read as abstracts because publisher pages returned 403s or challenges. Claims verified only against an index copy of the abstract (Jansen, 2014; Yang et al., 2022; Prinz et al., 2020) are not used as source-verified.
- **Not found:** a comparison of dyslexic, ADHD, autistic or low-literacy readers with others on one text change; any study of caveats in a lower layer; inline synonym versus replacement; one versus several examples in explanatory prose; persistence over weeks.
- **Blocked:** the expertise reversal meta-analysis (Tetzlaff et al., 2025), which could show whether added detail helps novices and hurts experts.
- **Low-priority questions left open:** inclusive wording (rule 4.10), the 2024 plain-language vaccine trial, citing works of McDonald et al. (2009), and narrative feedback studies.

The research board is at `.research/write-better-evidence-refresh/` in the main checkout (not committed) and can be resumed.

## References

Alfieri, L., Nokes-Malach, T. J., & Schunn, C. D. (2013). Learning through case comparisons: A meta-analytic review. *Educational Psychologist, 48*(2), 87–113. https://api.openalex.org/works/doi:10.1080/00461520.2013.775712

August, T., Lo, K., Smith, N. A., & Reinecke, K. (2024). *Know your audience: The benefits and pitfalls of generating plain language summaries beyond the "general" audience* (arXiv:2403.04979). arXiv. https://arxiv.org/html/2403.04979v1

Beelders, T. R. (2025). Guiding the gaze: How Bionic Reading influences eye movements. *Journal of Eye Movement Research, 18*(5), 49. https://pmc.ncbi.nlm.nih.gov/articles/PMC12565662/

Brewer, B. A. (2008). *Effects of lexical simplification and elaboration on ESL readers' local-level perceived comprehension* [Master's thesis, Brigham Young University]. https://scholarsarchive.byu.edu/etd/1665

Büchter, R. B., Fechtelpeter, D., Knelangen, M., Ehrlich, M., & Waltering, A. (2014). Words or numbers? Communicating risk of adverse effects in written consumer health information: A systematic review and meta-analysis. *BMC Medical Informatics and Decision Making, 14*, 76. https://pmc.ncbi.nlm.nih.gov/articles/PMC4153005/

Buell, S., Langdon, P., Pounds, G., & Bunning, K. (2020). An open randomized controlled trial of the effects of linguistic simplification and mediation on the comprehension of "easy read" text by people with intellectual disabilities. *Journal of Applied Research in Intellectual Disabilities*. https://research-portal.uea.ac.uk/en/publications/an-open-randomized-controlled-trial-of-the-effects-of-linguistic-/

Cachola, I., Khashabi, D., & Dredze, M. (2025). Evaluating the evaluators: Are readability metrics good measures of readability? In *Proceedings of EMNLP 2025* (pp. 24011–24027). ACL Anthology. https://aclanthology.org/2025.emnlp-main.1225

Cerga-Pashoja, A., Gaete, J., Shishkova, A., & Jordanova, V. (2019). Improving reading in adolescents and adults with high-functioning autism through an assistive technology tool: A cross-over multinational study. *Frontiers in Psychiatry, 10*, 546. https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2019.00546/full

Crossley, S., Skalicky, S., Berger, C., & Heidari, A. (2023). *Assessing readability formulas in the wild*. Zenodo. https://zenodo.org/records/8436713/files/Assessing%20Readability%20Formulas%20in%20the%20Wild.pdf

Cruz, F., & Lombrozo, T. (2025). How laypeople evaluate scientific explanations containing jargon. *Nature Human Behaviour, 9*(10), 2038–2053. https://ideas.repec.org/a/nat/nathum/v9y2025i10d10.1038_s41562-025-02227-0.html

Cunningham, J. W., Hiebert, E. H., & Mesmer, H. A. (2018). Investigating the validity of two widely used quantitative text tools. *Reading and Writing, 31*, 813–833. https://textproject.org/wp-content/uploads/2022/07/Cunningham-Hiebert-Mesmer-2018.pdf

Damen, D., van der Wijst, P., van Amelsvoort, M., & Krahmer, E. (2018). The curse of knowing: The influence of explicit perspective awareness on the curse of knowledge. In *Proceedings of the 40th Annual Conference of the Cognitive Science Society*. https://research.tilburguniversity.edu/en/publications/the-curse-of-knowing-the-influence-of-explicit-perspective-awaren/

Damen, D., van der Wijst, P., van Amelsvoort, M., & Krahmer, E. (2020). Can the curse of knowing be lifted? The influence of explicit perspective-focus instructions on readers' perspective-taking. *Journal of Experimental Psychology: Learning, Memory, and Cognition*. https://research.tilburguniversity.edu/en/publications/can-the-curse-of-knowing-be-lifted-the-influence-of-explicit-pers/

Damen, D., van Amelsvoort, M., van der Wijst, P., Pollmann, M., & Krahmer, E. (2021). Lifting the curse of knowing: How feedback improves perspective-taking. *Quarterly Journal of Experimental Psychology, 74*(6). https://research.tilburguniversity.edu/en/publications/lifting-the-curse-of-knowing-how-feedback-improves-perspective-ta/

Dieckmann, N. F., Slovic, P., & Peters, E. M. (2009). The use of narrative evidence and explicit likelihood by decisionmakers varying in numeracy. *Risk Analysis, 29*(10), 1473–1488. https://pmc.ncbi.nlm.nih.gov/articles/PMC7159394

Emanuel, E. J., Lopez-Rico, S., Lijerón Ozisik, M., & Silvert, E. (2026). A randomized control trial of re-designed and shorter research informed consent forms to improve comprehension. *Clinical Trials, 23*(4), 421–429. https://pmc.ncbi.nlm.nih.gov/articles/PMC13451594/

Fleisig, E., Smith, G., Bossi, M., Rustagi, I., Yin, X., & Klein, D. (2024). *Linguistic bias in ChatGPT: Language models reinforce dialect discrimination* (arXiv:2406.08818). arXiv. https://arxiv.org/abs/2406.08818

Friedman, N., Nyanyo, A., Weatherwax, K., Wang, L., Zhu, C., Zhu, Z., & Mountford, S. J. (2026). *Not too short, not too long: How LLM response length shapes people's critical thinking in error detection* (arXiv:2603.06878). arXiv. https://arxiv.org/html/2603.06878

Funkhouser, A., & Nicoladis, E. (2023). A really good example helps learning about an abstract concept. *International Journal for the Scholarship of Teaching and Learning, 17*(1), 12. https://digitalcommons.georgiasouthern.edu/ij-sotl/vol17/iss1/12

Gick, M. L., & Holyoak, K. J. (1983). Schema induction and analogical transfer. *Cognitive Psychology, 15*, 1–38. https://gwern.net/doc/psychology/1983-gick.pdf

Guidroz, T., Ardila, D., Li, J., et al. (2025). *LLM-based text simplification and its effect on user comprehension and cognitive load* (arXiv:2505.01980). arXiv. https://arxiv.org/abs/2505.01980

Guo, Y., Sohn, J. H., Leroy, G., & Cohen, T. (2025). *Are LLM-generated plain language summaries truly understandable? A large-scale crowdsourced evaluation* (arXiv:2505.10409). arXiv. https://arxiv.org/html/2505.10409v1

Hakim, M. A. (2026). *Brevity constraints reverse performance hierarchies in language models* (arXiv:2604.00025). arXiv. https://arxiv.org/abs/2604.00025

Hartig, A. J., & Lu, X. (2014). Plain English and legal writing: Comparing expert and novice writers. *English for Specific Purposes, 33*(1), 87–96. https://pure.psu.edu/en/publications/plain-english-and-legal-writing-comparing-expert-and-novice-write/

Hinds, P. J. (1999). The curse of expertise: The effects of expertise and debiasing methods on prediction of novice performance. *Journal of Experimental Psychology: Applied, 5*(2), 205–221. https://api.openalex.org/works/doi:10.1037/1076-898x.5.2.205

Jones, M. D., Torgbi, M., & Tayyar Madabushi, H. (2026). Improving the understandability of clinical guidelines: Development and evaluation of a GPT-4-based pipeline. *Journal of Medical Internet Research, 28*, e81915. https://pmc.ncbi.nlm.nih.gov/articles/PMC12928683/

Kalandadze, T., Norbury, C., Nærland, T., & Næss, K.-A. B. (2018). Figurative language comprehension in individuals with autism spectrum disorder: A meta-analytic review. *Autism*. https://pmc.ncbi.nlm.nih.gov/articles/PMC5843023

Kerwer, M., Stoll, M., Jonas, M., Benz, G., & Chasiotis, A. (2021). How to put it plainly? Findings from two randomized controlled studies on writing plain language summaries for psychological meta-analyses. *Frontiers in Psychology, 12*. https://www.frontiersin.org/articles/10.3389/fpsyg.2021.771399

Kim, S. S. Y., Liao, Q. V., Vorvoreanu, M., Ballard, S., & Vaughan, J. W. (2024). *"I'm not sure, but...": Examining the impact of large language models' uncertainty expression on user reliance and trust* (arXiv:2405.00623). arXiv. https://ar5iv.labs.arxiv.org/html/2405.00623

Kim, S. S. Y., Vaughan, J. W., Liao, Q. V., Lombrozo, T., & Russakovsky, O. (2025). *Fostering appropriate reliance on large language models: The role of explanations, sources, and inconsistencies* (arXiv:2502.08554). arXiv. https://arxiv.org/abs/2502.08554

Kuang, E., Soure, E. J., Shen, L., Goyal, N., Fan, M., & Shinohara, K. (2026). *"It became my buddy, but I'm not afraid to disagree": A multi-session study of UX evaluators collaborating with conversational AI assistants* (arXiv:2603.13717). arXiv. https://arxiv.org/abs/2603.13717

Kuster, S. M., van Weerdenburg, M., Gompel, M., & Bosman, A. M. T. (2018). Dyslexie font does not benefit reading in children with or without dyslexia. *Annals of Dyslexia, 68*(1), 25–42. https://europepmc.org/article/PMC/PMC5934461

Le Jeune, P., Malézieux, B., Xiao, W., & Dora, M. (2025). *Phare: A safety probe for large language models* (arXiv:2505.11365). arXiv. https://arxiv.org/abs/2505.11365

Lorch, R. F., & Lorch, E. P. (1996). Effects of headings on text recall and summarization. *Contemporary Educational Psychology, 21*(3), 261–278. https://scholars.uky.edu/en/publications/effects-of-headings-on-text-recall-and-summarization/

McCarthy, K., Steinberg, J., Dreier, K., O'Reilly, T., Sabatini, J., & McNamara, D. S. (2020). *Revisiting the reverse cohesion effect: Influences of text cohesion, prior knowledge, and foundational reading skill on scenario-based comprehension* (EasyChair Preprint 3879). https://easychair.org/publications/preprint/4Krz

McDonald, A. M., Reeder, R. W., Kelley, P. G., & Cranor, L. F. (2009). A comparative study of online privacy policies and formats. In *Privacy Enhancing Technologies*. Springer. https://www.springerprofessional.de/doi/10.1007/978-3-642-03168-7_3

McNamara, D. S., Kintsch, E., Songer, N. B., & Kintsch, W. (1996). Are good texts always better? Interactions of text coherence, background knowledge, and levels of understanding in learning from text. *Cognition and Instruction, 14*(1), 1–43. https://doi.org/10.1207/s1532690xci1401_1

Paas, F. G. W. C., & van Merriënboer, J. J. G. (1994). Variability of worked examples and transfer of geometrical problem-solving skills: A cognitive-load approach. *Journal of Educational Psychology, 86*(1), 122–133. https://api.openalex.org/works/doi:10.1037/0022-0663.86.1.122

Palod, V., Biswas, U., & Kambhampati, S. (2026). *Evaluating the false trust engendered by LLM explanations* (arXiv:2605.10930). arXiv. https://arxiv.org/html/2605.10930

Ponce, H. R., Mayer, R. E., & Méndez, E. E. (2022). Effects of learner-generated highlighting and instructor-provided highlighting on learning from text: A meta-analysis. *Educational Psychology Review, 34*(2), 989–1024. https://investigadores.anid.cl//en/public_search/work?id=701573

Poole-Dayan, E., Roy, D., & Kabbara, J. (2025). *LLM targeted underperformance disproportionately impacts vulnerable users* (arXiv:2406.17737). arXiv. https://arxiv.org/abs/2406.17737

Rathi, N., Jurafsky, D., & Zhou, K. (2025). *Humans overrely on overconfident language models, across languages* (arXiv:2507.06306). arXiv. https://arxiv.org/html/2507.06306

Rello, L., Saggion, H., & Baeza-Yates, R. (2014). Keyword highlighting improves comprehension for people with dyslexia. In *Proceedings of the 3rd Workshop on Predicting and Improving Text Readability for Target Reader Populations*. ACL Anthology. https://aclanthology.org/W14-1204.pdf

Rets, I., & Rogaten, J. (2021). To simplify or not? Facilitating English L2 users' comprehension and processing of open educational resources in English using text simplification. *Journal of Computer Assisted Learning, 37*(3), 705–717. https://eprints.lancs.ac.uk/id/eprint/155908

Rhodes, S. (1997). *The active and passive voice are equally comprehensible in scientific writing* [Doctoral dissertation, University of Washington]. https://digital.lib.washington.edu/researchworks/items/214d8593-77d9-40e8-b735-d92d83fca1c4

Richter, J., Scheiter, K., & Eitel, A. (2019). *Data for meta-analysis: Signaling text-picture relations in multimedia learning* [Data set record carrying the abstract of the 2016 meta-analysis]. PsychArchives. https://psycharchives.org/handle/20.500.12034/2019

Sarani, A., & Talati, A. (2015). Nominalization in the writing of novice vs. experienced members of academic communities: A comparative discourse analysis. *Iranian Journal of Applied Language Studies, 7*(2), 205–232. https://ijals.usb.ac.ir/article_2678.html

Si, C., Goyal, N., Wu, S. T., Zhao, C., Feng, S., Daumé, H., III, & Boyd-Graber, J. (2023). *Large language models help humans verify truthfulness—except when they are convincingly wrong* (arXiv:2310.12558). arXiv. https://arxiv.org/abs/2310.12558

Snell, J. (2024). No, Bionic Reading does not work. *Acta Psychologica, 247*, 104304. https://research.vu.nl/en/publications/no-bionic-reading-does-not-work/

Spencer, M., Gilmour, A. F., Miller, A. C., Emerson, A. M., Saha, N. M., & Cutting, L. E. (2018). Understanding the influence of text complexity and question type on reading outcomes. *Reading and Writing, 32*(3), 603–637. https://pmc.ncbi.nlm.nih.gov/articles/PMC6455959

Staab, R., Vero, M., Balunović, M., & Vechev, M. (2024). *Beyond memorization: Violating privacy via inference with large language models* (arXiv:2310.07298). arXiv. https://arxiv.org/abs/2310.07298

Stallwood, L., Sammy, A., Prebeg, M., et al. (2023). Plain language vs standard format for youth understanding of COVID-19 recommendations: A randomized clinical trial. *JAMA Pediatrics, 177*(9), 956–965. https://jamanetwork.com/journals/jamapediatrics/fullarticle/2808109

Steyvers, M., Tejeda, H., Kumar, A., Belem, C., Karny, S., Hu, X., Mayer, L., & Smyth, P. (2025). *What large language models know and what people think they know* (arXiv:2401.13835). arXiv. https://arxiv.org/html/2401.13835v2

Trott, S., & Rivière, P. D. (2024). *Measuring and modifying the readability of English texts with GPT-4* (arXiv:2410.14028). arXiv. https://arxiv.org/abs/2410.14028

Trypke, M., Stebner, F., & Wirth, J. (2023). Two types of redundancy in multimedia learning: A literature review. *Frontiers in Psychology, 14*, 1148035. https://pmc.ncbi.nlm.nih.gov/articles/PMC10192876/

Tullis, J. G., & Feder, B. (2022). The "curse of knowledge" when predicting others' knowledge. *Memory & Cognition*. https://pmc.ncbi.nlm.nih.gov/articles/PMC9794110/

Venagli, I., Nardon, A., Dal Maso, S., Melloni, C., Piccinin, S., & Vender, M. (n.d.). *Investigating the impact of event nominalizations on reading behaviour and comprehension* [Workshop abstract]. https://tmalsburg.github.io/ComprehensionWorkshop/abstracts/VenagliEtAl2025

Wery, J. J., & Diliberto, J. A. (2016). The effect of a specialized dyslexia font, OpenDyslexic, on reading rate and accuracy. *Annals of Dyslexia, 67*(2), 114–127. https://pmc.ncbi.nlm.nih.gov/articles/PMC5629233

Wintle, B. C., Fraser, H., Wills, B. C., Nicholson, A. E., & Fidler, F. (2019). Verbal probabilities: Very likely to be somewhat more confusing than numbers. *PLoS One, 14*(4), e0213522. https://pmc.ncbi.nlm.nih.gov/articles/PMC6469752

Wohn, C., Çarık, B., Ding, X., Lee, S. W., Kim, Y.-H., & Rho, E. H. (2026). *"Are we writing an advice column for Spock here?" Understanding stereotypes in AI advice for autistic users* (arXiv:2601.12690). arXiv. https://arxiv.org/html/2601.12690

Wood, S. G., Moxley, J. H., Tighe, E. L., & Wagner, R. K. (2018). Does use of text-to-speech and related read-aloud tools improve reading comprehension for students with reading disabilities? A meta-analysis. *Journal of Learning Disabilities, 51*(1), 73–84. https://pmc.ncbi.nlm.nih.gov/articles/PMC5494021

Wu, Y., Wang, R., Cheng, C., & Wang, Z. (2026). *Seductive details, cognitive load, and academic achievements: A multi-level meta-analysis and MASEM* [Roundtable abstract]. AERA Annual Meeting. https://convention2.allacademic.com/one/aera/aera26/online_program_direct_link/view_paper/2273554/

Xiao, W., Wu, M., & Jo, Y. (2026). *Designing for understanding: How interface-level consent designs shape attention and understanding in privacy disclosures* (arXiv:2603.13747). arXiv. https://arxiv.org/html/2603.13747v1

Young, D. J. (1999). Linguistic simplification of SL reading material: Effective instructional practice? *The Modern Language Journal, 83*(3), 350–366. https://eric.ed.gov/?id=EJ591395
