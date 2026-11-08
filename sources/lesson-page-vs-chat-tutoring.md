# Does a structured lesson page teach better than tutoring in chat?

Research register · Search date: 8 November 2026

**Scope.** Whether an AI tutor should deliver lessons and collect the learner's answers through a separate structured page or through chat, judged by learning measured without the AI. Also covers the features such a page would carry: segmented chunks, required confidence and self-explanation fields, quizzes that hide earlier material, records of attempts, and splitting the lesson between two places. Extends `sources/ai-agent-teaching-new-topics.md` and does not repeat it.

**Status.** 8 questions answered, 1 contested, and 1 left open at low priority (section 4). Most evidence comes from university and school students in courses. Many sources were read only as abstracts or through a fetch tool that summarizes pages, and several are recent preprints.

No study compares the same tutoring delivered through a structured page and through chat. The features a page would enforce either work in any medium, such as self-explanation prompts, or showed no learning gain on their own, such as a separate confidence rating or a progress record. A lesson page therefore rests on design choices or the user's stated preference, not on evidence that it improves learning.

## 1. Findings, with how strong the evidence is

### 1.1. A structured interface versus chat

**Evidence: no direct test; indirect studies are small or associational.**

- In a graduate robotics course, 58 students used either a structured ChatGPT interface, which asked them to classify and organize their prompts, or plain ChatGPT. The authors "found no differences in performance or learning between groups", and the prompting habits did not transfer once the structure was removed (Brender et al., 2025). The paper does not say whether the post-tests were taken without AI.
- In a discrete-maths course, 148 students had staggered access to a chatbot and an embedded proof-review tool. Access raised homework scores but not exam scores, and "only chatbot usage constituted a negative associative pathway to subsequent exam performance". The authors state these are associations, not causal effects (Chen et al., 2026a).
- Plain ChatGPT access lowered closed-book exam grades by 17%. A chat tutor with prompts that safeguard learning removed the harm but added no gain (Bastani et al., 2025). Both conditions were chat, so the study tests the tutor's instructions, not the interface.
- ChatGPT hints delivered inside a step-based tutor produced learning gains over no help, with no significant difference from human-written hints (N = 274; Pardos & Bhandari, 2024). No study compared the same hints in chat.
- Step-based intelligent tutoring systems reached d = 0.76 against no tutoring, close to human tutoring at d = 0.79 (VanLehn, 2011, abstract). The abstract does not compare step-based and answer-based interfaces.

### 1.2. Required self-explanation

**Evidence: strong for the prompt itself; thin for its format.**

- Prompting learners to explain gave g = .55 across 69 effect sizes. No difference was detected between media or between computer instruction, tutoring systems and simulations (Bisra et al., 2018). A page is not needed for the effect.
- Only 2 studies used multiple-choice prompts (g = .24, not different from zero). The authors call for direct comparisons of multiple-choice, fill-in and open-ended prompts (Bisra et al., 2018).
- In a calculus study of 92 learners, menu-based and open-ended explanations with LLM feedback did not differ from no explanation on the post-test (Chen et al., 2026b).
- No study tested a required field against an optional prompt.

### 1.3. Confidence ratings

**Evidence: a separate rating did not help in the one study that isolated it.**

- Adding a 0–100 confidence rating to standard multiple-choice practice did not improve a final test: 6.41 vs 6.54 items out of 20. Confidence-weighted multiple choice, where the answer format itself expresses certainty, scored 8.11 (Sparck et al., 2016).
- Errors made with high confidence are corrected more often after feedback, but they can return after a week if the correct answer is forgotten (Butler et al., 2011, abstract).
- An AI tool for confidence calibration raised learning gains by 8.9% in a randomized study (N = 133). The tool bundled several supports, so the rating's own share cannot be separated (Lee et al., 2025, abstract).
- This bears on the earlier finding that requiring confidence ratings *and* explanations had the largest effect on practice exams (Ahmad et al., 2025, in `ai-agent-teaching-new-topics.md`). Together, the studies suggest the explanation may carry that effect. No study tested this directly.

