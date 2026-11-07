# How an AI agent should teach a user a new topic

Research register · Search date: 7 November 2026

**Scope.** How an AI agent should order the material, check understanding, and give feedback so that a user learns a new topic. The focus is on practices backed by evidence, and on where that evidence is weak or disputed, to inform agent instructions such as a skill.

**Status.** 11 questions answered, 5 contested, and 3 not found. Two medium-priority questions remain open because their sources were blocked (section 4). Most of the evidence comes from school and university students in courses, mostly in STEM subjects, with short-term outcomes. No study covered adults teaching themselves outside a course.

The best-supported rule is that the agent should not hand over answers. It should make the learner try first, and then guide them with hints, questions and worked examples. In a randomized study, students who had unrestricted access to GPT-4 scored 17% lower than the control group once the AI was taken away. A tutor that gave hints instead of answers prevented that drop (Bastani et al., 2025). Most of the remaining structure rests on learning-science research done without LLMs, or on small, early LLM studies.

## 1. Suggested structure, with how strong the evidence is

### 1.1. Withhold answers and guide with hints or questions

**Evidence: fairly strong for avoiding harm; weak for producing gains.**

- In a study of about 1,000 high-school maths students, unrestricted GPT-4 raised practice grades by 48%. On a later closed-book exam, the same students scored 17% lower than students without AI.
- A hint-only tutor raised practice grades by 127%, but its students scored about the same as the control group on the exam. It removed the harm without adding a gain (Bastani et al., 2025).
- Contractor and Reyes (2026) randomized 211 undergraduates who studied an unfamiliar topic with or without AI. A smaller gain remained one week later, on a test taken without AI. That gain held for students who used the AI "as a tutor" and faded for those who had it write for them. This split by use was observed, not randomized.
- In a graduate robotics course, students rated a Socratic tutor as less efficient. Those students later showed higher learning gains (Brender et al., 2026).

### 1.2. Ask the learner to attempt the problem before the agent explains

**Evidence: contested.**

- In a randomized experiment, students who attempted a problem before using ChatGPT did better on a later test (Akgun & Toker, 2024). In their follow-up studies, the benefit was largest on complex, exploratory tasks and smaller on simple computational ones (Akgun & Toker, 2025). Both are preprints, and the follow-up reuses the first study's cohort. Neither says whether the final test was taken without AI.
- Another study found the opposite for one variant: asking learners to explain the material to themselves before using GenAI reduced transfer, especially for learners unfamiliar with the topic (Lepennetier et al., 2026). Transfer here means applying the knowledge to new problems.

### 1.3. Order the lesson: key terms first, small chunks, a worked example before each practice problem, and less help as the learner improves

**Evidence: good for teaching in general; almost none for LLM tutors.**

- Teaching the names and features of the main concepts before the lesson ("pre-training") helped in 13 of 16 tests. Splitting a lesson into chunks that learners advance through at their own pace ("segmenting") helped in 10 of 10 tests (Mayer & Pilegard, 2014).
- Studying a worked example and then solving a similar problem worked better than problem solving alone (van Gog et al., 2010).
- Gradually removing worked-out steps as the learner shows understanding ("fading") beat fixed fading, which beat plain problem solving (Renkl et al., 2000; Salden et al., 2010).
- In an AI tutor for a five-month Python course, choosing practice problems to fit each student raised exam scores, on an exam taken without help, by 0.15 standard deviations compared with a fixed problem order (Chung et al., 2026, preprint).
- No study tested the order of steps inside an LLM tutoring session.

### 1.4. Quiz the learner and space practice over time

**Evidence: strong in general; thin for LLMs.**

- A large review rated practice testing and spaced practice as the most useful study techniques. Summarizing, highlighting and rereading were rated low (Dunlosky et al., 2013).
- In a non-randomized study of about 60 students, a week with LLM-generated quiz questions produced 89% accuracy on a retention quiz, against 73% in a week without them. The authors warn that question quality varies (An et al., 2025).

