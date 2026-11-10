# Interleaved practice, for an AI agent that teaches one user

Research register · Search date: 10 November 2026

**Scope.** What evidence shows that interleaved practice improves learning, under what conditions, and whether an AI agent that teaches one user (the `teach-better` skill) should use it. Interleaved practice means mixing problems or examples of different types within a session, instead of practising one type at a time (blocked practice).

**Status.** 8 questions closed. 6 answered, 2 contested. A large meta-analysis and several classroom trials exist. No study tested interleaving with an LLM tutor, and none tested adults in a tutoring system.

Interleaving has a moderate average effect, g = 0.42 across 238 effect sizes, but its effect depends on the material (Brunmair & Richter, 2019). It helps most when the types are easy to confuse. It does not help, or reverses, for word lists and expository texts. In grade 7 mathematics classes, interleaved problem sets raised scores on unannounced tests one month later from 38% to 61% (Rohrer et al., 2019). Learners judge interleaving as less effective than blocking, even after their own scores show the opposite (Kornell & Bjork, 2008). `teach-better` currently gives one practice problem per chunk, so all of its practice is blocked. Its quizzes, which come after every few chunks, are the natural place to mix problem types.

## 1. What interleaving is

- Blocked practice orders problems AABB. Interleaved practice orders them ABAB (Chen et al., 2021).
- Interleaving also spaces practice of each type, so sources disagree about which of the two causes the benefit. With spacing held fixed, interleaving still "doubled scores on a test given one day later" in children's mathematics (Taylor & Rohrer, 2010, abstract only). Foster et al. (2019) attribute the effect on geometry problems mainly to spacing (as reported by an article read for this report, S-i3-2 on the board).
- The two main accounts are discriminative contrast and attentional bias. Discriminative contrast holds that learners compare adjacent items of different types. Attentional bias holds that interleaving directs attention to differences between categories and blocking directs it to what members of one category share (Carvalho & Goldstone, 2015, abstract only; Firth et al., 2021). A 24-hour delay did not shift results toward interleaving, which argues against spacing as the main cause (Carvalho & Goldstone, 2014, abstract only).

## 2. Evidence, with how strong it is

### 2.1. Meta-analyses

**Evidence: moderate overall; depends on the material.**