### 1.4. Closed-book quizzes

**Evidence: contested.**

- In two university classes, one per condition, closed-book practice beat open-book on a surprise quiz 1 to 7 weeks later and on a later exam, with about 50 students (Rummer et al., 2019).
- In lab experiments, open-book and closed-book practice gave equivalent retention. Learners who expected a closed-book final test retained more than those who expected an open-book one (Agarwal, 2009; Agarwal & Roediger, 2011).

### 1.5. Records of attempts and progress

**Evidence: no achievement gain.**

- A review of 38 studies found "no evidence" that learning dashboards improve achievement, and many compared users with non-users (Kaliisa et al., 2023).
- A narrative synthesis of 26 studies of open learner models found mixed results, with the clearest gains in learners' monitoring and self-assessment, not achievement (Robles Mucho et al., 2026).

### 1.6. Whether structure stops learners from asking for answers

**Evidence: one observational preprint.**

- Answer-seeking made up 92.0% of conversations on unrestricted chat and 66.5% on pedagogically constrained tools. Resistance to scaffolding was the same on both (0.227 vs 0.223), and 49.0% of students ignored the tutor's guidance (Kobler et al., 2026).

### 1.7. Splitting a lesson between a chat and a page

**Evidence: indirect only.**

- No study measures this for AI tutors. Separating related information costs learners (Ginns, 2006, d = 0.85, as cited by Beege et al., 2019), but results are mixed, and the cost shrinks when the material is easy (Beege et al., 2019).

## 2. Where the evidence is weak or disagrees

- Open-book versus closed-book practice: one field study favours closed-book, while lab studies find equivalence and point to test expectancy instead.
- A reanalysis argues that the advantage of retrieval practice over concept mapping is a methodological artifact (Mayrhofer et al., 2023). Evidence that retrieval beats other study activities is therefore contested.
- The Rummer et al. (2019) paper gives the exam delay as 6 weeks in its abstract and 8 weeks in its methods.

## 3. Method

The coordinator ran four broadening searches, one in German, then seeded 10 questions on a shared research board. Five worker agents researched them in parallel. Two verifier agents opened the source of every claim the conclusion depends on: all 33 quotes were found on their pages, and 9 claims were corrected where they overstated a source. The board is in `.research/lesson-page-vs-chat-tutoring/`.

## 4. Open questions and blocked sources

- Low priority, open: which interface designs current AI tutoring products use, and whether any was evaluated on learning.
- Not read: Wenzel et al. (2022), a two-week replication of open- versus closed-book testing (bot check); McLaren (2022) and Johnson and Mayer (2010) on self-explanation prompt format (blocked); the full text of Lee et al. (2025).

## 5. Sources

Agarwal, P. K. (2009). *Test expectancy and transfer of knowledge with open-book and closed-book tests* [Doctoral dissertation, Washington University in St. Louis]. https://repository.library.washu.edu/etd/493

Agarwal, P. K., & Roediger, H. L. (2011). Expectancy of an open-book test decreases performance on a delayed closed-book test. *Memory, 19*(8), 836–852. https://profiles.wustl.edu/en/publications/expectancy-of-an-open-book-test-decreases-performance-on-a-delaye/

Bastani, H., Bastani, O., Sungu, A., Ge, H., Kabakcı, Ö., & Mariman, R. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *Proceedings of the National Academy of Sciences, 122*(26), e2422633122. https://ideas.repec.org/a/nas/journl/v122y2025pe2422633122.html

Beege, M., Wirzberger, M., Nebel, S., Schneider, S., Schmidt, N., & Rey, G. D. (2019). Spatial continuity effect vs. spatial contiguity failure. Revising the effects of spatial proximity between related and unrelated representations. *Frontiers in Education, 4*, 86. https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2019.00086/full