### 1.5. Give feedback, but don't expect the type of feedback to matter much

**Evidence: small effects.**

- The type of GPT-4o feedback on practice exams made no significant difference to performance. Requiring students to rate their confidence and explain their answers had the largest effect (Ahmad et al., 2025).
- LLM feedback helped in only 2 of 7 lessons, and only when learners chose to use it (Thomas et al., 2025).
- ChatGPT hints produced learning gains with no significant difference from hints written by human tutors. However, 32% of the ChatGPT hints failed quality checks before filtering (Pardos & Bhandari, 2024).
- About 7% of 2,389 GPT-4 feedback messages on statistics exams contained errors (Herklotz et al., 2025).

### 1.6. Check understanding with tasks done without the AI, because learners overestimate what they know

**Evidence: consistent.**

- Students using the hint-only tutor believed they had done significantly better on the exam, but they had not (Bastani et al., 2025).
- People solving reasoning problems with AI overestimated their own score by four points (Fernandes et al., 2024).
- Novice programmers who struggled with AI finished "with an illusion of competence" (Prather et al., 2024).
- Asking learners to explain in their own words, with LLM feedback, improved the quality of their explanations on one type of transfer problem. It did not change post-test scores (Chen et al., 2026).

### 1.7. Expect the learner to push back on being challenged

**Evidence: the pushback is documented; the remedies are untested for AI.**

- In a survey, 68% of students preferred direct help over indirect guidance (Ma et al., 2026).
- In physics classes, students learned more from active teaching but rated their own learning lower (Deslauriers et al., 2019). After a 20-minute talk explaining this gap, 75% of students said they felt more favourable toward active learning. That figure is self-reported.

## 2. Where the evidence is weak or disagrees

- **Who was studied.** Almost all studies cover school or university students in courses, mostly in STEM subjects, with short-term outcomes. Searches found no study comparing self-directed adults with students in courses. The closest match to an adult learning on their own is Contractor and Reyes (2026): undergraduates learning an unfamiliar topic.
- **Personalization.** Results disagree. In one study, examples personalized by generative AI raised motivation but did not change learning (Leong et al., 2024, n=272).
- **Overall effect of LLMs.** A preprint meta-analysis of 133 studies found the effect of LLMs on learning "positive but uneven" (Huang et al., 2025).
- **Vendor tutoring modes.** Anthropic describes its Learning mode as guiding reasoning instead of giving answers, and reports no evaluation (Anthropic, 2025). The ChatGPT study-mode instructions are known only from a copy a blogger got ChatGPT to output. They tell the model to ask about the user's goals and level first and not to do the user's work (Willison, 2025).
- **Google's Guided Learning.** Google reports two randomized trials of Guided Learning, its tutoring mode in Gemini (Cornelis & Johnson, 2026; LearnLM Team, Google & Fab AI, 2026). Both are reported by Google itself, and neither says whether the final test was taken without AI.
- **Strong results in the wrong comparison.** In a Harvard physics trial, an AI tutor beat in-class active learning (Kestin et al., 2025). It was not compared with an AI that gives answers, and the paper does not say whether the post-test allowed AI.

## 3. Method

- Research board: `.research/ai-agent-tutoring-structure/` (not committed). It holds every question, claim and source, with each source marked by how it was read.
- Workers on a cheaper model researched the questions. The coordinator checked every quote cited above against its source page, except the blocked items in section 4.
- Many papers were readable only as abstracts. PDFs could not be rendered in this environment, so full texts were read only where an HTML copy existed (arXiv HTML, Europe PMC).

## 4. Open questions

- **How to quickly test what a learner already knows before choosing how much help to give.** The main papers on "rapid knowledge tests" (Kalyuga & Sweller, 2004, 2005) were blocked or unreadable.
- **Whether learners miss tutor errors that match their own misconceptions.** The only lead (eScholarship paper 9pk053k6) could not be read.
- **Whether the 17% exam drop has been replicated in other populations.** No direct replication was found.
- **Whether explaining why an answer is wrong beats only saying whether it is right.** The relevant papers appeared only in search results and could not be read.

