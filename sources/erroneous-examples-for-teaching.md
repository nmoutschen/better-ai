# Erroneous examples, for an AI agent that teaches one user

Research register · Search date: 10 November 2026

**Scope.** What evidence shows that asking learners to find and explain an error in a worked solution helps them learn, under what conditions, and whether an AI agent that teaches one user (the `teach-better` skill) should use it.

**Status.** 6 questions closed. 4 answered, 2 contested. A recent meta-analysis finds a weak effect. Single studies split between delayed benefits and no benefit. No study tested an LLM tutor that gives learners erroneous examples to study.

Erroneous examples have "a statistically significant but weak effect" on learning, g = .136 across 42 papers (Alemdag et al., 2025, abstract only). Explaining the error matters: self-explanation prompts or instructional explanations beat no explanation (Alemdag et al., 2025). In a tutor for decimals, erroneous examples did not help on the immediate test but did one week later (d = .33). Students liked the problem-solving version more (McLaren et al., 2015, abstract only). In another tutoring study, students who solved problems gained more and felt less confusion and frustration (Richey et al., 2019). The evidence does not support erroneous examples as a default.

## 1. What the technique is

- An erroneous example is "a worked example that contains at least one incorrect solution step" (Wesenberg et al., 2022).
- Variants differ in what the learner does: study the error, find and fix it, explain it, or compare it with a correct solution side by side or one after the other (Durkin, 2012; McLaren et al., 2015).
- Order matters too. Correct examples first lowered mental load and went with better learning. Erroneous examples first gave more accurate self-assessment (Wesenberg et al., 2022).

## 2. Evidence, with how strong it is

### 2.1. Size of the effect

**Evidence: weak on average; contested.**

- Across 42 papers and 177 effect sizes, erroneous examples were compared with correct examples or with problem solving. The effect was g = .136 (Alemdag et al., 2025, abstract only).
- In decimal tutoring data with about 600 students, erroneous examples did not beat problem solving on the immediate test (d = 0.14, not significant). They did on the delayed test (d = 0.27) (Richey et al., 2019).
- In a replication with 390 students, the erroneous-examples group "performed significantly better on a delayed test, given a week after the initial post-test (d = .33, for gain scores)" (McLaren et al., 2015, abstract only).
- A study of critical thinking with 170 students tested at once, after 3 weeks and after 9 months found "no differences in learning gains or transfer performance" between contrasting, correct-example, erroneous-example and practice conditions (van Peppen et al., 2021, abstract only).
- In a study with 342 students learning decimals, adding incorrect examples to correct examples "did not lead to significantly greater learning than studying only correct examples" (Durkin, 2012, abstract only).

### 2.2. Conditions

**Evidence: one systematic review; primary studies mostly read as abstracts.**

- A review of 40 studies found that the benefits "depend on how errors are explained or highlighted, how prompts are designed, and on learners' prior knowledge and cognitive capabilities" (Dieterich et al., 2025, abstract).
- Prompts to identify, explain, correct or reflect on errors "often promote deeper learning". They "may also shift the balance ... toward cognitive overload, particularly when the material is complex" (Dieterich et al., 2025, abstract).
- In SQL-Tutor, novices gained more debugging knowledge when erroneous examples were added to worked examples and problem solving (Chen et al., 2016).
- As reported secondhand, highlighting the error helped novices, and erroneous examples helped advanced students on far transfer (Große & Renkl, 2007, in Chen et al., 2016).

### 2.3. Delivery by a computer or an LLM

**Evidence: tutoring systems exist; no LLM study of the learning effect.**

- Web-based decimals tutors and SQL-Tutor have used erroneous examples (McLaren et al., 2015; Chen et al., 2016).
- An LLM generated buggy code, verified by a test suite, for students to debug. Student performance on these exercises was "comparable to those manually created by instructors" (Pădurean et al., 2024, abstract only). This shows that an LLM can write the errors. It does not show a learning gain.

## 3. Where the evidence disagrees

- **Delayed benefit or none.** The decimals tutors showed delayed gains. A classroom study and a critical-thinking study showed none.
- **Problem solving can win.** In a tutoring study with 174 middle-school students, "students in the problemsolving condition improved significantly more and experienced significantly less confrustion" (Richey et al., 2019, AIED). "Confrustion" is the authors' term for confusion and frustration. The higher confrustion "was associated with poorer learning".
- **Prompts.** The erroneous-examples meta-analysis found that explanation prompts help (Alemdag et al., 2025). A mathematics meta-analysis of worked examples reported that self-explanation prompts moderated effects negatively, and that correct examples alone beat incorrect or mixed sets (Barbieri et al., 2023). The coordinator could not reopen that paper, so these claims are unverified on the board.
- **Liking.** Learners liked the erroneous-examples tutor less and found it harder to use (d = .21 and .37) (McLaren et al., 2015, abstract only).

## 4. What this means for `teach-better`

These are inferences from the evidence above, not tested rules. The report does not change the skill.