Bisra, K., Liu, Q., Nesbit, J. C., Salimi, F., & Winne, P. H. (2018). Inducing self-explanation: A meta-analysis. *Educational Psychology Review*. https://www.Gwern.net/doc/psychology/spaced-repetition/2018-bisra.pdf

Brender, J., El-Hamamsy, L., Uittenhove, K., Mondada, F., & Bumbacher, E. (2025). *Structured prompts, better outcomes? Exploring the effects of a structured interface with ChatGPT in a graduate robotics course*. arXiv. https://arxiv.org/abs/2507.07767

Butler, A. C., Fazio, L. K., & Marsh, E. J. (2011). The hypercorrection effect persists over a week, but high-confidence errors return. *Psychonomic Bulletin & Review, 18*(6), 1238–1244. https://profiles.wustl.edu/en/publications/the-hypercorrection-effect-persists-over-a-week-but-high-confiden/

Chen, E., Judicke, S., Beigh, K., et al. (2026a). *Chat-based support alone may not be enough: Comparing conversational and embedded LLM feedback for mathematical proof learning*. arXiv. https://arxiv.org/abs/2602.18807

Chen, E., Tang, X., Zhao, Y., Chen, M., Elmir, M., McLaughlin, E., Yuan, M., Wang, Y., Agarwal, S., Cochrane, J., Lin, J., Wu, T., & Koedinger, K. (2026b). *Practice less, explain more: LLM-supported self-explanation improves explanation quality on transfer problems in calculus*. arXiv. https://arxiv.org/abs/2604.00142

Kaliisa, R., Misiejuk, K., López-Pernas, S., Khalil, M., & Saqr, M. (2023). *Have learning analytics dashboards lived up to the hype? A systematic review of impact on students' achievement, motivation, participation and attitude*. arXiv. https://arxiv.org/abs/2312.15042

Kobler, S., Clemson, M., Sun, A., & Kummerfeld, J. K. (2026). *Your students don't use LLMs like you wish they did*. arXiv. https://arxiv.org/html/2604.23486v1

Lee, H. J., Stinar, F., Zong, R., Valdiviejas, H., Wang, D., & Bosch, N. (2025). Learning behaviors mediate the effect of AI-powered support for metacognitive calibration on learning outcomes. In *CHI 2025 Proceedings*. ACM. https://experts.illinois.edu/en/publications/learning-behaviors-mediate-the-effect-of-ai-powered-support-for-m/

Mayrhofer, R., Kuhbandner, C., & Frischholz, K. (2023). Re-examining the testing effect as a learning strategy: The advantage of retrieval practice over concept mapping as a methodological artifact. *Frontiers in Psychology, 14*. https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1258359/full

Pardos, Z. A., & Bhandari, S. (2024). ChatGPT-generated help produces learning gains equivalent to human tutor-authored help on mathematics skills. *PLOS ONE*. https://scale.stanford.edu/publications/chatgpt-generated-help-produces-learning-gains-equivalent-human-tutor-authored-help

Robles Mucho, J. L., Andrade-Girón, D. C., et al. (2026). Open learner models and pedagogical strategies in higher education: A meta-synthesis of approaches to self-regulated learning. *Frontiers in Education, 10*. https://www.frontiersin.org/articles/10.3389/feduc.2025.1760183

Rummer, R., Schweppe, J., & Schwede, A. (2019). Open-book versus closed-book tests in university classes: A field experiment. *Frontiers in Psychology, 10*. https://www.frontiersin.org/articles/10.3389/fpsyg.2019.00463/full

Sparck, E. M., Bjork, E. L., & Bjork, R. A. (2016). On the learning benefits of confidence-weighted testing. *Cognitive Research: Principles and Implications, 1*, 3. https://pmc.ncbi.nlm.nih.gov/articles/PMC5256426/

VanLehn, K. (2011). The relative effectiveness of human tutoring, intelligent tutoring systems, and other tutoring systems. *Educational Psychologist, 46*(4), 197–221. https://eric.ed.gov/?id=EJ946764