## 5. Sources

Ahmad, M., Ravi, P., Karger, D., & Facciotti, M. (2025). *How adding metacognitive requirements in support of AI feedback in practice exams transforms student learning behaviors*. arXiv. https://arxiv.org/html/2505.13381v1

Akgun, M., & Toker, S. (2024). *Evaluating the effect of pretesting with conversational AI on retention of needed information*. arXiv. https://arxiv.org/abs/2412.13487

Akgun, M., & Toker, S. (2025). *Struggle first, prompt later: How task complexity shapes learning with GenAI-assisted pretesting*. arXiv. https://arxiv.org/abs/2504.10249v1

An, Y., Liu, J., Acharya, N., & Hashmi, R. (2025). *Enhancing student learning with LLM-generated retrieval practice questions: An empirical study in data science courses*. arXiv. https://arxiv.org/abs/2507.05629v2

Anthropic. (2025, April 2). *Introducing Claude for Education*. https://www.anthropic.com/news/introducing-claude-for-education

Bastani, H., Bastani, O., Sungu, A., Ge, H., Kabakcı, Ö., & Mariman, R. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *Proceedings of the National Academy of Sciences, 122*(26), e2422633122. https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12232635/fullTextXML

Brender, J., El-Hamamsy, L., Uittenhove, K., Perez, A., Jermann, P., Mondada, F., & Bumbacher, E. (2026). *Reflective dialogue or prompt refinement? Effects of tutor scaffolding on students' independent LLM use for programming*. arXiv. https://www.alphaxiv.org/abs/2607.03303

Chen, E., Tang, X., Zhao, Y., Chen, M., Elmir, M., McLaughlin, E., Yuan, M., Wang, Y., Agarwal, S., Cochrane, J., Lin, J., Wu, T., & Koedinger, K. (2026). *Practice less, explain more: LLM-supported self-explanation improves explanation quality on transfer problems in calculus*. arXiv. https://arxiv.org/html/2604.00142v1

Chung, A. T.-H., Zhang, B., Kung, L.-C., Bastani, H., & Bastani, O. (2026). *Effective personalized AI tutors via LLM-guided reinforcement learning*. arXiv. https://arxiv.org/abs/2608.16907

Contractor, Z., & Reyes, G. (2026). *Experimental evidence on the learning impact of generative AI*. arXiv. https://arxiv.org/html/2607.08849v2

Cornelis, S., & Johnson, A. (2026, November 3). *New research shows how Guided Learning supports students*. Google, The Keyword. https://blog.google/products-and-platforms/products/education/guided-learning-uk-japan/

Deslauriers, L., McCarty, L. S., Miller, K., Callaghan, K., & Kestin, G. (2019). Measuring actual learning versus feeling of learning in response to being actively engaged in the classroom. *Proceedings of the National Academy of Sciences, 116*(39). https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6765278/fullTextXML

Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham, D. T. (2013). Improving students' learning with effective learning techniques. *Psychological Science in the Public Interest, 14*(1), 4–58. https://stafforini.com/works/dunlosky-2013-improving-students-learning/

Fernandes, D., Villa, S., Nicholls, S., Haavisto, O., Buschek, D., Schmidt, A., Kosch, T., Shen, C., & Welsch, R. (2024). *AI makes you smarter, but none the wiser: The disconnect between performance and metacognition*. arXiv. https://arxiv.org/abs/2409.16708v1

Herklotz, M., Ippisch, N., & Haensch, A.-C. (2025). *Can we trust LLMs as a tutor for our students? Evaluating the quality of LLM-generated feedback in statistics exams*. arXiv. https://arxiv.org/abs/2511.04213v1

Huang, J., Wang, R. R., Liu, J.-H., Xia, B., Huang, Y., Sun, R., Xue, J. M., & Zou, J. (2025). *A meta-analysis of LLM effects on students across qualification, socialisation, and subjectification*. arXiv. https://arxiv.org/abs/2509.22725

