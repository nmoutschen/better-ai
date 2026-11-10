# Teaching for use, not recall, for an AI agent that teaches one user

Research register · Search date: 10 November 2026

**Scope.** What makes a learner actually use what they learned in a one-to-one lesson, in their own work or life, as opposed to remembering it on a test. Training research calls the first "typical transfer" and the second "maximum transfer". The register covers predictors of use that a tutor can influence, practice on tasks like the real ones, plans for when to use a skill, references used while doing the task, follow-up on real use, chances to use the skill, varied practice, application questions against fact questions, and confidence after training. It applies these to the `teach-better` skill. It revises the recall-oriented advice in `sources/take-away-after-lesson-for-teaching.md` and `sources/long-term-recall-for-teaching.md`.

**Status.** 10 questions closed, all answered, most on thin evidence. The coordinator checked 28 quotes against their sources. Most evidence comes from workplace training, medical simulations and lab studies, often small, and much of it was read as abstracts. No study tested an AI tutor teaching for later use.

What people can do after training and what they actually do correlate only weakly. Ability factors, such as knowledge and skill acquired, predicted what people can do. Motivation factors predicted what they actually do: confidence after training, motivation to use the skill, conscientiousness and workplace support (Huang et al., 2015). A test score after a lesson is therefore a poor guide to whether the user will use the topic. Three things a tutor controls went with more use: practice that resembles the real task (van der Locht et al., 2013), if-then plans for when to use a skill (Friedman & Ronen, 2015), and feedback on real use (Grossman & Salas, 2011).

## 1. Evidence, with how strong it is

### 1.1. Use depends on more than what was learned

**Evidence: one meta-analysis, read as an abstract and in an open full text.**

- "Maximum and typical transfer were only weakly correlated and, as hypothesized, were predicted by different antecedents" (Huang et al., 2015).
- "Ability factors including declarative knowledge, skill acquisition, and cognitive ability were stronger predictors of maximum transfer, whereas motivation factors including posttraining self-efficacy, motivation to transfer, conscientiousness, and workplace support were stronger predictors of typical transfer" (Huang et al., 2015).
- A review identifies training design (behavioural modelling, error management, realistic training environments) and the work environment (transfer climate, support, opportunity to perform, follow-up) as factors with the strongest links to transfer (Grossman & Salas, 2011).

### 1.2. Practice that resembles the real task

**Evidence: indirect.**

- In a survey of 595 managers, identical elements (training that resembles the work situation), expected utility and motivation to learn "each had a unique contribution to the prediction of training transfer" (van der Locht et al., 2013).
- "Aspects of training should mirror the environment in which trained competencies will be applied as closely as possible" (Grossman & Salas, 2011).
- In an algebra tutor, problems built on students' own interests triggered interest, and "triggered interest predicted in-tutor outcomes (accuracy, learning efficiency)" (Bernacki & Walkington, 2018, abstract only). This differs from personalising to hobbies, which raised motivation without improving learning (`sources/ai-agent-teaching-new-topics.md`).
- No study compared practice on the learner's own tasks with generic practice, measured by later real use.

### 1.3. Plans for when and where to use the skill

**Evidence: two small training experiments, and a large meta-analysis outside training.**

- Trainees who formed implementation intentions "implemented active listening skills sooner, and to a greater degree, than those in the control group" (N = 37). In a field experiment (n = 28), they scored higher on using the trained behaviour (Friedman & Ronen, 2015, abstract only).
- Across 642 tests, implementation intentions were effective "for cognitive, affective, and behavioural outcomes (.27 ≤ d ≤ .66)". "Effect sizes were larger when plans had a contingent (if-then) format, participants were highly motivated to pursue the goal, and plans were rehearsed" (Sheeran et al., 2024, abstract only).

### 1.4. A reference at hand, and what it cannot supply

**Evidence: randomized simulations in medicine and process control.**

