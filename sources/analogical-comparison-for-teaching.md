# Comparing examples, for an AI agent that teaches one user

Research register · Search date: 10 November 2026

**Scope.** What evidence shows that asking learners to compare two or more examples side by side helps them learn, under what conditions, and whether an AI agent that teaches one user (the `teach-better` skill) should use it. Sources call this case comparison, analogical encoding, comparing methods, or contrasting cases.

**Status.** 6 questions closed. 5 answered, 1 contested. One meta-analysis and several controlled studies support the technique. Prior knowledge decides whether it helps. The only LLM study found a small effect, limited to some learners.

Comparing cases beat studying them one at a time, studying a single case, and traditional instruction, d = .50 across 57 experiments (Alfieri et al., 2013, abstract only). Comparing two negotiation cases more than doubled transfer of the principle, 48% against 19% for studying the cases separately (Gentner et al., 2003). But novices who knew neither method "benefited most from studying examples sequentially, rather than from comparing methods" (Rittle-Johnson et al., 2017). Learners rarely compare unless asked, and specific prompts work better than a bare "compare".

## 1. What the technique is

| Variant | What the learner does | Source |
|---|---|---|
| Analogical encoding | Compares two analogous examples to find the shared principle | Gentner et al. (2003, 2009) |
| Comparing methods | Compares two methods for solving the same problem, side by side | Rittle-Johnson & Star (2007) |
| Comparing problems | Compares two problems solved with the same method | Rittle-Johnson & Star (2009) |
| Contrasting cases | Analyzes cases to notice what tells them apart, then is told the principle | Schwartz & Bransford (1998) |

- In the classroom studies, the compared examples were "presented simultaneously", with "side-by-side presentation and common language" to help learners align the steps. The control group studied the same examples one at a time with explanation prompts (Rittle-Johnson et al., 2017).

## 2. Evidence, with how strong it is

### 2.1. Size of the effect

**Evidence: one meta-analysis plus consistent controlled studies; mostly short delays.**

- "Case comparison activities commonly led to greater learning outcomes than other forms of case study including sequential, single case, and nonanalogous, as well as traditional instruction and control (d = .50)" (Alfieri et al., 2013, abstract only).
- Effects were larger when learners were asked to find similarities, when the principle came after the comparison, with perceptual content, and with immediate tests (Alfieri et al., 2013).
- Comparing two cases gave 48% transfer of the principle, against 19% for studying the same cases separately (Gentner et al., 2003).
- Comparing two methods side by side beat studying them one at a time on procedural knowledge and flexibility, with comparable conceptual gains (Rittle-Johnson & Star, 2007, abstract only). Comparing methods beat comparing problems (Rittle-Johnson & Star, 2009, abstract only).
- With slower pacing, comparing methods improved flexibility "including on a one-month retention test" (Rittle-Johnson et al., 2017).
- Inventing a formula from contrasting cases before being told it gave equal skill at using the formula but more transfer than being told first (Schwartz et al., 2011, abstract only).

### 2.2. Conditions

**Evidence: mostly from one research group's classroom studies.**

- **Prior knowledge.** Comparing methods helped students who already tried algebra. Novices learned more from sequential study (Rittle-Johnson et al., 2009, abstract only). The authors explain: "when both methods are unfamiliar, the working memory demands may be too high and impede learning" (Rittle-Johnson et al., 2017).
- **Experts may not need it.** "Once students develop strong knowledge in the domain, explicit comparison may not be needed" (Rittle-Johnson et al., 2017).
- **Prompts.** With more support, more learners applied the principle afterwards. 90% did so after guided comparison, 70% after plain comparison, 55% after separate cases and 37% with no training (Gentner et al., 2003). Specific prompts beat generic prompts "to compare" (Rittle-Johnson et al., 2017, citing earlier work).
- **Comparison does not happen by itself.** "It often fails to occur in situations where it could be effective—even when two analogous cases are analyzed in immediate succession" (Gentner et al., 2009). Students "never spontaneously offered reflection on a contrasting case when it was not specifically requested" (Naik et al., 2025).
- **Timing.** Studying one method on day 1 and comparing on day 2 gave the least learning of three conditions (Rittle-Johnson et al., 2017).

### 2.3. Delivery by an LLM

**Evidence: one study.**

- GPT-4 generated a contrasting case for each team's own solution, keeping "many concrete details the same" to highlight the contrast. The study found no main effect on learning. Students with low pretest scores learned more from the provided case. High-pretest students learned marginally more from generating their own. The authors call the effect "small and specific to a subpopulation of students" (Naik et al., 2025).

## 3. Where the evidence disagrees

- **Novices.** Comparing helped novices only with slower pacing, and only on flexibility (Rittle-Johnson et al., 2017).
- **What is compared.** College students comparing two algebra word problems "did not support learning or transfer of the solution methods" across five experiments (Reed et al., as reported by Rittle-Johnson et al., 2017). Comparing problem types "did not differ from students in the sequential condition on any outcome" (Rittle-Johnson et al., 2017).
- **Correct against erroneous examples.** Comparing correct and erroneous examples for critical thinking gave "no differences in learning gains or transfer performance" at immediate, 3-week and 9-month tests (van Peppen et al., 2021, abstract only).
- **Delivery.** A year-long comparison curriculum gave no gain, because teachers used it "much less often than expected" (Rittle-Johnson et al., 2017).

## 4. What this means for `teach-better`

These are inferences from the evidence above, not tested rules. The report does not change the skill.