| Material | Effect (Hedges' g) |
|---|---|
| All studies (k = 238) | 0.42 |
| Paintings | 0.67 |
| Mathematical tasks | 0.34 (I² = 76.9%) |
| Expository texts | not significant |
| Words | −0.39 (blocking better) |

- Source: Brunmair and Richter (2019). The authors warn that the result for words rests on few studies. The analysis excluded motor skills.
- The effect was stronger when categories were more similar to each other, when items within a category were less similar, and when the material was more complex (Brunmair & Richter, 2019).
- A systematic review of 26 studies, 17 of them pooled, found benefits for memory (g up to 0.65) and for transfer to new items (g up to 0.66), mostly from lab studies with short delays (Firth et al., 2021).
- For motor skills, mixed practice improved retention in the lab, but "the beneficial effect of random practice on the retention was almost negligible" in applied settings (Czyż et al., 2024).

### 2.2. Classroom mathematics with delayed tests

**Evidence: large effects, mostly from one research group.**

- In grade 7, interleaved practice beat blocked practice on tests 1 day later (d = 0.42) and 30 days later (d = 0.79) (Rohrer et al., 2015).
- With 140 grade 7 students, scores on an unannounced test two weeks later were 72% against 38% (d = 1.05). The problems were not superficially similar (Rohrer et al., 2014).
- In a randomized trial with 54 grade 7 classes, the interleaved group scored 61% against 38% on an unannounced test one month later (d = 0.83) (Rohrer et al., 2019).
- In a homework study with a 2–5 day delay, the overall effect did not reach significance (g = 0.22). Many students were lost because one teacher did not assign the post-test (Ostrow et al., 2015).
- Interleaved practice in undergraduate physics improved recall and problem solving (Samani & Pan, 2021, abstract only).
- Costs reported by the trial's authors: "every teacher reported that the interleaved assignments took more time than did blocked practice." The effect was smaller at the shorter test delay (Rohrer et al., 2019).

### 2.3. Adults and tutoring systems

**Evidence: lab studies only for adults; no LLM study.**

- In four experiments that included adults outside university, interleaving improved verb conjugation in Romance languages after two weekly sessions and a one-week delay. The benefit held for dissimilar tenses as well (Pan, Rodríguez Flores, et al., 2025).
- In an online adult sample, the benefit for painting styles grew with fluid intelligence. It did not vary with fluid intelligence for categories learned from text (Pan, Yu, et al., 2025).
- An intelligent tutoring system for fractions, used by 230 students in grades 4 and 5, gave better results when it interleaved graphical representations than when it blocked them (Rau et al., 2014). That study interleaved representations, not problem types.

### 2.4. How learners judge interleaving

**Evidence: consistent.**

- Learners studied paintings either grouped by artist ("massing") or mixed ("spacing"). "Participants rated massing as more effective than spacing, even after their own test performance had demonstrated the opposite" (Kornell & Bjork, 2008, abstract only).
- Grade 7 students judged interleaved practice "less effective, less preferable, more time-consuming, and more difficult" than blocked practice (Hartwig & Rohrer, 2025).
- Two kinds of explanation had "only modest effects" on this belief: why blocking seems better but is not, and how the study schedule links to later scores. Most learners changed their view only when shown separate test scores for each schedule, combined with both explanations (Yan et al., 2016, abstract only).

## 3. Where the evidence disagrees

- **Blocked practice first.** Rohrer et al. (2019) write that interleaving "might be less effective or too difficult if students do not first receive at least a small amount of blocked practice when they encounter a new skill or concept." The claim that novices need blocking first comes mainly from research on motor skills (Yan & Sana, 2021). In cognitive tasks, the benefit held across levels of working memory and task demand and "never reversed" (Yan & Sana, 2021). Prior knowledge did not change the benefit in 236 grade 3 students (Nemeth & Lipowsky, 2023). For verbal categories, blocked presentation first beat pure interleaving (Sorensen & Woltz, 2016). The coordinator could not reopen Nemeth and Lipowsky (2023) or Sorensen and Woltz (2016) (section 5).
- **Texts.** Single studies disagree. A study that interleaved two unrelated texts found no effect (Dobson, 2011, as reported by Brunmair & Richter, 2019). In another study, students who drew inferences while reading interleaved texts did better on comparative and inductive reasoning (Abel et al., 2020, abstract only).
- **Similarity.** The meta-analysis links the benefit to similar categories (Brunmair & Richter, 2019). Pan, Rodríguez Flores, et al. (2025) found benefits for dissimilar tenses as well.
- **Unrelated material.** Mixing science terms with foreign vocabulary gave no benefit. Firth et al. (2021) judge it unlikely that interleaving whole lessons or topics gives a major benefit, because the evidence comes from brief items placed next to each other.

## 4. What this means for `teach-better`

These are inferences from the evidence above, not tested rules. The report does not change the skill.

1. **Quizzes are the natural place to interleave.** The skill gives one practice problem per chunk and a quiz after every few chunks. A quiz that mixes problem types from earlier chunks matches the classroom trials, where interleaved assignments came after the types had been introduced. The skill's review questions in later sessions (section 4.2) could mix types too.
2. **Mix types the learner could confuse.** The benefit is largest when the learner must decide which method or category applies. Mixing unrelated topics, or interleaving whole chunks, has little support.
3. **Keep the first practice of a new idea blocked.** The skill's worked example followed by a similar problem is blocked practice. The Rohrer group suggests a small amount of it before interleaving. The evidence on whether novices need it is contested.
4. **Expect lower scores during practice.** Interleaving lowered scores during practice but raised scores on delayed tests (Taylor & Rohrer, 2010). The agent should not read a drop on mixed problems as failure, nor raise the support level because of it alone.
5. **Expect pushback.** Learners judge interleaving as worse. Explanations alone changed this belief only a little. The skill already handles pushback (section 5), and a learner who prefers blocked practice decides.
6. **Not for vocabulary lists or long expository texts.** The meta-analysis found no benefit for texts and a reversal for words.
7. **Time cost.** Interleaved assignments took longer. The effect appeared at delays of days to a month, which matches the skill's spaced review rather than a single session.

## 5. Method

- Research board: `.research/interleaved-practice/` (not committed). It holds every question, claim and source, with each source marked by how it was read.
- Workers on a cheaper model researched the questions, in English and German. The coordinator checked the quotes cited above against their sources. Exceptions: Springer pages for Chen et al. (2021), Nemeth and Lipowsky (2023), Rau et al. (2014) and Sorensen and Woltz (2016) returned bot-check pages. Their claims are marked unverified on the board.
- Abstract-only sources are marked "abstract only" in the text, and support only what their abstracts state.

## 6. Open questions

- **A meta-analysis of interleaved mathematics** by Nemeth and colleagues was seen only through a corrigendum.
- **Interleaving in tutoring systems or with LLM tutors**, for adults, with a delayed test. Patel et al. (2016) appeared only in search results.
- **Whether explaining interleaving to the learner changes their acceptance** in a tutoring setting.
- **Hybrid schedules** (blocked, then interleaved) for problem solving with novices. No direct test was read.

## 7. Sources

Abel, R., Niedling, L. M., & Hänze, M. (2020). Spontaneous inferential processing while reading interleaved expository texts enables learners to discover the underlying regularities. *Applied Cognitive Psychology*. https://doi.org/10.1002/acp.3761

Brunmair, M., & Richter, T. (2019). Similarity matters: A meta-analysis of interleaved learning and its moderators. *Psychological Bulletin, 145*(11), 1029–1052. https://doi.org/10.1037/bul0000209 (accepted manuscript: https://www.psychologie.uni-wuerzburg.de/fileadmin/06020400/2019/Brunmair_Richter_in_press__2019_META-ANALYSIS_OF_INTERLEAVED_LEARNING.pdf)

Carvalho, P. F., & Goldstone, R. L. (2014). Effects of interleaved and blocked study on delayed test of category learning generalization. *Frontiers in Psychology, 5*, 936. https://pubmed.ncbi.nlm.nih.gov/25202296/

Carvalho, P. F., & Goldstone, R. L. (2015). The benefits of interleaved and blocked study: Different tasks benefit from different schedules of study. *Psychonomic Bulletin & Review, 22*(1), 281–288. https://pubmed.ncbi.nlm.nih.gov/24984923/

Chen, O., Paas, F., & Sweller, J. (2021). Spacing and interleaving effects require distinct theoretical bases: A systematic review testing the cognitive load and discriminative-contrast hypotheses. *Educational Psychology Review*. https://link.springer.com/article/10.1007/s10648-021-09613-w

Czyż, S. H., Wójcik, A. M., Solarská, P., & Kiper, P. (2024). High contextual interference improves retention in motor learning: Systematic review and meta-analysis. *Scientific Reports*. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11237090/

Firth, J., Rivers, I., & Boyle, J. (2021). A systematic review of interleaving as a concept learning strategy. *Review of Education*. https://strathprints.strath.ac.uk/75711/7/Firth_etal_RE_2021_A_systematic_review_of_interleaving.pdf

Hartwig, M. K., & Rohrer, D. (2025). Students' perceptions of effective math learning strategies. *Behavioral Sciences, 15*(8), 1047. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12383065/

Kornell, N., & Bjork, R. A. (2008). Learning concepts and categories: Is spacing the "enemy of induction"? *Psychological Science, 19*(6), 585–592. https://pubmed.ncbi.nlm.nih.gov/18578849/

Nemeth, L., & Lipowsky, F. (2023). The role of prior knowledge and need for cognition for the effectiveness of interleaved and blocked practice. *European Journal of Psychology of Education, 39*, 907–929. https://doi.org/10.1007/s10212-023-00723-3

Ostrow, K., Heffernan, N., Heffernan, C., & Peterson, Z. (2015). Blocking vs. interleaving: Examining single-session effects within middle school math homework. In *Artificial Intelligence in Education (AIED 2015)*, Lecture Notes in Computer Science 9112 (pp. 338–347). Springer. https://d-miller.github.io/DRK12/topic1/3574.pdf

Pan, S. C., Rodríguez Flores, S., Kaku, M. E., & Lai, W. H. E. (2025). Interleaved practice enhances grammar skill learning for similar and dissimilar tenses in Romance languages. *Learning and Instruction, 95*, 102045. https://sc-pan.github.io/pdf/PRKL_2024.pdf

Pan, S. C., Yu, L., Hong, Y., Wong, M. J., Selvarajan, G., & Kaku, M. E. (2025). Individual differences in fluid intelligence moderate the interleaving effect for perceptual category learning. *Learning and Individual Differences, 117*, 102603. https://sc-pan.github.io/pdf/PYHWSK_2025.pdf

Rau, M. A., Aleven, V., Rummel, N., & Pardos, Z. (2014). How should intelligent tutoring systems sequence multiple graphical representations of fractions? A multi-methods study. *International Journal of Artificial Intelligence in Education, 24*, 125–161. https://link.springer.com/content/pdf/10.1007/s40593-013-0011-7.pdf

Rohrer, D., Dedrick, R. F., & Burgess, K. (2014). The benefit of interleaved mathematics practice is not limited to superficially similar kinds of problems. *Psychonomic Bulletin & Review*. https://doi.org/10.3758/s13423-014-0588-3

Rohrer, D., Dedrick, R. F., Hartwig, M. K., & Cheung, C.-N. (2019). A randomized controlled trial of interleaved mathematics practice. *Journal of Educational Psychology*. https://doi.org/10.1037/edu0000367

Rohrer, D., Dedrick, R. F., & Stershic, S. (2015). Interleaved practice improves mathematics learning. *Journal of Educational Psychology, 107*(3), 900–908. https://www.gwern.net/doc/psychology/spaced-repetition/2014-rohrer-2.pdf

Samani, J., & Pan, S. C. (2021). Interleaved practice enhances memory and problem-solving ability in undergraduate physics. *npj Science of Learning, 6*, 32. https://pubmed.ncbi.nlm.nih.gov/34772951/

Sorensen, L. J., & Woltz, D. J. (2016). Blocking as a friend of induction in verbal category learning. *Memory & Cognition*. https://link.springer.com/article/10.3758/s13421-016-0615-x

Taylor, K., & Rohrer, D. (2010). The effect of interleaving practice. *Applied Cognitive Psychology, 24*(6), 837–848. https://digitalcommons.usf.edu/psy_facpub/1760/

Yan, V. X., Bjork, E. L., & Bjork, R. A. (2016). On the difficulty of mending metacognitive illusions: A priori theories, fluency effects, and misattributions of the interleaving benefit. *Journal of Experimental Psychology: General, 145*(7), 918–933. https://pubmed.ncbi.nlm.nih.gov/27227415/

Yan, V. X., & Sana, F. (2021). The robustness of the interleaving benefit. *Journal of Applied Research in Memory and Cognition, 10*, 589–602. https://www.Gwern.net/doc/psychology/spaced-repetition/2021-yan.pdf