- "Failure to adhere to lifesaving processes of care was less common during simulations when checklists were available (6% of steps missed when checklists were available vs. 23% when they were unavailable)". "Every team performed better when the crisis checklists were available than when they were not" (Arriaga et al., 2013, abstract only).
- "Approximately, 1 of 3 trainees assigned to use a CA (electronic 29%, paper 36%) chose not to use it during the scenario." The authors stress "training clinicians in when and how to use an emergency CA" (Watkins et al., 2016, abstract only). CA means cognitive aid.
- People trained on how the system works "performed better, especially for less familiar and complex faults", than people trained on procedures (Hockey et al., 2007, abstract only). In an earlier study, people trained on diagnostic rules "performed less well on novel faults (but did equally well on familiar faults)" (Sauer et al., 2000).
- "Job aids facilitate transfer by providing important instructions and other reference materials, thereby reducing the mental workload required to apply new skills" (Grossman & Salas, 2011).
- No study tested how people recognise when a rule applies. The finding on new faults suggests that a reference cannot replace understanding how a procedure works.

### 1.5. Feedback and follow-up on real use

**Evidence: one meta-analysis of teacher coaching, one uncontrolled study, one review.**

- Coaching teachers on their real work gave "pooled effect sizes of 0.49 standard deviations (SD) on instruction and 0.18 SD on achievement". The authors note the "challenges of taking coaching programs to scale while maintaining effectiveness" (Kraft et al., 2018, abstract only).
- In a public agency, "Training increased productivity by 22.4 percent", and eight weeks of one-on-one coaching after it raised the gain to 88.0%. The study had no separate control group (Olivero et al., 1997).
- "Post-training interventions such as relapse prevention, self-management, goal setting, training in self-talk and post-training instructor follow-ups generally show positive effects on the transfer of training" (Grossman & Salas, 2011).
- No study compared follow-up on real use with review of content.

### 1.6. Chances to use the skill

**Evidence: reviews and decay meta-analyses.**

- Clarke (2002) identified "limited opportunity to perform skills on the job as the strongest barrier to successful training transfer" (as reported by Grossman & Salas, 2011).
- The review advises that the "delay between training and opportunity for trainees to use their learned skills should be minimized" (Grossman & Salas, 2011, citing Salas et al., 2006).
- Skill loss reached d = −1.4 after more than a year without use (Arthur et al., 1998). Half of the gains in accuracy were lost after about 6.5 months without use (Tatel & Ackerman, 2025, abstract only).

### 1.7. Application questions against fact questions

**Evidence: classroom experiments, read through the author's blog; one meta-analysis.**

- In classroom experiments, fact quizzes improved fact tests, and "higher order retrieval improved performance on a higher order test". "A mix of questions benefitted performance on both types of tests" (Agarwal, 2019).
- Recall practice transferred to new questions on average (d = 0.40), but "often indicating no positive transfer when none of the aforementioned moderators are present" (Pan & Rickard, 2018).

### 1.8. Varied practice

**Evidence: one cross-domain review; thin.**

- "More variability tends to make initial learning more challenging" but tends to produce more general learning (Raviv et al., 2022, abstract only).
- A pilot study of pianists gave "only partial support" for varied practice (Bangert et al., 2014).

### 1.9. Confidence after training

**Evidence: one meta-analysis and one experiment; how to raise it accurately is unknown.**

- Confidence after training predicted actual use more than it predicted test performance (Huang et al., 2015).
- "Self-efficacy predicted performance in jobs or tasks of low complexity, but not those of medium or high complexity" (Judge et al., 2007, as reported by Grossman & Salas, 2011).
- In negotiation training, "pre-test self-efficacy contributed positively to both initial and delayed performance" six weeks later (Gist et al., 1991, abstract only).
- No study tested how to raise confidence accurately, for example through success on realistic tasks.

## 2. Where the evidence is weak or disagrees

