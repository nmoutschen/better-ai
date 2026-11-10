# Deep explanatory questions, for an AI agent that teaches one user

Research register · Search date: 10 November 2026

**Scope.** What evidence shows that deep explanatory questions improve learning, under what conditions, and whether an AI agent that teaches one user (the `teach-better` skill) should use them. Deep explanatory questions are why, how and what-if questions that make the learner build explanations. The report covers elaborative interrogation and deep-level reasoning questions in tutoring. It excludes asking the learner to explain their own answer to a practice problem, which `teach-better` already does.

**Status.** 9 questions closed. 6 answered, 2 contested, 1 not found. The meta-analytic evidence is moderate. Evidence on deep or delayed outcomes is thin. No study tested an LLM that asks why or how questions with a later test taken without AI.

Asking the learner "why is this true?" about a stated fact or rule has a moderate average effect, d = 0.56 across 254 cases (Donoghue & Hattie, 2021). Most of that evidence measures recall of facts at short delays. It works best when the learner generates the explanation, and it fails when the learner cannot produce a good one. An agent could add such prompts to its explanation cards. It would then need to check each explanation the learner writes, as it already checks practice answers.

## 1. What the techniques are

| Technique | Who asks | Who answers | Origin |
|---|---|---|---|
| Elaborative interrogation | The tutor or the material, after each stated fact | The learner: "why does this fact make sense?" | Pressley et al. (1987, 1988) |
| Deep-level reasoning questions | A tutor or an animated agent, before each content sentence | The material: the learner only overhears the answer | Craig and Gholson's vicarious-learning studies (Gholson & Craig, 2006) |
| Deep questions in tutoring dialogue | The tutor | The learner, with hints and prompts from the tutor | AutoTutor (Nye et al., 2014) |
| Learner question generation | The learner, often with question stems | The learner or peers | King (1992, 1994); Rosenshine et al. (1996) |

- Graesser and Person (1994) define deep-reasoning questions as six categories: causal antecedent, causal consequence, goal orientation, instrumental or procedural, enablement, and expectational. Comparison questions ("How does X compare to Y?") are long-answer questions but are not in this deep-reasoning set.
- Graesser and Person (1994) also found that tutors rarely ask deep questions themselves.

## 2. Evidence, with how strong it is

### 2.1. Elaborative interrogation

**Evidence: moderate on average; mostly recall of facts at short delays.**

- A meta-analysis of ten learning techniques gives elaborative interrogation d = 0.56, across 254 cases and 2,138 participants (I² = 78%). By school level: 0.38 primary, 0.71 secondary, 0.58 university (Donoghue & Hattie, 2021).
- The same authors caution that most included studies measured surface or factual outcomes. The results may not apply to deeper, relational outcomes (Donoghue & Hattie, 2021).
- Dunlosky et al. (2013) rate the technique as moderate utility. Their review states that "firm conclusions about the extent to which elaborative-interrogation benefits comprehension or the extent to which elaborative-interrogation effects persist across longer delays await further research."
- In the original experiments, undergraduates prompted to explain why scored about 72%, against about 37% for groups that received the explanation or only read the material (Pressley et al., 1987, as reported by Dunlosky et al., 2013). Explanations the learners generated themselves beat explanations given to them (Pressley et al., 1987, abstract only).
- One classroom-like study gave biology students "Why is this true?" prompts. They scored 76% against 69% on a true/false test, after controlling for prior knowledge, and took 32 minutes against 28 (B. L. Smith et al., 2010, as reported by Dunlosky et al., 2013).
- Elaborative interrogation (d = 0.56) and self-explanation (d = 0.54) have almost the same average effect. Both are below practice testing (d = 0.74). No experiment read here compares them directly (Donoghue & Hattie, 2021).

### 2.2. Deep questions in tutoring and instruction

**Evidence: one research group, with immediate tests.**

- In the Memphis group's studies, college students overheard a deep question before each content sentence. They gained more (d = 1.99) than students using interactive AutoTutor (d = 1.72) or hearing a monologue of the same content (d = 1.76) (Gholson & Craig, 2006).
- In those studies the learner did not produce the explanation. A question was spoken, then the answer sentence followed. The benefit comes from the question as a frame for the content (Gholson & Craig, 2006).
- AutoTutor asks deep questions and elicits the learner's explanation through dialogue. Its developers report average gains of about 0.8 standard deviations over reading static text for the same time. Early versions gained only 0.28 standard deviations on deep test questions (Nye et al., 2014). The coordinator could not reopen this review (section 5).
- In human tutoring, tutors who were barred from explaining and could only prompt produced learning as good as unrestricted tutoring (Chi et al., 2001).

### 2.3. Learner-generated questions

**Evidence: moderate, with training.**