Kestin, G., Miller, K., Klales, A., Milbourne, T., & Ponti, G. (2025). AI tutoring outperforms in-class active learning: An RCT introducing a novel research-based design in an authentic educational setting. *Scientific Reports, 15*, 17458. https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12179260/fullTextXML

LearnLM Team, Google, & Fab AI. (2026). *Teaching with Gemini: Measuring the impact of Guided Learning on student mathematics progress in Sierra Leone*. Stanford SCALE AI Repository. https://scale.stanford.edu/ai/repository/teaching-gemini-measuring-impact-guided-learning-student-mathematics-progress-sierra

Leong, J., Pataranutaporn, P., Danry, V., Perteneder, F., Mao, Y., & Maes, P. (2024). *Putting things into context: Generative AI-enabled context personalization for vocabulary learning improves learning motivation*. MIT Media Lab. https://www.media.mit.edu/projects/ai-enabled-context-personalization/overview/

Lepennetier, S., Fleury, S., Lepont, V., Hamdani, F., & Meyrueis, V. (2026). Generative AI-assisted learning: An unexpected detrimental interaction with self-explanation. *AMCIS 2026 Proceedings*. AIS Electronic Library. https://aisel.aisnet.org/amcis2026/sig_ed/sig_ed/9/

Ma, B., Xie, Y., Li, H., Li, G., Chen, L., Shimada, A., & Konomi, S. (2026). *Design implications for student and educator needs in AI-supported programming learning tools*. arXiv. https://arxiv.org/html/2603.22673v1

Mayer, R. E., & Pilegard, C. (2014). Principles for managing essential processing in multimedia learning: Segmenting, pre-training, and modality principles. In R. E. Mayer (Ed.), *The Cambridge handbook of multimedia learning* (2nd ed., pp. 316–344). Cambridge University Press. https://www.cambridge.org/core/services/aop-cambridge-core/content/view/DD24C2F48B9B1277CE59F78276110258

Pardos, Z. A., & Bhandari, S. (2024). ChatGPT-generated help produces learning gains equivalent to human tutor-authored help on mathematics skills. *PLOS ONE, 19*(5), e0304013. https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11125466/fullTextXML

Prather, J., Reeves, B., Leinonen, J., MacNeil, S., Randrianasolo, A. S., Becker, B., Kimmel, B., Wright, J., & Briggs, B. (2024). *The widening gap: The benefits and harms of generative AI for novice programmers*. arXiv. https://arxiv.org/abs/2405.17739

Renkl, A., Atkinson, R. K., & Maier, U. H. (2000). *From example study to problem solving: Smooth transitions help learning* (Forschungsbericht Nr. 140). Psychologisches Institut der Universität Freiburg; PsychArchives. https://www.psycharchives.org/handle/20.500.11780/196

Salden, R. J. C. M., Aleven, V., Schwonke, R., & Renkl, A. (2010). The expertise reversal effect and worked examples in tutored problem solving. *Instructional Science, 38*(3), 289–307. https://researchportal.hw.ac.uk/en/publications/the-expertise-reversal-effect-and-worked-examples-in-tutored-prob/

Thomas, D. R., Borchers, C., Bhushan, S., Gatz, E., Gupta, S., & Koedinger, K. R. (2025). *LLM-generated feedback supports learning if learners choose to use it*. arXiv. https://arxiv.org/abs/2506.17006

van Gog, T., Kester, L., & Paas, F. (2010). *Effects of worked examples, example-problem pairs, and problem-example pairs compared to problem solving* [Conference paper, EARLI SIG meeting, Ulm]. Open Universiteit. https://research.ou.nl/en/publications/effects-of-worked-examples-example-problem-pairs-and-problem-exam/

Willison, S. (2025, July 29). *OpenAI: Introducing study mode*. Simon Willison's Weblog. https://simonwillison.net/2025/Jul/29/openai-introducing-study-mode/
