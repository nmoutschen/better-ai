# Static self-study material, for an AI agent that writes lessons for unknown readers

Research register · Search date: 11 November 2026

**Scope.** What makes lesson material effective when it is written once and studied alone, with no tutor to check the reader's work. Such material includes web pages, workbooks and self-paced modules. The register covers access to worked solutions, hints on request, self-explanation and self-test prompts, feedback without a tutor, readers whose prior knowledge is unknown, spaced review, and module structure. It informs a static generation mode for the `teach-better` skill, as distinct from its 1:1 tutor mode.

**Status.** 11 questions closed as answered, most on thin evidence. One low-priority question on terms stayed open. Many publisher pages were blocked, so much of the evidence comes from abstracts. 22 quotes the conclusions depend on were checked against the source. No study tested click-to-reveal solutions, hint sequences or self-check pretests in static text material.

The strongest finding is that prompts asking readers to explain the material work in print as well as on screen. They work about as well when nobody checks the explanation (Bisra et al., 2018). The second strongest is that explanations beat bare answers as feedback (van der Kleij et al., 2015). Both findings come from meta-analyses. Everything about how readers use solutions and hints when left alone rests on single studies, mostly from tutoring software.

## 1. Evidence, with how strong it is

### 1.1. Self-explanation prompts without a checker

**Evidence: one meta-analysis, read in full.**

- Prompting learners to self-explain had an overall effect of g = .55 across 69 effect sizes: "The overall weighted mean effect size using a random effects model was g = .55" (Bisra et al., 2018).
- Print (g = .550, k = 21) and digital material (g = .550, k = 42) had the same effect. Material with no interactivity (g = .575, k = 50) did as well as computer-based instruction (.587) or tutoring systems (.483). No difference between media or levels of interactivity was significant (Bisra et al., 2018, Table 5).
- When researchers verified that learners self-explained, the effect was g = .613 (k = 31). When they did not, it was .409 (k = 21). The difference was not significant (QB = 4.735, p = .192) (Bisra et al., 2018, Table 8).
- Most prompt features did not matter: "variation in these factors rarely matters when learners self-explain" (Bisra et al., 2018).
- Two features did matter:
  - Multiple-choice prompts had "an effect size (g = .24) not statistically different from zero", in only 2 studies. The authors suggest that strong cues in the prompt undermine self-explanation (Bisra et al., 2018).
  - Prompts asking for conceptual explanations "were more effective than those inducing metacognitive self-explanations" (Bisra et al., 2018).
- Explanations on demand can undercut prompts. In one study reviewed, "making a relevant instructional explanation available undermines learners' incentive to self-explain effortfully" (Bisra et al., 2018, describing Schworm & Renkl).
- Prompts written once by an instructor "may be suitable for instructional settings in which the same readings or problems are assigned to many students" (Bisra et al., 2018).
- Gap: no source measured how often readers skip prompts when nothing checks them.

### 1.2. Self-tests without feedback

**Evidence: one review chapter, read in full.**

- "Retrieval practice promotes long term retention, even in the absence of feedback. However, successful retrieval at practice is critical in learning from tests" (Shanks et al., 2023).
- Learners use self-tests too little: "learners tend to underappreciate the merits of practice tests, leading to their underemployment" (Shanks et al., 2023).
- Learners self-test more "when the tests are easy, … or when feedback or an opportunity to restudy is provided during testing" (Shanks et al., 2023).
- A wrong multiple-choice pick can be remembered as true. "This effect is heavily dependent on corrective feedback being withheld in the practice MCQ test" (Shanks et al., 2023).

### 1.3. Feedback: explanations against answer keys

**Evidence: one meta-analysis, read as an abstract; erroneous examples mixed.**

- Across 40 studies of computer-based feedback, "elaborated feedback (EF; e.g., providing an explanation) produced larger effect sizes (0.49) than feedback regarding the correctness of the answer (KR; 0.05) or providing the correct answer (KCR; 0.32)." Also: "EF was particularly more effective than KR and KCR for higher order learning outcomes" (van der Kleij et al., 2015).
- Studies of erroneous examples, which are wrong solutions for the learner to find and fix, report that "EE compared with CE may indeed have a positive impact on learning". Effects depend on moderators such as prior knowledge, and the 2022 experiment that reviewed them found no effect of order or congruency (Wesenberg et al., 2022). The original studies could not be read.

### 1.4. Access to worked solutions

**Evidence: thin; one study on use, indirect evidence on effect.**

