# Tactical decision games and related decision training, for an AI agent that teaches one user

Research register · Search date: 10 November 2026

**Scope.** What evidence shows that tactical decision games (TDGs) and related scenario-based decision training improve learners' decisions, under what conditions, and whether an AI agent that teaches one user (the `teach-better` skill) should use them. Related methods include ShadowBox, decision-making exercises and scenario-based training for naturalistic decision making.

**Status.** 13 questions closed. 11 answered, 1 contested, 1 not found. Every answer rests on thin evidence. No meta-analysis of TDGs or ShadowBox exists. No study tested an LLM that runs a TDG or a ShadowBox scenario.

The only format in this family with a controlled test is ShadowBox, and it is also the format that fits a one-on-one agent best. The learner ranks options at decision points in a scenario and writes a rationale. The learner then compares both with the rankings and rationales of an expert panel. In a randomized study with Marines, expert feedback produced 28% better agreement with the experts' top choices than writing rationales without feedback (d = .63). The training ran without a facilitator (Klein & Borders, 2016). The classic TDG, a short dilemma solved under a time limit and argued in a group, has no controlled test of its effect on decisions. Its own advocates attribute much of its value to group argument and a skilled facilitator, which a one-on-one agent cannot supply.

## 1. What the formats are

| Format | Core steps | Time limit | Who gives the comparison | Group needed |
|---|---|---|---|---|
| Tactical decision game (Schmitt, 1990) | Read a dilemma, write an order or plan and a short rationale, discuss | Yes (five minutes in Schmitt's example) | Peers and a facilitator, with no "school solution" | Designed for groups of up to about a dozen |
| Decision game, six-element form (Gudmundsson, 2026) | Problem, Socratic discussion in which players "devise, describe, and defend solutions", facilitator critique, reflection | Not stated in the sources read | Facilitator | Yes |
| ShadowBox (Klein & Wright, 2016; Klein & Borders, 2016) | Scenario with decision points; rank given options, write a rationale, then see the expert panel's rankings and rationales | None described | A pre-recorded panel of subject-matter experts; experts need not be present | No |

- Schmitt (1990) stresses reasoning over the choice: "Since there is no school solution to a problem like this, the emphasis is not so much on the course you take as in the reasons behind that course."
- ShadowBox scenarios are static. "The trainee follows along a scripted scenario, rather than letting the trainee's choices alter the scenario" (Klein & Borders, 2016).
- ShadowBox scores learning as agreement between the trainee's top-ranked option and the panel's top-ranked option. The studies collected rationales but did not score them (Klein & Borders, 2016).
- Klein (2023) contrasts ShadowBox with situational judgement tests, which also score closeness to expert-keyed options. Situational judgement tests serve selection. ShadowBox uses the expert answers and the debrief "to help trainees restructure their thinking."

The terms "decision-making exercise" and generic "scenario-based decision training" appeared only in vendor pages. The research found no definition with evidence behind it.

## 2. Evidence, with how strong it is

### 2.1. Tactical decision games

**Evidence: none controlled.**

- A cohort study with 16 junior doctors found that self-rated confidence in non-technical skills rose by a mean of 0.83 on a 0–10 scale after a TDG session. The rise was not statistically significant. Participants valued the session, mostly for "observing the behaviours and thought processes of their colleagues" (Suarez & Suarez, 2019). The coordinator could not reopen this paper to check its quotes (section 5).
- A team of 30 in oil and gas drilling reported that a TDG workshop was valuable (Crichton, 2009, abstract only).
- A pilot that combined critical-thinking training with TDGs reported that it met its training objectives (van den Bosch & Helsdingen, 2003, abstract only).
- A Naval Postgraduate School thesis randomly assigned 16 students to a paper TDG or a computer simulation. Both formats could evaluate leadership and decision making, but only the simulation could evaluate situational awareness. Improvement was self-reported (Ayvaz & Fitzpatrick, 2007).
- The ShadowBox developers believe, without data, that "TDGs provide better training than ShadowBox" when run in a small group with a skilled facilitator. They have also seen TDGs run "by mediocre facilitators, with disappointing results" (Klein & Borders, 2016).

### 2.2. ShadowBox and expert-comparison feedback

**Evidence: one randomized comparison, run by the method's developers.**

- **Marines, randomized, n = 60, 3 hours on paper, no facilitated discussion.** At the fourth scenario, the expert-feedback group matched the expert panel 28% better than a group that wrote rationales without feedback (M = .59 vs .44, d = .63). The authors call the comparison group a "no feedback group" rather than a control, because "this type of reflection may have conferred some training benefits" (Klein & Borders, 2016).
- **Army officers, n = 30, 1 hour, self-paced on a tablet, no control group.** Agreement with the experts rose 21% on average. Twenty participants improved, and the other ten "got worse, averaging a 36% decrease in alignment with the expert rankings" (Klein & Borders, 2016).
- **Earlier study of 29 fire officers.** The expert-feedback group scored 18% higher than a no-feedback group on the final scenario. The study did not account for starting scores (reported in Klein & Borders, 2016).
- **Industrial operators.** A trade-press report describes a 26% gain in identifying root causes in a plant simulator. No primary report was found (Chemical Processing, 2015).
- **Transfer to the job is unknown.** "It is uncertain how response alignment with SMEs translates to performance on the job" (Klein & Borders, 2016). No study validates the agreement score against job performance.

### 2.3. Which components matter

**Evidence: thin. Only two components have comparative tests.**

- **Expert-comparison feedback** beat rationale-writing alone (section 2.2).
- **Decision-control prompts.** Incident commanders received prompts to evaluate goals, anticipated consequences, and risks and benefits once they had identified a course of action. Across three experiments, they formed explicit plans more often than commanders given standard training, who tended "to move directly from information gathering to action" (Cohen-Hatton & Honey, 2015, abstract only). The outcome is a change in the decision process, not in the quality of the decision.
- **Time pressure.** No study varied time pressure inside a decision-training exercise. In adjacent studies with novices, practising a surgical motor task under time pressure did not change learning or retention, and it raised reported stress (Molzahn et al., 2024, abstract only). A change in pressure between practice and test lowered performance in either direction (Cassell et al., 2018, abstract only). Practitioners disagree: one calls time limits "essential to the value of the TDG experience" (Ferencz et al., 1993), and another says artificial limits give "a false sense of the operational tempo of battle" (Hershey, 2011).
- **Group discussion and facilitator debrief.** Supported only by participants' perceptions (Suarez & Suarez, 2019) and by practitioner opinion (Gudmundsson, 2026). In an automated West Point TDG, "most of the actual learning occurs afterwards with the instructor-led guidance provided in after action review." The automated tutor added for self-study had no formal evaluation of learning (Jensen et al., 2013).

### 2.4. Delivery by a computer or an LLM

**Evidence: none for LLMs running TDGs or ShadowBox.**

- ShadowBox raised agreement with experts without a facilitator, on paper and on a tablet (Klein & Borders, 2016).
- In a randomized study of 21 medical students practising with LLM-simulated patients, the group that also received structured feedback generated by the LLM outperformed the group without that feedback on clinical decision making after four sessions (p = .049) (Brügge et al., 2024).
- Offering on-demand LLM feedback did not improve post-test scores on its own. Benefits appeared in 2 of 7 lessons, and only for learners who chose to use the feedback (Thomas et al., 2025).
- A conference abstract reports that faculty rated LLM feedback on neurology cases as equal to or better than expert feedback (Qian et al., 2026, abstract only).

### 2.5. Which learners and domains

**Evidence: indirect.**

- The ShadowBox studies used novices: second lieutenants and newly promoted lieutenants (Klein & Borders, 2016). No study compares novices and experienced learners.
- The Marines needed an explanation of who the experts were. Their own deployments had taught a different approach, "and it confused them to receive feedback from SMEs who were skilled at managing civilian cooperation" (Klein & Borders, 2016). Expert comparison depends on the learner accepting the experts' frame.
- Kahneman and Klein (2009) conclude that the quality of an intuitive judgement depends on "the predictability of the environment" and "the individual's opportunity to learn the regularities of that environment". They add that "subjective experience is not a reliable indicator of judgment accuracy."
- Support that helps novices can "lose their effectiveness and even have negative consequences for more proficient learners" (Kalyuga, 2009).

### 2.6. Broader syntheses

**Evidence: adjacent.**

- Simulation training in the health professions shows large pooled effects against no intervention. Of the 609 studies, 405 used a single-group pre-post design, and the analysis found "no consistent statistically significant interactions" with instructional design features (Cook et al., 2011, abstract only).
- Educational debiasing has a small effect on targeted tasks (g = 0.26). All studies were at unclear or high risk of bias, and transfer to real-world decisions is unknown (Swaryandini et al., 2025, abstract only).
- A systematic review found "insufficient evidence that bias mitigation interventions will substantially help people to make better decisions in real life conditions" (Korteling et al., 2021).

## 3. What this means for `teach-better`

These are inferences from the evidence above, not tested rules. The report does not change the skill.

1. **The gap that TDG-style practice would fill.** Section 1.1 of `teach-better` lists "make a kind of decision" as a possible GOAL. Its practice cards assume a problem with one right answer. A scenario with decision points and ranked options would give such a GOAL a practice format. The closest tested model is ShadowBox, not the classic TDG: it needs no group and no facilitator, and it is the only format with a controlled comparison.
2. **The expert comparison is the active component, and the agent cannot supply it from its own knowledge.** The tested effect came from comparing the learner with rankings and rationales from real experts. An agent that writes the "expert" rankings itself would replace the tested component with an untested one. It would also break the repository's rule against facts from training data (PRINCIPLES.md, section 1). The comparison needs a cited source of expert judgement: published guidance, case reviews, or a named expert's analysis. No study tested LLM-written expert rankings.
3. **The fit with existing rules is close.** `teach-better` section 3.4 already asks for the answer and the reasoning together. ShadowBox asks for a ranking and a rationale, then compares the rationale with the experts'. Writing the rationale alone may also help, since the developers did not count the no-feedback group as a true control.
4. **Domains need care.** Expert comparison suits domains where experts agree and the environment gives learnable cues. Where experts disagree, ShadowBox shows minority expert views instead of one answer (Klein, 2023). Where the learner's own experience conflicts with the experts' view, the Marines' case suggests explaining who the experts are and why they decide as they do.
5. **Time limits have no supporting evidence.** The research found none for or against time limits in decision training. Adding one would be a design choice.
6. **Decision-control prompts are a cheap option with some support.** Prompts to state the goal, the expected consequences, and the risks and benefits changed how incident commanders planned (abstract-level evidence).
7. **Quizzes would measure agreement, not job performance.** A decision quiz could reuse the format: rank options in a new scenario without help. It would measure agreement with the expert source. No study shows that this agreement predicts real decisions.

## 4. Where the evidence is weak or disagrees

- **Who ran the studies.** The ShadowBox developers ran or reported every controlled ShadowBox result read here.
- **What was measured.** Outcomes are agreement with an expert panel, self-reported confidence, or a change in the planning process. None measures decisions in the field.
- **Sample sizes.** The largest randomized comparison has 60 participants.
- **Time limits and model answers.** Practitioners disagree on both, and no data settle either (Ferencz et al., 1993; Hershey, 2011; Ball, 2024).
- **LLM delivery.** No study tested an LLM that runs decision scenarios with expert comparison. The adjacent LLM-feedback studies are small or show benefits only for learners who choose to use the feedback.

## 5. Method

- Research board: `.research/tactical-decision-games/` (not committed). It holds every question, claim and source, with each source marked by how it was read.
- Workers on a cheaper model researched the questions in English, German and French. The German and French searches returned no relevant non-English source.
- The coordinator checked the quotes cited above against their sources. Exception: the coordinator could not reopen the full text of Suarez and Suarez (2019), because PubMed Central returned a bot challenge. The worker read it in full. Its claims are marked unverified on the board.
- Abstract-only sources are marked "abstract only" in the text, and support only what their abstracts state.

## 6. Open questions

- **The LSBU randomized trial of ShadowBox with 83 trainee child-protection social workers (Whittaker, Moser, Harvey and Brand, 2021).** It is the only independent randomized ShadowBox trial found. Its repository failed TLS verification in this environment, and no other copy was found, so its results are not used here. It could strengthen or weaken the conclusion in section 2.2.
- **The industrial-operator ShadowBox study.** Only a trade-press report was found.
- **Time pressure in decision training.** Two leads, Belling et al. (2015) and Banks et al. (2020), remain unread.
- **LLM-written expert rankings.** No study compares rankings written by an LLM with rankings from expert panels.

## 7. Sources

Ayvaz, Ü., & Fitzpatrick, C. N., III. (2007). *Training methods and tactical decision-making simulations* [Master's thesis, Naval Postgraduate School]. Internet Archive. https://archive.org/details/trainingmethodsn109453348

Ball, G. (2024, January 30). *Tactical decision games reconsidered*. The Connecting File. https://thecxfile.substack.com/p/tactical-decision-games-reconsidered

Brügge, E., Ricchizzi, S., Arenbeck, M., Keller, M. N., Schur, L., Stummer, W., Holling, M., Lu, M. H., & Darici, D. (2024). Large language models improve clinical decision making of medical students through patient simulation and structured feedback: A randomized controlled trial. *BMC Medical Education, 24*, 1391. https://pmc.ncbi.nlm.nih.gov/articles/PMC11605890/

Cassell, V. E., Beattie, S., & Lawrence, G. (2018). Changing performance pressure between training and competition influences action planning because of a reduction in the efficiency of action execution. *Anxiety, Stress and Coping, 31*(1), 107–120. https://research.bangor.ac.uk/en/publications/changing-performance-pressure-between-training-and-competition-in/

Chemical Processing. (2015, August 19). *Military training technique improves operator performance*. https://www.chemicalprocessing.com/industrynews/2015/military-training-technique-improves-operator-performance-/

Cohen-Hatton, S. R., & Honey, R. C. (2015). Goal-oriented training affects decision-making processes in virtual and simulated fire and rescue environments. *Journal of Experimental Psychology: Applied*. https://pubmed.ncbi.nlm.nih.gov/26523338/

Cook, D. A., Hatala, R., Brydges, R., Zendejas, B., Szostek, J. H., Wang, A. T., Erwin, P. J., & Hamstra, S. J. (2011). Technology-enhanced simulation for health professions education: A systematic review and meta-analysis. *JAMA, 306*(9), 978–988. https://pubmed.ncbi.nlm.nih.gov/21900138/

Crichton, M. T. (2009). Improving team effectiveness using tactical decision games. *Safety Science, 47*(3), 330–336. https://trid.trb.org/View/884238

Ferencz, N., III, Walters, E. M., & Ettore, M. L. (1993, April 1). Tactical decision games [Letters]. *Marine Corps Gazette*. https://www.mca-marines.org/gazette/tactical-decision-games-3/

Gudmundsson, B. I. (2026, January 15). *The structure of decision games (A guidebook for Marines, 3 of 7)*. The Tactical Notebook. https://tacticalnotebook.substack.com/p/the-structure-of-decision-games

Hershey, A. H. (2011, January 1). Misleading future Marine tacticians? *Marine Corps Gazette*. https://mca-marines.org/?p=86489

Jensen, R., Presnell, B., Cobb, M. G., Kidd, D., & Lunsford, J. (2013). *Generalizing automated assessment of small unit tactical decision making* (Paper No. 13272). Interservice/Industry Training, Simulation, and Education Conference. https://xcdacademy.s3.amazonaws.com/iitsec/2013/8622410U13R32287.pdf

Kahneman, D., & Klein, G. (2009). Conditions for intuitive expertise: A failure to disagree. *American Psychologist*. https://pubmed.ncbi.nlm.nih.gov/19739881/

Kalyuga, S. (2009). Managing cognitive load in adaptive ICT-based learning. *Journal of Systemics, Cybernetics and Informatics, 7*(5). https://www.iiisci.org/journal/PDV/sci/pdfs/XE225KW.pdf

Klein, G. (2023, March 17). *Situational judgement tests vs. ShadowBox: Surface similarities mask essential differences*. ShadowBox Training. https://www.shadowboxtraining.com/news/2023/03/17/situational-judgement-tests-vs-shadowbox-surface-similarities-mask-essential-differences/

Klein, G., & Borders, J. (2016). The ShadowBox approach to cognitive skills training: An empirical evaluation. *Journal of Cognitive Engineering and Decision Making*. https://doi.org/10.1177/1555343416636515 (author copy: https://www.gary-klein.com/_files/ugd/2360d8_32306473d35f4022ac49e0456830f8dc.pdf)

Klein, G., & Wright, C. (2016). Macrocognition: From theory to toolbox. *Frontiers in Psychology, 7*. https://www.frontiersin.org/articles/10.3389/fpsyg.2016.00054/full

Korteling, J. E., Gerritsma, J. Y. J., & Toet, A. (2021). Retention and transfer of cognitive bias mitigation interventions: A systematic literature study. *Frontiers in Psychology*. https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.629354/full

Molzahn, A. G., Lovett, M. K., Biffar, D., de Oliveira Almeida, G., & Hamilton, A. J. (2024). The effect of time pressure on surgical skill retention in novices: A randomized controlled trial. *Surgical Innovation, 31*(5), 541–549. https://experts.arizona.edu/en/publications/the-effect-of-time-pressure-on-surgical-skill-retention-in-novice/

Qian, C., et al. (2026). *Large language models provide appropriate and timely narrative feedback as compared to experts for neurology case-based learning* [Conference abstract]. American Academy of Neurology. https://index.mirasmart.com/AAN2026/PDFfiles/AAN2026-003711.html

Schmitt, J. F. (1990, April 1). The enemy over the bridge. *Marine Corps Gazette*. https://www.mca-marines.org/gazette/the-enemy-over-the-bridge/

Suarez, A. E., & Suarez, N. (2019). Tactical decision games: A novel teaching method for non-technical skills. *BMJ Simulation & Technology Enhanced Learning*. https://pmc.ncbi.nlm.nih.gov/articles/PMC8936680

Swaryandini, G., Graham, J., Griffith, S., Grilo, V., Ruzzante, F., Zhang, X., Yeung, S. K., Mangiarulo, M., Basarkod, G., Ng, C., Parker, P., Tangen, J., Saeri, A., Grundy, E., Slattery, P., & Noetel, M. (2025). Systematic review and meta-analysis of educational approaches to reduce cognitive biases among students. *Nature Human Behaviour*. https://doi.org/10.1038/s41562-025-02253-y

Thomas, D. R., Borchers, C., Bhushan, S., Gatz, E., Gupta, S., & Koedinger, K. R. (2025). *LLM-generated feedback supports learning if learners choose to use it*. arXiv. https://arxiv.org/abs/2506.17006

van den Bosch, K., & Helsdingen, A. S. (2003). Critical thinking in tactical decision games training. In *Proceedings Human Factors of Decision Making in Complex Systems*. TNO Repository. https://repository.tno.nl/SingleDoc?docId=8860