- **Settings.** Workplace training, medical simulations and lab tasks dominate. No study covered adults learning alone with an AI tutor.
- **Personalising problems.** Problems built on interests raised performance in an algebra tutor (Bernacki & Walkington, 2018). Personalised examples raised motivation without improving vocabulary learning (Leong et al., 2024, in `sources/ai-agent-teaching-new-topics.md`). Practice resembling the real task is a different manipulation from either, and has only survey evidence.
- **Recall and use.** The earlier registers show that retrieval practice and spacing improve recall. This register shows that recall predicts what people can do more than what they do.

## 3. What this means for `teach-better`

These are inferences from the evidence above, not tested rules.

1. **Find out where and when the user will use the topic.** Build practice, quizzes and the take-away around those situations.
2. **Make most practice and quiz questions tasks the user will do.** Questions train the kind of task they ask for. Ask for a fact only when the user must know it without looking it up.
3. **End with if-then plans.** The user writes one to three "When <situation>, I will <step>" plans and rehearses them.
4. **Recast the take-away as a reference for use.** Lead with when to use the topic, because a reference cannot tell the user when to open it. Give steps as a checklist, and say why the steps work, to help with new cases. Then the user practises one task with the take-away open.
5. **Prefer real use and feedback on it over review of content.** Suggest a first use soon. Offer a follow-up on a real attempt.
6. **Keep spaced practice only for skills the user will not use soon,** with tasks rather than recall questions.
7. **Do not read a quiz score as evidence that the user will use the topic.**

## 4. Method

- Research board: `.research/transfer-to-use/` (not committed). It holds every question, claim and source, with each source marked by how it was read.
- Workers on a cheaper model researched the questions. Broadening searches included one in German. The coordinator checked 28 quotes against their sources, through Europe PMC and Crossref abstracts and open full texts.
- Two claims from Adams (1992) on spontaneous use of facts could not be rechecked and are not used. Morris et al. (1977) and Perfetto et al. (1983) were blocked.

## 5. Open questions

- **Practice on the learner's own tasks** against generic practice, measured by later real use.
- **Recognising when a rule applies**, and how to teach it.
- **Follow-up on real use against review of content.**
- **Raising confidence accurately** after a lesson.
- **Any of the above with an AI tutor** or with adults learning alone.

## 6. Sources

Agarwal, P. K. (2019, March 27). *Chicken, eggs, and Bloom's taxonomy: Fact knowledge before higher order learning?* RetrievalPractice.org. http://www.retrievalpractice.org/strategies/2019/3/27/blooms-taxonomy

Arriaga, A. F., Bader, A. M., Wong, J. M., Lipsitz, S. R., Berry, W. R., Ziewacz, J. E., Hepner, D. L., Boorman, D. J., Pozner, C. N., Smink, D. S., & Gawande, A. A. (2013). Simulation-based trial of surgical-crisis checklists. *The New England Journal of Medicine, 368*(3), 246–253. https://doi.org/10.1056/NEJMsa1204720

Arthur, W., Jr., Bennett, W., Jr., Stanush, P. L., & McNelly, T. L. (1998). Factors that influence skill decay and retention: A quantitative review and analysis. *Human Performance, 11*(1), 57–101. https://www.Gwern.net/doc/psychology/spaced-repetition/1998-arthur.pdf

Bangert, M., Wiedemann, A., & Jabusch, H.-C. (2014). Effects of variability of practice in music: A pilot study on fast goal-directed movements in pianists. *Frontiers in Human Neuroscience, 8*, 598. https://pmc.ncbi.nlm.nih.gov/articles/PMC4128393

Bernacki, M. L., & Walkington, C. (2018). The role of situational interest in personalized learning. *Journal of Educational Psychology, 110*(6), 864–881. https://oasis.library.unlv.edu/edpsych_fac_articles/190

Friedman, S., & Ronen, S. (2015). The effect of implementation intentions on transfer of training. *European Journal of Social Psychology*. https://doi.org/10.1002/ejsp.2114