- Teaching students to generate questions about what they read improved comprehension. The median effect size was 0.36 on standardized tests and 0.86 on tests the researchers wrote (Rosenshine et al., 1996).
- The type of question matters. Learners trained to generate conceptual questions recalled conceptual content better than learners who reread. Generating detail questions gave no benefit (Bugg & McDaniel, 2012).

### 2.4. Delivery by an LLM

**Evidence: none that isolates deep questions.**

- No study tested an LLM that asks why or how questions with a later test taken without AI.
- The closest evidence concerns tutors that withhold answers. A hint-only GPT-4 tutor removed the 17% exam drop that unrestricted GPT-4 caused, but added no gain (Bastani et al., 2025). A tutor that asked only open-ended reflective questions produced larger gains than a prompt-refinement tutor in one of three sessions (Brender et al., 2026, preprint).

## 3. Where the evidence disagrees

- **Prior knowledge.** Dunlosky et al. (2013) report that "effects generally increase as prior knowledge increases." In one text-reading study, the opposite held for one measure: "The experimental effect on coherence was higher for students who had less knowledge than students who had more knowledge" (Ozgungor & Guthrie, 2004, abstract only).
- **Long texts.** Effects are "substantially diluted" or "even reversed" when prompts come only every one or two pages (Dunlosky et al., 2013). One study instead reports support for margin prompts in a long web text (Dornisch & Sperling, 2006, abstract only).
- **Poor explanations.** In a lab experiment reported on a blog without statistics, students who answered how and why questions did worse on transfer problems than students who read twice. They took about twice as long, and 86% of their explanations were inadequate, missing, circular or wrong (Clinton, 2017). Dunlosky et al. (2013) state that "the extent to which elaborative-interrogation effects depend on the quality of the elaborations generated is still an open question."
- **Unsupported prompts.** With an eight-page text, undergraduates who used elaborative interrogation without support had difficulty recognizing the main ideas. It worked best when the main ideas were underlined in advance and specific why questions were added (Boudreau et al., 1999, abstract only).

## 4. What this means for `teach-better`

These are inferences from the evidence above, not tested rules. The report does not change the skill.

1. **The skill already uses the closest relative.** Section 3.4 asks the learner to explain their answers, which is a form of self-explanation (d = 0.54). Elaborative interrogation would add a different moment: a why question about a fact or rule on an explanation card, before any practice.
2. **The learner should generate the explanation.** Explanations the learner generates beat explanations given to them (Pressley et al., 1987). This fits the skill's rule against giving answers.
3. **The agent would need to check each explanation.** Learners often produce poor explanations, and the benefit may depend on their quality. The skill's rules on feedback (sections 3.4 and 3.5) would apply to these answers as well.
4. **Prompts should be frequent and specific.** Sparse prompts in long material lost their effect, and specific why questions helped. One prompt per key fact or rule matches the evidence better than one prompt per chunk.
5. **The best evidence is for facts and rules, not for transfer.** Most studies measured recall at short delays. Deep questions are a candidate for the key-terms and explanation cards, not a replacement for practice problems or quizzes.
6. **Question stems are an option with conditions.** Learners generated useful questions when trained and when the questions were conceptual. A stem such as "Why does X lead to Y?" is the tested form.
7. **Time cost varies.** In one self-paced study the extra time was 32 minutes against 28, which Dunlosky et al. (2013) call "relatively minimal". In the blog-reported experiment it was about twice as long. A large cost would add to the pushback the skill already expects (section 5).

## 5. Method

- Research board: `.research/deep-explanatory-questions/` (not committed). It holds every question, claim and source, with each source marked by how it was read.
- Workers on a cheaper model researched the questions. The coordinator checked the quotes cited above against their sources. Exceptions: Gholson et al. (2009), Nye et al. (2014), Bisra et al. (2018) and Dornisch et al. (2011) returned bot-check pages or had no reachable abstract. Their claims are marked unverified on the board, and this report uses only Nye et al. (2014), as noted in section 2.2.
- Abstract-only sources are marked "abstract only" in the text, and support only what their abstracts state.

## 6. Open questions

- **Primary studies on long texts.** Callender and McDaniel (2007) and Ramsay et al. (2010) could not be retrieved. The report knows them only through Dunlosky et al. (2013).
- **The prior-knowledge moderator.** Woloshyn et al. (1992), the study the moderator rests on, is a scanned PDF without a text layer.
- **A head-to-head comparison** between elaborative interrogation, self-explanation and retrieval practice. None was found.
- **Feedback on explanations.** No study tested feedback on elaborative-interrogation answers specifically.
- **LLM delivery** with a delayed test taken without AI.

## 7. Sources