1. **Not a default tool.** The average effect is weak, and problem solving sometimes did better. Correct worked examples remain the skill's base, as now.
2. **If used, ask for the explanation.** The benefit depended on explaining the error, through a prompt or an explanation.
3. **Show the correct solution next to the error.** The review found that contrasting the error with the correct solution worked better than the error alone (Dieterich et al., 2025). The coordinator could not recheck this point against the full text.
4. **Show the correct example first.** Correct-first lowered load and went with better learning (Wesenberg et al., 2022).
5. **Use it after the basics, for common mistakes.** Find-the-error prompts can overload learners on complex material. Highlighting the error helped novices.
6. **Make the error real and check it.** An LLM can write plausible errors, but each one must be a real error with exactly one intended fault. That matches the skill's rule to check its own examples (section 3.5).
7. **Expect a delayed payoff and lower liking.** Gains appeared a week later, not at once, and learners liked the format less.

## 5. Method

- Research board: `.research/erroneous-examples/` (not committed). It holds every question, claim and source, with each source marked by how it was read.
- Workers on a cheaper model researched the questions. The coordinator checked the quotes cited above against their sources. Exceptions: the full texts of Dieterich et al. (2025) and Barbieri et al. (2023), and the abstracts of Isotani et al. (2011), Chen et al. (2016, ITS) and McLaren et al. (2012), returned bot-check pages. Their claims are marked unverified on the board. This report quotes only the abstract of Dieterich et al. (2025) and states where it relies on unverified points.

## 6. Open questions

- **Full texts of Große and Renkl (2007), Booth et al. (2013) and Alemdag et al. (2025)** were not accessible.
- **Error type.** Beege et al. (2021), on syntactic against semantic errors in programming, was blocked.
- **LLM tutors** that give learners erroneous examples, with a learning test. None was found.

## 7. Sources

Alemdag, E., Eichelmann, A., & Narciss, S. (2025). A framework for learning from erroneous examples and meta-analysis of empirical research. *Review of Educational Research*. https://doi.org/10.3102/00346543251390901

Barbieri, C. A., Miller-Cotto, D., Clerjuste, S. N., & Chawla, K. (2023). A meta-analysis of the worked examples effect on mathematics performance. *Educational Psychology Review*. https://link.springer.com/article/10.1007/s10648-023-09745-1

Chen, X., Mitrovic, T., & Mathews, M. (2016). Do novices and advanced students benefit from erroneous examples differently? In *Proceedings of the 24th International Conference on Computers in Education*. APSCE. https://library.apsce.net/index.php/ICCE/article/download/1002/937/1832

Dieterich, S., Rumann, S., & Rodemer, M. (2025). Conditions for effective learning from erroneous examples: A systematic review. *Educational Psychology Review, 37*, 94. https://doi.org/10.1007/s10648-025-10071-x

Durkin, K. (2012). *The effectiveness of incorrect examples and comparison when learning about decimal magnitude* [Doctoral dissertation, Vanderbilt University]. https://ir.vanderbilt.edu/handle/1803/11934

McLaren, B. M., Adams, D. M., & Mayer, R. E. (2015). Delayed learning effects with erroneous examples: A study of learning decimals with a web-based tutor. *International Journal of Artificial Intelligence in Education*. https://link.springer.com/article/10.1007/s40593-015-0064-x

Pădurean, V.-A., Denny, P., & Singla, A. (2024). *BugSpotter: Automated generation of code debugging exercises*. arXiv. https://arxiv.org/abs/2411.14303

Richey, J. E., Andres-Bray, J. M. L., Mogessie, M., Scruggs, R., Andres, J. M. A. L., Star, J. R., Baker, R. S., & McLaren, B. M. (2019). More confusion and frustration, better learning: The impact of erroneous examples. *Computers & Education, 139*, 173–190. https://par.nsf.gov/servlets/purl/10155531

Richey, J. E., McLaren, B. M., Andres-Bray, M., Mogessie, M., Scruggs, R., Baker, R., & Star, J. (2019). Confrustion in learning from erroneous examples: Does type of prompted self-explanation make a difference? In *Artificial Intelligence in Education (AIED 2019)*, LNAI 11625 (pp. 445–457). Springer. https://par.nsf.gov/servlets/purl/10155532

van Peppen, L. M., Verkoeijen, P. P. J. L., Heijltjes, A. E. G., Janssen, E. M., & van Gog, T. (2021). Enhancing students' critical thinking skills: Is comparing correct and erroneous examples beneficial? *Instructional Science, 49*, 747–777. https://link.springer.com/content/pdf/10.1007/s11251-021-09559-0.pdf

Wesenberg, L., Krieglstein, F., Jansen, S., Rey, G. D., Beege, M., & Schneider, S. (2022). The influence of the order and congruency of correct and erroneous worked examples on learning and (meta-)cognitive load. *Frontiers in Psychology*. https://www.frontiersin.org/articles/10.3389/fpsyg.2022.1032003/full