- When answers were one click away, students tried a question at least once before viewing its solution 84% of the time on average ("a rather high 84%"). This held across 550 students in four classes. Earnestness fell as the course went on, mostly from tiredness and other student factors rather than question difficulty (Yuen et al., 2016, abstract).
- Whether early access lowers learning could not be read from any full text. Papers on solution-manual use were blocked.
- Indirect evidence points both ways:
  - In an engineering course, feedback given one week after the homework deadline led to better exam performance on new problems about the same concepts. Students still preferred immediate feedback, "revealing a metacognitive disconnect between actual and perceived effectiveness" (Mullet et al., 2014, abstract).
  - Students who observed another learner's whole productive-failure process "even outperformed students who engaged in PF themselves" (Hartmann et al., 2021, abstract, not verified). Attempting first is not always better than studying an example first.
  - In grade-8 mathematics, an early advantage of problem solving over worked examples for some students did not last three months (Reinhard et al., 2019, not verified).
  - A press report on a 53-study meta-analysis says problem solving before instruction helped secondary and undergraduate students more than primary students, and "requires a certain amount of prior knowledge" (Elhardt, 2021, press coverage; the paper was blocked).
- No study tested click-to-reveal, step-by-step reveal, or solutions shown only after an attempt, in static material.

### 1.5. Hints on request

**Evidence: tutoring software, correlational, abstracts.**

- In a geometry tutor (38 students), "asking for help on challenging steps is associated with productive learning", and overusing help went with poorer learning. On steps where students had little prior knowledge, avoiding help and failing went with better learning than seeking help. The authors suggest "novice learners may benefit from engaging in solution attempts before they can make sense of given assistance" (Roll et al., 2014).
- Teaching students to seek help better changed their behaviour but not their learning: "feedback helped students to use on-demand help more deliberately, even after the feedback was no longer given, but not to achieve better learning outcomes" (Aleven et al., 2016).
- No source tested hint sequences in static material.

### 1.6. Readers with unknown prior knowledge

**Evidence: thin; secondary sources.**

- Expertise reversal: "instructional guidance, which may be essential for novices, may have negative consequences for more experienced learners." The proposed response is to fade worked-out steps as the learner shows understanding (Wikipedia contributors, n.d., low trust; primary papers blocked). A 2022 review reports some interactions with prior knowledge as significant and others not (Wesenberg et al., 2022).
- Letting learners choose their own content order did not change learning compared with an assigned order, while scaffolding improved recall (Herold & Seufert, 2025, not verified).
- No source tested self-check pretests, self-routing or optional worked examples that the reader chooses to skip.

### 1.7. Spaced review: facts against application

**Evidence: one author's summary of one study.**

- "Fact-based retrieval practice improved performance on a final fact test", and "Higher order retrieval improved performance on a higher order test". "A mix of questions benefitted performance on both types of tests" in Experiments 2 and 3 (Agarwal, 2019). The page does not claim that fact practice helps higher-order tests.
- Whether self-directed learners follow a spacing schedule was not found in any readable source.

### 1.8. Module structure and completion

**Evidence: thin; video and online courses only.**

- In four edX courses, "shorter videos are much more engaging", with engagement measured as watch time and attempts at problems, not learning (Guo et al., 2014, abstract).
- In a randomized trial in an online course, students given a commitment device were "40% more likely to complete the course". Reminders and distraction blocking had no detectable effect. Completion in open online courses is "often less than 10%" (Patterson, 2018).
- No source covered module length, sequencing, summaries or reference sections in text material.

## 2. What this means for a static mode

These are inferences from section 1, not findings.

- **Keep self-explanation prompts in static material.** They are the one tool tested in print with no checker. Ask for open, conceptual explanations, not multiple-choice picks. Do not place an explanation of the answer right next to a prompt.
- **Write feedback as explanations.** A solution should explain why each step is right and why common wrong answers are wrong. An answer key alone is the weakest form.
- **Keep solutions apart from problems.** Most learners try first when the solution is one click away. No evidence says which form of hiding works best.
- **Give hints sparingly and say to try first.** Hint overuse went with less learning in tutoring software. No evidence covers hint sequences in static text.
- **Make review tasks the same kind as the use.** Application questions train application, fact questions train facts, and a mix helps both.
- **Expect most readers not to finish or review.** Completion of open courses is low. Learners self-test too little, and nothing found shows that readers follow a review schedule on their own.
- **The reader's level is unknown.** Worked examples suit novices and can hinder experts, and no tested way exists for a reader to route themselves. Static material has to pick one audience level, or offer several paths without evidence for them.

## 3. Open questions

- What terms do sources use for this kind of material (self-instructional material, programmed instruction, self-paced learning)? This low-priority question was not researched.
- Does access to solutions before an attempt lower learning in static material? Papers on solution-manual use (ASEE) and the Sinha and Kapur (2021) meta-analysis were blocked.
- Do readers do prompts and self-tests in static material when nothing checks them?
- Does a self-check pretest help readers choose what to skip?