Bastani, H., Bastani, O., Sungu, A., Ge, H., Kabakcı, Ö., & Mariman, R. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *Proceedings of the National Academy of Sciences, 122*(26), e2422633122. https://doi.org/10.1073/pnas.2422633122

Boudreau, R. L., Wood, E., Willoughby, T., & Specht, J. (1999). Evaluating the efficacy of elaborative strategies for remembering expository text. *Alberta Journal of Educational Research, 45*(2). https://journalhosting.ucalgary.ca/index.php/ajer/article/view/54666

Brender, J., El-Hamamsy, L., Uittenhove, K., Perez, A., Jermann, P., Mondada, F., & Bumbacher, E. (2026). *Reflective dialogue or prompt refinement? Effects of tutor scaffolding on students' independent LLM use for programming*. arXiv. https://arxiv.org/abs/2607.03303

Bugg, J. M., & McDaniel, M. A. (2012). Selective benefits of question self-generation and answering for remembering expository text. *Journal of Educational Psychology, 104*(4), 922–931. https://sites.wustl.edu/ccalab/files/2020/03/buggmcdaniel_2012_selfgenquestions.pdf

Chi, M. T. H., Siler, S. A., Jeong, H., Yamauchi, T., & Hausmann, R. G. (2001). Learning from human tutoring. *Cognitive Science, 25*, 471–533. https://education.asu.edu/sites/default/files/lcl/image3_2.pdf

Clinton, V. (2017, July 11). *Guest post: Elaborative interrogation – What if students can't produce useful elaborations?* The Learning Scientists. https://www.learningscientists.org/blog/2017/7/11-1

Donoghue, G. M., & Hattie, J. A. C. (2021). A meta-analysis of ten learning techniques. *Frontiers in Education, 6*, 581216. https://doi.org/10.3389/feduc.2021.581216

Dornisch, M. M., & Sperling, R. A. (2006). Facilitating learning from technology-enhanced text: Effects of prompted elaborative interrogation. *Journal of Educational Research, 99*(3), 156–166. https://pure.psu.edu/en/publications/facilitating-learning-from-technology-enhanced-text-effects-of-pr/

Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham, D. T. (2013). Improving students' learning with effective learning techniques: Promising directions from cognitive and educational psychology. *Psychological Science in the Public Interest, 14*(1), 4–58. https://doi.org/10.1177/1529100612453266

Gholson, B., & Craig, S. D. (2006). Promoting constructive activities that support vicarious learning during computer-based instruction. *Educational Psychology Review, 18*, 119–139. https://typeset.io/pdf/promoting-constructive-activities-that-support-vicarious-54ye9vrjck.pdf

Graesser, A. C., & Person, N. K. (1994). Question asking during tutoring. *American Educational Research Journal, 31*(1), 104–137. https://talkbank.org/class/access/0docs/graesser1994.pdf

King, A. (1992). Comparison of self-questioning, summarizing, and notetaking-review as strategies for learning from lectures. *American Educational Research Journal, 29*(2), 303–323. https://doi.org/10.3102/00028312029002303

King, A. (1994). Guiding knowledge construction in the classroom: Effects of teaching children how to question and how to explain. *American Educational Research Journal, 31*(2), 338–368. https://doi.org/10.3102/00028312031002338

Nye, B. D., Graesser, A. C., & Hu, X. (2014). AutoTutor and family: A review of 17 years of natural language tutoring. *International Journal of Artificial Intelligence in Education, 24*, 427–469. https://link.springer.com/content/pdf/10.1007/s40593-014-0029-5.pdf

Ozgungor, S., & Guthrie, J. T. (2004). Interactions among elaborative interrogation, knowledge, and interest in the process of constructing knowledge from text. *Journal of Educational Psychology, 96*(3), 437–443. https://doi.org/10.1037/0022-0663.96.3.437

Pressley, M., McDaniel, M. A., Turnure, J. E., Wood, E., & Ahmad, M. (1987). Generation and precision of elaboration: Effects on intentional and incidental learning. *Journal of Experimental Psychology: Learning, Memory, and Cognition, 13*(2), 291–300. https://profiles.wustl.edu/en/publications/generation-and-precision-of-elaboration-effects-on-intentional-an/

Pressley, M., Symons, S., McDaniel, M. A., Snyder, B. L., & Turnure, J. E. (1988). Elaborative interrogation facilitates acquisition of confusing facts. *Journal of Educational Psychology, 80*, 268–278. https://profiles.wustl.edu/en/publications/elaborative-interrogation-facilitates-acquisition-of-confusing-fa/

Rosenshine, B., Meister, C., & Chapman, S. (1996). Teaching students to generate questions: A review of the intervention studies. *Review of Educational Research, 66*(2), 181–221. https://doi.org/10.3102/00346543066002181