1. **A candidate tool for worked examples.** After the learner knows one method or case, the agent can show a second one side by side and ask what they share or how they differ.
2. **Not for the first example of a new idea.** Novices learned more from one example at a time. The skill already starts each chunk with a single worked example, and that should stay.
3. **Show both at once, aligned.** Put the two examples side by side in a table with matching steps, not on two separate cards, and not a day apart.
4. **Give a specific prompt.** Ask about a named aspect, such as "Which step differs, and why does it lead to the same answer?", not just "compare these". Learners did not compare without being asked.
5. **Give the principle after the comparison.** Effects were larger when the principle came after the comparison.
6. **Compare methods rather than problem types,** where the topic has more than one method.
7. **Check the second example.** An LLM can build a contrasting case. It must differ only in the intended aspect, which the skill's checking rule (section 3.5) covers.
8. **Skip it for learners who already know the domain well.** Explicit comparison may add little for them.

## 5. Method

- Research board: `.research/analogical-comparison/` (not committed). It holds every question, claim and source, with each source marked by how it was read.
- Workers on a cheaper model researched the questions. The coordinator checked the quotes cited above against their sources. Exceptions: Chase et al. (2019, Springer), some wording from the Naik et al. (2025) abstract, and Chang (2014) could not be rechecked. Those claims are marked unverified on the board, and this report does not use them. Ten claims had their fields shifted on the board. The coordinator restored them before checking.
- Abstract-only sources are marked "abstract only" in the text, and support only what their abstracts state.

## 6. Open questions

- **The final Alfieri et al. (2013) full text** and its moderator analysis. Only the abstract and a 2011 preliminary report were read.
- **Comparing against explaining each example.** A direct test (Nokes-Malach et al., 2013) was seen only in search results.
- **Adults learning alone.** Most studies used school students. The LLM study used college students in teams.
- **Delayed tests** beyond one month.

## 7. Sources

Alfieri, L., Nokes, T. J., & Schunn, C. D. (2011). *Aligning the structural components across learning tasks of case comparisons* [Conference abstract]. Society for Research on Educational Effectiveness. ERIC ED528947. https://files.eric.ed.gov/fulltext/ED528947.pdf

Alfieri, L., Nokes-Malach, T. J., & Schunn, C. D. (2013). Learning through case comparisons: A meta-analytic review. *Educational Psychologist, 48*(2), 87–113. https://doi.org/10.1080/00461520.2013.775712

Gentner, D., Loewenstein, J., & Thompson, L. (2003). Learning and transfer: A general role for analogical encoding. *Journal of Educational Psychology, 95*(2), 393–408. https://typeset.io/pdf/learning-and-transfer-a-general-role-for-analogical-encoding-1j5d5qfzya.pdf

Gentner, D., Loewenstein, J., Thompson, L., & Forbus, K. D. (2009). Reviving inert knowledge: Analogical abstraction supports relational retrieval of past events. *Cognitive Science, 33*, 1343–1382. https://www.qrg.northwestern.edu/papers/Files/QRG_Dist_Files/QRG_2009/Gentner,Loewenstein,Thompson&Forbus_2009-1.pdf

Naik, A., Yin, J. R., Kamath, A., Ma, Q., Wu, S. T., Murray, R. C., Bogart, C., Sakr, M., & Rose, C. P. (2025). Providing tailored reflection instructions in collaborative learning using large language models. *British Journal of Educational Technology, 56*, 531–550. https://par.nsf.gov/servlets/purl/10639383

Rittle-Johnson, B., & Star, J. R. (2007). Does comparing solution methods facilitate conceptual and procedural knowledge? An experimental study on learning to solve equations. *Journal of Educational Psychology, 99*(3), 561–574. https://doi.org/10.1037/0022-0663.99.3.561

Rittle-Johnson, B., & Star, J. R. (2009). Compared with what? The effects of different comparisons on conceptual knowledge and procedural flexibility for equation solving. *Journal of Educational Psychology, 101*(3), 529–544. https://doi.org/10.1037/a0014224

Rittle-Johnson, B., Star, J. R., & Durkin, K. (2009). The importance of prior knowledge when comparing examples: Influences on conceptual and procedural knowledge of equation solving. *Journal of Educational Psychology, 101*(4), 836–852. https://doi.org/10.1037/a0016026

Rittle-Johnson, B., Star, J. R., & Durkin, K. (2017). The power of comparison in mathematics instruction: Experimental evidence from classrooms. In *Mathematical cognition and learning* (Vol. 3, pp. 273–296). Elsevier. https://cdn.vanderbilt.edu/t2-my/my-prd/wp-content/uploads/sites/3147/2020/01/RittleJohnson_Star_Durkin_2017_ComparisonChapter.pdf

Schwartz, D. L., & Bransford, J. D. (1998). A time for telling. *Cognition and Instruction, 16*(4), 475–522. https://www.wright.edu/sites/www.wright.edu/files/uploads/2017/Feb/event/Schwartz_Bransford_1998_TimeForTelling.pdf

Schwartz, D. L., Chase, C. C., Oppezzo, M. A., & Chin, D. B. (2011). Practicing versus inventing with contrasting cases: The effects of telling first on learning and transfer. *Journal of Educational Psychology, 103*(4), 759–775. https://doi.org/10.1037/a0025140

van Peppen, L. M., Verkoeijen, P. P. J. L., Heijltjes, A. E. G., Janssen, E. M., & van Gog, T. (2021). Enhancing students' critical thinking skills: Is comparing correct and erroneous examples beneficial? *Instructional Science, 49*(6), 747–777. https://research-portal.uu.nl/en/publications/enhancing-students-critical-thinking-skills-is-comparing-correct-/