## References

Agarwal, P. K. (2019, March 27). *Chicken, eggs, and Bloom's taxonomy: Fact knowledge before higher order learning?* RetrievalPractice.org. http://www.retrievalpractice.org/strategies/2019/3/27/blooms-taxonomy

Aleven, V., Roll, I., McLaren, B. M., & Koedinger, K. R. (2016). Help helps, but only so much: Research on help seeking with intelligent tutoring systems. *International Journal of Artificial Intelligence in Education, 26*(1), 205–223. https://cris.iucc.ac.il/en/publications/help-helps-but-only-so-much-research-on-help-seeking-with-intelli/

Bisra, K., Salimi, F., Liu, Q., Nesbit, J. C., & Winne, P. H. (2018). Inducing self-explanation: A meta-analysis. *Educational Psychology Review*. https://www.gwern.net/doc/psychology/spaced-repetition/2018-bisra.pdf

Elhardt, C. (2021, September 2). *Those who fail productively are all the wiser*. Phys.org. https://phys.org/news/2021-09-productively-wiser.html

Guo, P. J., Kim, J., & Rubin, R. (2014). How video production affects student engagement: An empirical study of MOOC videos. In *Proceedings of the First ACM Conference on Learning @ Scale* (pp. 41–50). https://pg.ucsd.edu/publications/edX-MOOC-video-production-and-engagement_LAS-2014.txt

Hartmann, C., van Gog, T., & Rummel, N. (2021). Preparatory effects of problem solving versus studying examples prior to instruction. *Instructional Science, 49*, 1–21. https://research-portal.uu.nl/en/publications/preparatory-effects-of-problem-solving-versus-studying-examples-p/

Herold, A., & Seufert, T. (2025). Who regulates? Effects of scaffolding in system- and self-regulated learning. *Frontiers in Psychology, 16*. https://www.frontiersin.org/articles/10.3389/fpsyg.2025.1543024/full

Mullet, H. G., Butler, A. C., Verdin, B., von Borries, R., & Marsh, E. J. (2014). Delaying feedback promotes transfer of knowledge despite student preferences to receive feedback immediately. *Journal of Applied Research in Memory and Cognition, 3*(3), 222–229. https://scholars.duke.edu/individual/pub1051154

Patterson, R. W. (2018). Can behavioral tools improve online student outcomes? Experimental evidence from a massive open online course. *Journal of Economic Behavior and Organization, 153*, 293–321. https://www.gwern.net/doc/psychology/personality/conscientiousness/2018-patterson.pdf

Reinhard, M.-A., Weissgerber, S. C., & Wenzel, K. (2019). Performance expectancies moderate the effectiveness of more or less generative activities over time. *Frontiers in Psychology, 10*. https://www.frontiersin.org/articles/10.3389/fpsyg.2019.01623/full

Roll, I., Baker, R. S. J. d., Aleven, V., & Koedinger, K. R. (2014). On the benefits of seeking (and avoiding) help in online problem-solving environments. *Journal of the Learning Sciences, 23*(4), 537–560. https://cris.iucc.ac.il/en/publications/on-the-benefits-of-seeking-and-avoiding-help-in-online-problem-so/

Shanks, D. R., Don, H. J., Boustani, S., & Yang, C. (2023). Test-enhanced learning. In *Oxford Research Encyclopedia of Education*. Oxford University Press. https://metacog.bnu.edu.cn/pdf/articles/2023/ShanksDonBoustani2023.pdf

van der Kleij, F. M., Feskens, R. C. W., & Eggen, T. J. H. M. (2015). Effects of feedback in a computer-based learning environment on students' learning outcomes: A meta-analysis. *Review of Educational Research, 85*. https://people.acer.org/en/publications/effects-of-feedback-in-a-computer-based-learning-environment-on-s/

Wesenberg, L., Krieglstein, F., Jansen, S., Rey, G. D., Beege, M., & Schneider, S. (2022). The influence of the order and congruency of correct and erroneous worked examples on learning and (meta-)cognitive load. *Frontiers in Psychology, 13*. https://www.frontiersin.org/articles/10.3389/fpsyg.2022.1032003/full

Wikipedia contributors. (n.d.). *Expertise reversal effect*. Wikipedia. https://en.wikipedia.org/wiki/Expertise_reversal_effect

Yuen, J. S., Edgcomb, A. D., & Vahid, F. (2016). *Will students earnestly attempt learning questions if answers are viewable?* zyBooks Research Library. https://www.zybooks.com/research-items/will-students-earnestly-attempt-learning-questions-if-answers-are-viewable/