Gist, M. E., Stevens, C. K., & Bavetta, A. G. (1991). Effects of self-efficacy and post-training intervention on the acquisition and maintenance of complex interpersonal skills. *Personnel Psychology*. https://doi.org/10.1111/j.1744-6570.1991.tb00701.x

Grossman, R., & Salas, E. (2011). The transfer of training: What really matters. *International Journal of Training and Development, 15*(2), 103–120. https://ftq.qc.ca/wp-content/uploads/sites/5/2019/04/Grossman_et_al-2011-International_Journal_of_Training_and_Development.pdf

Hockey, G. R. J., Sauer, J., & Wastell, D. G. (2007). Adaptability of training in simulated process control: Knowledge- versus rule-based guidance under task changes and environmental stress. *Human Factors, 49*(1), 158–174. https://europepmc.org/search?query=%22Adaptability%20of%20training%20in%20simulated%20process%20control%22

Huang, J. L., Blume, B. D., Ford, J. K., & Baldwin, T. T. (2015). A tale of two transfers: Disentangling maximum and typical transfer and their respective predictors. *Journal of Business and Psychology, 30*(4), 709–732. https://link.springer.com/article/10.1007/s10869-014-9394-1

Kraft, M., Blazar, D., & Hogan, D. (2018). The effect of teacher coaching on instruction and achievement: A meta-analysis of the causal evidence. *Review of Educational Research, 88*(4), 547–588. https://annenberg.brown.edu/publications/effect-teacher-coaching-instruction-and-achievement-meta-analysis-causal-evidence

Olivero, G., Bane, K. D., & Kopelman, R. E. (1997). Executive coaching as a transfer of training tool: Effects on productivity in a public agency. *Public Personnel Management, 26*(4), 461–469. https://www.vabankers.org/sites/main/files/file-attachments/executivecoachingasatransferoftrainingtool.pdf

Pan, S. C., & Rickard, T. C. (2018). Transfer of test-enhanced learning: Meta-analytic review and synthesis. *Psychological Bulletin, 144*(7), 710–756. https://sc-pan.github.io/pdf/PR_2018.pdf

Raviv, L., Lupyan, G., & Green, S. C. (2022). How variability shapes learning and generalization. *Trends in Cognitive Sciences, 26*(6), 462–483. https://eprints.gla.ac.uk/272070

Sauer, J., Hockey, G. R. J., & Wastell, D. G. (2000). Effects of training on short- and long-term skill retention in a complex multiple-task environment. *Ergonomics, 43*(12), 2043–2064. https://folia.unifr.ch/documents/301282/files/SauerHockeyWastell2000_draft.pdf

Sheeran, P., Listrom, O., & Gollwitzer, P. M. (2024). The when and how of planning: Meta-analysis of the scope and components of implementation intentions in 642 tests. *European Review of Social Psychology*. https://doi.org/10.1080/10463283.2024.2334563

Tatel, C. E., & Ackerman, P. L. (2025). Procedural skill retention and decay: A meta-analytic review. *Psychological Bulletin, 151*(6), 696–736. https://pubmed.ncbi.nlm.nih.gov/40455501/

van der Locht, M., van Dam, K., & Chiaburu, D. S. (2013). Getting the most of management training: The role of identical elements for training transfer. *Personnel Review, 42*(4), 422–439. https://www.emerald.com/insight/content/doi/10.1108/PR-05-2011-0072/full/html

Watkins, S. C., Anders, S., Clebone, A., Hughes, E., Patel, V., Zeigler, L., Shi, Y., Shotwell, M. S., McEvoy, M. D., & Weinger, M. B. (2016). Mode of information delivery does not effect anesthesia trainee performance during simulated perioperative pediatric critical events: A trial of paper versus electronic cognitive aids. *Simulation in Healthcare*. https://pubmed.ncbi.nlm.nih.gov/27922569/
