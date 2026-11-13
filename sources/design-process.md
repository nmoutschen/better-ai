# Which design process steps change the result, when an AI agent builds an interface

Research findings · Search date: 13 November 2026

The evidence supports some process steps and not others, and almost none of it comes from agents building interfaces. Three steps have controlled support: showing several alternatives before committing, showing a rough version instead of a polished one, and re-checking after fixes because fixes create new problems. Review against a list of heuristics, and review by a model, both produce many findings that tests with users do not confirm. Two steps that practitioners treat as basic, a brief with users and scenarios and review by someone who did not build the page, have no study showing they change the usability of the result.

**Scope.** The process by which an interface is designed and evaluated: the steps, what is shown to the user, the checks and who performs them. The question is which steps have measured effects on the result or on the problems found. Which visual and layout rules hold is covered in `design-better.md`. The goal is to decide which process sections `/design-better` can state and how firmly.

**Status.** No high- or medium-priority question is open. Of 50 questions, 28 are answered, 4 are contested, 1 found nothing, 9 were merged or set out of scope, and 8 low-priority questions were not researched. Sixteen Sonnet workers and one coordinator ran the research: 115 sources and 161 claims. Seven Sonnet verifiers opened the source pages: 160 claims are verified and 1 is unverified. The coordinator set 6 of the verified ones after a verifier flagged them, by correcting the claim to match the copied passage or, for one, by noting that only the recorded quote could not be located. This report does not rely on the unverified claim. Web search stopped for part of the first round when the session's search limit was reached, and resumed after the limit was raised. Many primary papers were blocked, so most answers are thin, and this report says where.

## How firmly the evidence supports each process step

| Step a skill could state | Support | Section |
|---|---|---|
| Write a brief with the users and their task scenarios | No study measures the usability of the result with and without one | 1 |
| Ask the user a few specific questions before building | One small interface study; costs shown in coding and search studies | 2 |
| Show two or three alternatives before committing | Controlled studies, none on a real interface project | 3 |
| Show a rough version, not a polished one | Controlled studies, one dissent | 4 |
| Learn visual preferences from examples the user reacts to | No direct comparison found; indirect support | 5 |
| Walk each scenario step and ask what can go wrong, and check a list of states | Mixed, and from requirements work; each method found cases the other missed | 6 |
| Review against a list of heuristics | Finds many problems cheaply; half or more of the findings are not confirmed by user tests | 7 |
| Report each finding with its user, task and evidence | One comparison across studies | 7 |
| Review by someone who did not build it | One small study found few differences; evaluators disagree widely with each other | 8 |
| Let a model review or act as a test user | Contested as reviewer; weak as test user | 9 |
| Re-check after each fix round and stop early | Supported: fixes create new problems and later rounds can score lower | 10 |
| Suggest a test with about five people | The model holds under its assumptions; small tests vary widely | 11 |
| Reuse components and tokens for consistency | Old controlled work on consistency; nothing on tokens given to an agent | 12 |

## 1. A brief with users and scenarios

- The standard for human-centred design names understanding the context of use and specifying user requirements as its first two activities, before design and evaluation (ISO, 2010; contents pages only).
- Studies of personas disagree, and none measures a finished interface. A five-week student experiment reports designs with better usability when personas were used; the page read does not describe the control group or the measure (Long, 2009). Evaluators with personas reported few differences from evaluators without (Friess, 2015). In a randomised experiment with 79 students, personas lowered the priority given to antisocial user stories and had no significant effect on prosocial ones (Ayoola et al., 2024). Students primed with personas generated more ideas; the outcome was ideation (Dhadphale, 2023).
- For scenarios, one quasi-experiment found they improved most decision-making practices with a small effect, on an engineering trade-off and not on an interface (Parolin et al., 2023).
- A survey of 203 practitioners and 26 interviews report that the use and effectiveness of personas vary across projects (Wang et al., 2024).

**Challenge (not found).** The challenge question looked for studies with professionals or finished products. It found no study that measures the usability of a product built with and without personas or scenarios.

**What this means for the skill (my reading):** a brief is a design choice, not a finding. Its use in the skill is practical: the scenarios are what sections 6, 7 and 10 check against.

## 2. Questions before building

- In a within-subjects study of 12 people building interfaces with a chatbot, answering guided questions before generation led to fewer iterations and revisions than free-form prompting, and took more time (Agarwal et al., 2026). Seven of eight UI experts preferred an agent that asks questions when building a web page from a sketch (Li et al., 2024).
- Questions have costs. Users of a coding agent trained to ask questions criticised excessive, generic and looping questions (Sun et al., 2025). A benchmark names interruption, latency and loss of trust as the costs, and found one model asking over-clarifying questions in 38% of the trials where it asked (Pu et al., 2026). In an 89-participant web-search study, low-quality clarifying questions disturbed users, and showing only high-quality ones gave better results with less effort (Zou et al., n.d.).
- Fewer and earlier questions carry most of the value. Limiting an agent to one to three questions cut the cost in user attention by 36–73% and kept 86–94% of the task reward (Zhang et al., 2026). In a long-horizon benchmark, how often an agent asked did not predict success, and clarification of goals lost nearly all its value after about 10% of the work (Gulati et al., 2026). Sets with more answerable questions did better (Vijayvargiya et al., 2026).

**What this means for the skill (my reading):** ask before building, and only a few questions the user can answer. All the evidence on how many comes from coding and search, so the number is a guide.

## 3. Showing alternatives before committing

- Making several designs in parallel beat refining one. In a randomised web-ad experiment with 33 participants, ads from the parallel condition had higher click-through rates and expert ratings (Dow et al., 2009). An independent lab found the same in a physical design competition with first-year students, who did not notice the benefit (Murphy et al., 2022).
- Showing several designs for feedback beat showing one. Sharing three designs improved outcome, exploration and critique quality in an 84-participant study (Dow et al., 2011). In a 48-participant test, each design was rated higher when seen alone than among three alternatives, significantly for two of the three (Tohidi et al., 2006). People are more critical when they can compare.
- Users identify problems and do not supply solutions: testing, even with several designs, did not produce constructive suggestions (Tohidi et al., 2006).

**Challenge.** No study was found in which one refined design beat several. The limits are conditions and costs:

- A second task in the same lab showed no difference (Dow et al., 2009).
- Parallel design costs more effort for the same work (Nielsen & Faber, 1996).
- Students taught the method did not use it when free to choose (Sjolund et al., 2025).
- Examples narrow what people consider. Students shown four examples explored fewer solution categories (Perttula & Liikkanen, 2006). With an AI image generator, 60 participants fixated more on an initial example and produced fewer and less varied ideas (Wadinambiarachchi et al., 2024). When a model rewrote people's ideas, quality rose and diversity and ownership fell (Maier et al., 2025).
- No evidence sets the number. The studies used three. A meta-analysis of choice overload found a mean effect of virtually zero, with large variance (Scheibehenne et al., 2010).

**What this means for the skill (my reading):** show two or three directions that differ in a way the user can see, and ask which problems each has, not how to fix them. Ask for the user's own direction first, because seeing the agent's examples first narrows it.

## 4. How finished the first version should be

- Rough and polished prototypes found largely the same usability problems in two experiments (Virzi et al., 1996). Paper and mock-up prototypes generally predicted the usability of the real product in a 48-user study (Sauer et al., 2010). Low- and high-fidelity web prototypes were equally effective at uncovering issues (Walker et al., 2002).
- One study of mobile phones found significant differences between fidelity levels (Zhang et al., 2012).
- Polish changes ratings. Users overrated the look of reduced-fidelity prototypes, and task time may be overestimated with a computer prototype (Sauer & Sonderegger, 2009).
- Sketchy representations of a concept drew more elaborate feedback and suggestions than refined ones (Ozcelik Buskermolen et al., 2015).

**Challenge.** No original report was found in which fidelity changed which problems were found.

**What this means for the skill (my reading):** a rough version is enough to find problems, and the agent should show it before the full build. Ratings of how it looks are not reliable at that stage.

## 5. Learning the user's visual preferences

- No study was found that compares examples, variants, reference sites and verbal description for a non-designer's preferences with a measured outcome.
- Designers report that they and their clients use visual references more than words (Tao et al., 2025). Letting app users pick from generated alternatives produced feedback that users and developers judged better than plain comments (Wei et al., 2026).
- For design attributes, preference studies found that pictures and words gave different results, and a review concludes that visual stimuli are needed there (Berneburg, 2007).
- Preferences are personal. Twenty professional designers agreed only weakly on which of two generated screens was better, and a model fitted to one designer predicted that designer better than a model of the majority (Peng et al., 2025). Visual appeal of websites differs by gender, education and country (Reinecke & Gajos, 2014).

**What this means for the skill (my reading):** learn the look from what the user picks and rejects, and treat the result as that user's preference, not as quality. This matches a rule the skill already needs: an existing design language wins.

## 6. Finding the cases a design leaves out

- No study was found that reports which interface states designs or generated interfaces omit, or that tests a checklist of states.
- Stepping through scenarios found more than examining a list. Experienced engineers found up to three times as many exceptions by walking scenario steps as by examining requirements (Alexander, 2000). In a randomised experiment with 48 graduate students inspecting requirements, reviewers who each searched for one class of fault found more faults than reviewers using a checklist or no method, and the checklist did no better than no method (Porter et al., 1995). The same group's summary gives about 35% more defects (Experimental Software Engineering Group, 1998). Usability inspectors who each took one perspective found about 30% more problems than heuristic evaluators (Zhang et al., 2000).
- Generated code has the same weakness. A taxonomy of bugs in generated code includes missing corner cases (Tambon et al., 2024), and models generate the interactive parts of a page less well than the static page (Xiao et al., 2024).

**Challenge (contested).** The advantage did not hold everywhere. Independent replications of that reading method in five contexts gave different results for students and practitioners (Basili et al., 1999). Two replications with undergraduates that compared reading from a perspective with a checklist conflicted on one document, and each technique found defects the other missed (Fabbri et al., 2004). A meta-analysis found no clear positive effect of reading from a perspective, which did worse than checklists (Ciolkowski, 2009; abstract only). One replication reported to find no advantage could not be read. All of these test reading procedures for requirements documents, not walks through a user's task on an interface.

**What this means for the skill (my reading):** the states step should walk each scenario step and ask what can go wrong there, and also check a short list of states, such as no data, slow response, an error and very long content. Each method found cases the other missed. The evidence is from requirements work and is mixed, so the rule gets soft wording.

## 7. Review against heuristics, and how to report findings

- Review against heuristics finds many problems for little effort. In one comparison it found more than half of all problems and the most serious ones at the lowest cost, with many low-priority reports (Jeffries et al., 1991).
- Many of its findings are not real. With 99 analysts, 65% of predicted problems were false when checked against user tests (Cockton & Woolrych, 2001). In another comparison, an inspection found about half of the problems that occurred in user testing, and only 19.8% of its findings were confirmed by the test (Nakamura et al., 2020).
- It misses what needs knowledge of the domain (Nielsen, 1995). A poster abstract reports a study in which lab testing found four to five times as many problems as heuristic evaluation (Desurvire et al., 1992).
- Walking tasks finds severe problems, and tests with users find all types (Beer et al., 1997).
- Structured reports helped in one comparison across studies: validity was 31% with a plain format and 48–63% when analysts gave a rationale for each problem, with no bogus reports (Cockton et al., 2004).

**What this means for the skill (my reading):** a review is a source of candidate problems, not of confirmed ones. Each finding should name the user, the task step and what was observed, and a finding without that should be dropped or marked unconfirmed.

## 8. Who reviews

- One study compares builders with outsiders. Four developers who built a prototype found 64 heuristic violations and UI experts found 102; the authors report relatively few differences (Levi & Conrad, 1996).
- Independent evaluators disagree widely with each other. Only 20% of 93 problems were found by all four evaluators of the same sessions (Jacobsen et al., 1998). Experienced professionals each reported about a third of the problems reported by all (Hertzum et al., 2014). Across 33 studies the median agreement between any two evaluators was 27% (Sauro, 2018). A review of eleven studies found overlap between two evaluators from about 5% to 65% (Hertzum & Jacobsen, 2003).

**Challenge.** No study was found that contradicts this, and none that shows builders miss what outsiders find. The case for independence rests on practitioner opinion.

**What this means for the skill (my reading):** a fresh-context review is a design choice here. What the evidence supports is that any single review, by anyone, finds a fraction, so a clean review is not evidence that the page works.

## 9. Models as reviewers and as test users

- As reviewers, results conflict. One model matched about a fifth of the issues human experts found and produced false positives (Guerino et al., 2025). Two models found many new defects with more false positives and redundant reports than four human inspectors (Campos et al., 2025). In another study a model found 73% and 77% of issues on two interfaces, against 57% and 63% for five human evaluators (Zhong et al., 2025a). The authors of a critique dataset say model evaluation does not yet match human evaluators (Duan et al., 2024).
- As walkthrough agents, models completed tasks more often than humans and identified fewer points of failure (Zhong et al., 2025b).
- As test users, no peer-reviewed study was found that measures overlap with human sessions. In a vendor test, AI agents succeeded on 0–25% of most tasks in one project where humans reached 62–95%, and could not flag problems beyond basic navigation (Biddle, 2025).
- Every comparison is against experts. None checks a model's findings against tests with users.

**What this means for the skill (my reading):** an agent operating the page shows whether the task can be completed, which is worth checking. It does not show where a person would struggle, and the report must say so.

## 10. Fix rounds

- Iteration raises measured usability on average: a median of 38% per iteration across four case studies, with smaller gains in later rounds (Nielsen, 1993), and 12–29% after one iteration in a comparison of four designs (Nielsen & Faber, 1996). Both are from the same author.
- Fixes create new problems. In a government site redesign, task accuracy in the third iteration was 52%, lower than in the two rounds before, and the team could not evaluate the earlier fixes (Olmsted-Hawala et al., 2011). A second round of a library site study caught a problem that the changes between rounds had created (DeStasio & Jeitner, 2024). A newsletter summary of another retest reports nine new problems from fixes and a net reduction of 37% (Bailey, 2002).

**What this means for the skill (my reading):** re-walk every scenario after each fix round, not only the one that failed, and stop after a few rounds. This matches the bounded repair loop in `/code-better`.

## 11. A test with real people

- The common model gives 85% of problems found by five users, from an average detection rate of 31% per user, and advises several small tests over one large one (Nielsen, 2000). Each distinct user group needs its own five (Nielsen, 2012).
- Small tests vary widely. Groups of five drawn from 60 participants found from 55% to nearly all of the problems, and in another study the first five users revealed 35% of the problems a larger set found (Straub, 2004, reporting two studies). The formula understates the sample needed, because problems differ in how visible they are (Schmettow, 2012; Lewis & Sauro, 2024).
- Remote tests with a moderator matched lab tests, and tests without one found fewer problems (Bastien, 2010). No study was found that compares hallway, first-click or five-second tests with moderated tests.

**What this means for the skill (my reading):** suggest that the user watches a few people from the intended audience try the scenarios. The skill can say such a test finds the common problems and should not give a percentage.

## 12. Consistency and design systems

- Interfaces with consistent wording reduced task time and errors in four experiments with 140 participants (Ozok, n.d.). One author argues consistency is an unreliable guide and that the users' work should decide (Grudin, 1989).
- No controlled study was found of giving a model a design system or tokens. Repairing generated code against a guideline knowledge base after generation improved guideline adherence and accessibility metrics (Yuan et al., 2024).

**What this means for the skill (my reading):** reusing the project's components and tokens is a design choice, in line with keeping the existing design language.

## What the research does not cover

- No study tests any of these steps with an AI agent building an interface for a user, except the two small studies of questions before building.
- No study measures a finished interface built with and without a brief, personas or scenarios.
- Which states interfaces leave out, and whether a list of states helps.
- Whether a reviewer who did not build the page finds more than the builder.
- Model findings checked against tests with users.
- Quick tests a non-specialist can run, other than remote tests.
- Blocked primary papers: one replication of the scenario-reading experiments (Fusaro et al., 1997), the original five-user studies (Virzi, 1992; Nielsen & Landauer, 1993), the 60-user study (Faulkner, 2003; its figures here come from a newsletter summary), the critique of method comparisons by Gray and Salzman (1998), and Hwang and Salvendy (2010).

## Open questions

Eight low-priority questions were left unresearched: false-alarm shares in later heuristic evaluation studies; how merging several evaluators reduces disagreement; references and text in design briefs; field reports of personas in product teams; original reports on remote tests; severity by method in one 1992 study; whether thinking of one's own idea first changes results with AI; and two further fidelity comparisons.

The research board is at `.research/design-process/` in the main checkout.

## References

Agarwal, S., Chen, H. W., Vogel, D., & Crisan, A. (2026). Thinking inside the box: Building user interfaces with question-guided inputs. *Graphics Interface 2026*. https://cs.uwaterloo.ca/~dvogel/gi2026/papers/1076b.pdf

Alexander, I. (2000). Scenario-driven search for exceptions improves capture of process knowledge. *Proceedings of the 11th International Workshop on Database and Expert Systems Applications (DEXA 2000)*. IEEE. https://scenarioplus.org.uk/papers/exceptions/exceptions.htm

Ayoola, B., Kuutila, M., Wehbe, R. R., & Ralph, P. (2024). *User personas improve social sustainability by encouraging software developers to deprioritize antisocial features*. arXiv (accepted for ICSE 2025). https://arxiv.org/abs/2412.10672

Bailey, B. (2002, April). *Iterative design*. Human Factors International. https://humanfactors.com/newsletters/iterative_design.asp

Basili, V. R., Shull, F., & Lanubile, F. (1999). Building knowledge through families of experiments. *IEEE Transactions on Software Engineering, 25*(4), 456–473. https://www.cs.umd.edu/users/basili/publications/journals/J75.pdf

Bastien, J. M. C. (2010). *Usability testing: Some current practices and research questions*. arXiv. https://arxiv.org/pdf/1009.5918

Beer, T., Anodenko, T., & Sears, A. (1997). Pair of techniques for effective interface evaluation: Cognitive walkthroughs and think-aloud evaluations. *Proceedings of the Human Factors and Ergonomics Society, 1*, 380–384. https://pure.psu.edu/en/publications/pair-of-techniques-for-effective-interface-evaluation-cognitive-w/

Berneburg, A. (2007). *Do consumers' stated preferences in choice models depend on differences in stimulus presentation: 2D versus 3D presentation?* (FEMM Working Paper No. 23). Otto-von-Guericke-University Magdeburg. https://journals.ub.ovgu.de/index.php/FEMM-WPS/article/view/111/110

Biddle, T. (2025, March 4). *AI vs. human usability testing: A comparative analysis using Loop11*. Loop11. https://www.loop11.com/ai-vs-human-usability-testing-a-comparative-analysis-using-loop11/

Campos, L. F. G., Marques, L. C., & Nakamura, W. T. (2025). *Will AI also replace inspectors? Investigating the potential of generative AIs in usability inspection*. arXiv (accepted at SBQS 2025). https://arxiv.org/abs/2510.17056

Ciolkowski, M. (2009). What do we know about perspective-based reading? An approach for quantitative aggregation in software engineering. *ESEM 2009*. IEEE Computer Society. Abstract read at https://ebse.webspace.durham.ac.uk/?p=130

Cockton, G., & Woolrych, A. (2001). Understanding inspection methods: Lessons from an assessment of heuristic evaluation. In *People and Computers XV*. Springer. https://researchportal.northumbria.ac.uk/en/publications/understanding-inspection-methods-lessons-from-an-assessment-of-he/

Cockton, G., Woolrych, A., & Hindmarch, M. (2004). Reconditioned merchandise: Extended structured report formats in usability inspection. *CHI 2004 Extended Abstracts*. ACM. https://hci.rwth-aachen.de/materials/conferences/CHI2004/2p1433.pdf

DeStasio, J. G., & Jeitner, E. (2024). Revise, redUX, re-cycle: Iterative website usability studies in an assessment cycle. *Performance Measurement and Metrics, 25*(1), 43–66. https://emerald.com/insight/content/doi/10.1108/PMM-08-2023-0025

Desurvire, H., Kondziela, J., & Atwood, M. E. (1992). What is gained and lost when using methods other than empirical testing. *Posters and Short Talks of the 1992 SIGCHI Conference on Human Factors in Computing Systems*, 125–126. ACM. https://researchdiscovery.drexel.edu/esploro/outputs/conferenceProceeding/What-is-gained-and-lost-when/991021868013504721

Dhadphale, T. (2023). *Effects of persona priming on creativity*. IDSA 2023 Education Paper, Industrial Designers Society of America. https://idsa.org/wp-content/uploads/2023/09/Effects-of-Persona-Priming-on-Creativity.pdf

Dow, S. P., Fortuna, J., Schwartz, D., Altringer, B., Schwartz, D. L., & Klemmer, S. R. (2011). Prototyping dynamics: Sharing multiple designs improves exploration, group rapport, and results. *CHI 2011*. ACM. https://d.ucsd.edu/srk/papers/2011/PrototypingDynamics-CHI2011.pdf

Dow, S. P., Glassco, A., Kass, J., Schwarz, M., & Klemmer, S. R. (2009). *The effect of parallel prototyping on design performance, learning, and self-efficacy* (Stanford Tech Report). Stanford HCI Group. https://www.cs.cmu.edu/~spdow/files/Prototyping-PSstudy-TechR09.pdf

Duan, P., Chen, C., Li, G., Hartmann, B., & Li, Y. (2024). *UICrit: Enhancing automated design evaluation with a UI critique dataset*. arXiv. https://arxiv.org/abs/2407.08850

Experimental Software Engineering Group. (1998, March 31). *Reading techniques for fault detection (2/2)*. University of Maryland. https://www.cs.umd.edu/projects/SoftEng/ESEG/topics/rtfault2.html

Fabbri, S., Maldonado, J. C., Hohn, E. N., de Oliveira, M. C. F., Martimiano, L., Mendonca, M., Shull, F., Carver, J., & Basili, V. (2004). *Data analysis of the first two PBR replications in Readers Project* (TR-225). Instituto de Ciencias Matematicas e de Computacao, Sao Carlos. https://www.cs.umd.edu/users/basili/publications/technical/T136.pdf

Friess, E. (2015). Personas in heuristic evaluation: An exploratory study. *IEEE Transactions on Professional Communication, 58*(2), 176–191. https://manuscript.isc.ac/Inventory/49/65791.htm

Grudin, J. (1989). The case against user interface consistency. *Communications of the ACM, 32*(10), 1164–1173. https://www.microsoft.com/en-us/research/wp-content/uploads/2017/01/the-case-against-user-interface-consistency.pdf

Guerino, G., Rodrigues, L., Capeleti, B., Mello, R. F., Freire, A., & Zaina, L. (2025). *Can GPT-4o evaluate usability like human experts? A comparative study on issue identification in heuristic evaluation*. arXiv. https://arxiv.org/abs/2506.16345v1

Gulati, A., Gupta, H., Lumer, E., Sen, S., & Subbiah, V. K. (2026). *Ask early, ask late, ask right: When does clarification timing matter for long-horizon agents?* arXiv. https://arxiv.org/html/2605.07937

Hertzum, M., & Jacobsen, N. E. (2003). The evaluator effect: A chilling fact about usability evaluation methods. *International Journal of Human-Computer Interaction, 15*(1), 183–204. https://forskning.ruc.dk/da/publications/the-evaluator-effect-a-chilling-fact-about-usability-evaluation-m/

Hertzum, M., Molich, R., & Jacobsen, N. E. (2014). What you get is what you see: Revisiting the evaluator effect in usability tests. *Behaviour and Information Technology, 33*(2), 144–162. https://econpapers.repec.org/RePEc:taf:tbitxx:v:33:y:2014:i:2:p:144-162

ISO. (2010). *ISO 9241-210:2010 Ergonomics of human-system interaction – Part 210: Human-centred design for interactive systems* (contents pages). https://www.din.de/de/mitwirken/normenausschuesse/naerg/veroeffentlichungen/wdc-beuth:din21:127800493/toc-1628985/download

Jacobsen, N. E., Hertzum, M., & John, B. E. (1998). The evaluator effect in usability studies: Problem detection and severity judgments. *Proceedings of the HFES 42nd Annual Meeting*, 1336–1340. https://researchprofiles.ku.dk/en/publications/the-evaluator-effect-in-usability-studies-problem-detection-and-s/

Jeffries, R., Miller, J. R., Wharton, C., & Uyeda, K. M. (1991). User interface evaluation in the real world: A comparison of four techniques. *Proceedings of CHI '91*. https://www.miramontes.com/writing/uievaluation/

Levi, M. D., & Conrad, F. G. (1996). *A heuristic evaluation of a World Wide Web prototype*. U.S. Bureau of Labor Statistics, Office of Survey Methods Research. https://www.bls.gov/osmr/research-papers/1996/html/st960160.htm

Lewis, J., & Sauro, J. (2024, October 1). *What you get with specific sample sizes in UX problem discovery studies*. MeasuringU. https://measuringu.com/specific-sample-sizes-in-problem-discovery-studies/

Li, R., Zhang, Y., & Yang, D. (2024). *Sketch2Code: Evaluating vision-language models for interactive web design prototyping*. arXiv. https://arxiv.org/html/2410.16232v1

Long, F. (2009, May 25). *Real or imaginary: The effectiveness of using personas in product design*. informationdesign.org. https://informationdesign.org/real_or_imaginary_the_effectiv

Maier, S., Schneider, M., & Feuerriegel, S. (2025). *Partnering with generative AI: Experimental evaluation of human-led and model-led interaction in human-AI co-creation*. arXiv. https://arxiv.org/abs/2510.23324

Murphy, A. R., Floresca, E. A., Fu, K. K., & Linsey, J. S. (2022). Comparing parallel and iterative prototyping strategies during engineering design. *Research in Engineering Design*. https://edrl.engr.wisc.edu/wp-content/uploads/sites/142/2022/02/Murphy2022_Article_ComparingParallelAndIterativeP.pdf

Nakamura, W. T., Marques, L. C., Ferreira, B., Barbosa, S. D. J., & Conte, T. (2020). To inspect or to test? What approach provides better results when it comes to usability and UX? *Proceedings of the 22nd International Conference on Enterprise Information Systems (ICEIS 2020), 2*. https://www.scitepress.org/Papers/2020/93679/pdf/index.html

Nielsen, J. (1993, November 1). *Iterative user interface design*. Nielsen Norman Group. https://www.nngroup.com/articles/iterative-design/

Nielsen, J. (1995, January 1). *Characteristics of usability problems found by heuristic evaluation*. Nielsen Norman Group. https://www.nngroup.com/articles/usability-problems-found-by-heuristic-evaluation/

Nielsen, J. (2000, March 18). *Why you only need to test with 5 users*. Nielsen Norman Group. https://www.nngroup.com/articles/why-you-only-need-to-test-with-5-users/

Nielsen, J. (2012, June 3). *How many test users in a usability study?* Nielsen Norman Group. https://www.nngroup.com/articles/how-many-test-users/

Nielsen, J., & Faber, J. M. (1996, February 1). *Improving system usability through parallel design*. Nielsen Norman Group. https://www.nngroup.com/articles/parallel-design/

Olmsted-Hawala, E., Romano Bergstrom, J., & Chen, J. (2011). *A high-fidelity usability evaluation of iteration 3 of the new American FactFinder web site: Increased functionality* (Study Series, Survey Methodology #2011-12). U.S. Census Bureau. https://www.census.gov/content/dam/Census/library/working-papers/2011/adrm/ssm2011-12.pdf

Ozcelik Buskermolen, D., Terken, J., Eggen, B., & van Loenen, E. (2015). Effect of visual quality and animation of concept representations on users' responses to early design concepts: A study on the adaptive patient room concept. *International Journal of Design, 9*(1), 91–106. https://ijdesign.org/index.php/IJDesign/article/download/1431/660

Ozok, A. A. (n.d.). *Guidelines for design and measurement of interface consistency on the World Wide Web* [Doctoral dissertation, Purdue University]. https://docs.lib.purdue.edu/dissertations/AAI3037621

Parolin, G., McAloone, T. C., & Pigosso, D. C. A. (2023). The effects of scenarios on decision-making quality in early design – An empirical study. *Proceedings of the Design Society, 3* (ICED23). https://cambridge.org/core/journals/proceedings-of-the-design-society/article/effects-of-scenarios-on-decisionmaking-quality-in-early-design-an-empirical-study/F71C9CD963DE775B0FF242382D5FA0ED

Peng, Y.-H., Bigham, J. P., & Wu, J. (2025). *DesignPref: Capturing personal preferences in visual design generation*. arXiv. https://arxiv.org/html/2511.20513v1

Perttula, M. K., & Liikkanen, L. A. (2006). Exposure effects in design idea generation: Unconscious conformity or a product of sampling probability? *NordDesign 2006*. https://www.designsociety.org/download-publication/24262/exposure_effects_in_design_idea_generation_unconscious_conformity_or_a_product_of_sampling_probability

Porter, A. A., Votta, L. G., Jr., & Basili, V. R. (1995). *Comparing detection methods for software requirements inspections: A replicated experiment* (CS-TR-3327.1). University of Maryland. https://drum.lib.umd.edu/items/96204769-6905-4196-b903-709ad81148ee/full

Pu, G., Lee, M. S., Sehwag, U. M., Lee, D. J., Zhu, B., Maurya, Y., Raghavendra, M., Xue, Y., & Denton, S. M. (2026). *LHAW: Controllable underspecification for long-horizon tasks*. arXiv. https://arxiv.org/html/2602.10525v1

Reinecke, K., & Gajos, K. Z. (2014). Quantifying visual preferences around the world. *CHI 2014*. ACM. https://wildlab.cs.washington.edu/Publications_files/ReineckeCHI2014.pdf

Sauer, J., Seibel, K., & Rüttinger, B. (2010). The influence of user expertise and prototype fidelity in usability tests. *Applied Ergonomics, 41*, 130–140. https://folia.unifr.ch/unifr/documents/302258

Sauer, J., & Sonderegger, A. (2009). The influence of prototype fidelity and aesthetics of design in usability tests: Effects on user behaviour, subjective evaluation and emotion. *Applied Ergonomics, 40*, 670–677. https://folia.unifr.ch/unifr/documents/302252

Sauro, J. (2018, March 28). *How large is the evaluator effect in usability testing?* MeasuringU. https://measuringu.com/evaluator-effect/

Scheibehenne, B., Greifeneder, R., & Todd, P. M. (2010). Can there ever be too many options? A meta-analytic review of choice overload. *Journal of Consumer Research, 37*(3), 409–425. https://edoc.unibas.ch/20586

Schmettow, M. (2012). Sample size in usability studies. *Communications of the ACM, 55*(4), 64–70. https://lists.cs.ucsb.edu/pipermail/ilab-users/attachments/20120410/399e3daf/attachment-0001.pdf

Sjolund, K., Brito, B., Murphy, A., & Linsey, J. (2025). Evaluation of self-directed usage of parallel and iterative prototyping strategies by first-year engineering students. *Proceedings of the Design Society, 5* (ICED25). https://doi.org/10.1017/pds.2025.10173

Straub, K. (2004, May). *Enough is enough... but five probably isn't. Evaluating the 'test-five-users' guideline*. Human Factors International. https://www.humanfactors.com/newsletters/enough_is_enough.html

Sun, W., Zhou, X., Du, W., Wang, X., Welleck, S., Neubig, G., Sap, M., & Yang, Y. (2025). *Training proactive and personalized LLM agents*. arXiv. https://arxiv.org/html/2511.02208

Tambon, F., Moradi Dakhel, A., Nikanjam, A., Khomh, F., Desmarais, M. C., & Antoniol, G. (2024). *Bugs in large language models generated code: An empirical study*. arXiv. https://arxiv.org/html/2403.08937v2

Tao, S., Liang, I., Peng, C., Wang, Z., Palani, S., & Dow, S. P. (2025). *DesignWeaver: Dimensional scaffolding for text-to-image product design*. arXiv (CHI 2025). https://arxiv.org/abs/2502.09867

Tohidi, M., Buxton, W., Baecker, R., & Sellen, A. (2006). Getting the right design and the design right: Testing many is better than one. *CHI 2006 Proceedings*. ACM. https://groups.cs.umass.edu/nmahyar/wp-content/uploads/sites/8/2019/01/reading22.pdf

Vijayvargiya, S., Viswanathan, V., & Neubig, G. (2026). *Asking what matters: Reward-driven clarification for software engineering tasks*. arXiv. https://arxiv.org/html/2604.14624

Virzi, R. A., Sokolov, J. L., & Karis, D. (1996). Usability problem identification using both low- and high-fidelity prototypes. *CHI '96 Proceedings*. ACM. https://chi1996.acm.org/proceedings/papers/Virzi/RAVtext.html

Wadinambiarachchi, S., Kelly, R. M., Pareek, S., Zhou, Q., & Velloso, E. (2024). *The effects of generative AI on design fixation and divergent thinking*. arXiv (CHI 2024). https://arxiv.org/abs/2403.11164

Walker, M., Takayama, L., & Landay, J. A. (2002). High-fidelity or low-fidelity, paper or computer? Choosing attributes when testing web prototypes. *Proceedings of the Human Factors and Ergonomics Society Annual Meeting, 46*. Abstract read via Crossref.

Wang, Y., Arora, C., Liu, X., Hoang, T., Malhotra, V., Cheng, B., & Grundy, J. (2024). *Who uses personas in requirements engineering: The practitioners' perspective*. arXiv. https://arxiv.org/abs/2403.15917

Wei, J., Pourasad, A. E., & Maalej, W. (2026). *LikeThis! Empowering app users to submit UI improvement suggestions instead of complaints*. arXiv (ICSE 2026). https://arxiv.org/abs/2603.04245

Xiao, J., Wan, Y., Huo, Y., Wang, Z., Xu, X., Wang, W., Xu, Z., Wang, Y., & Lyu, M. R. (2024). *Interaction2Code: Benchmarking MLLM-based interactive webpage code generation from interactive prototyping*. arXiv. https://arxiv.org/abs/2411.03292

Yuan, M., Chen, J., Xing, Z., Quigley, A., Luo, Y., Luo, T., Mohammadi, G., Lu, Q., & Zhu, L. (2024). *DesignRepair: Dual-stream design guideline-aware frontend repair with large language models*. arXiv. https://arxiv.org/abs/2411.01606

Zhang, T., Rau, P.-L. P., Salvendy, G., & Zhou, J. (2012). Comparing low and high-fidelity prototypes in mobile phone evaluation. *International Journal of Technology Diffusion, 3*(4), 1–19. https://doi.org/10.4018/JTD.2012100101

Zhang, X., Rezaeian, A. H., Ballesteros, M., Sun, W., Geyer, W., Chilton, L. B., Yu, Z., Benajiba, Y., & Roth, D. (2026). *Ask less, ask better: Allocating user attention in proactive LLM agents with interruption budgets*. arXiv. https://www.opentrain.ai/papers/ask-less-ask-better-allocating-user-attention-in-proactive-llm-agents-with-inter--arxiv-2610.24411/

Zhang, Z., Basili, V., & Shneiderman, B. (2000). *Perspective-based usability inspection: An empirical validation of efficacy* (CS-TR-4193). University of Maryland. https://drum.lib.umd.edu/items/4febdf7c-141b-4888-9ead-32e974881bd7/full

Zhong, R., McDonald, D. W., & Hsieh, G. (2025a). *Synthetic heuristic evaluation: A comparison between AI- and human-powered usability evaluation*. arXiv. https://arxiv.org/abs/2507.02306

Zhong, R., McDonald, D. W., & Hsieh, G. (2025b). *Synthetic cognitive walkthrough: Aligning large language model performance with human cognitive walkthrough*. arXiv. https://arxiv.org/abs/2512.03568

Zou, J., Sun, A., Long, C., Aliannejadi, M., & Kanoulas, E. (n.d.). *Asking clarifying questions: To benefit or to disturb users in web search?* Preprint. https://irlab.science.uva.nl/wp-content/papercite-data/pdf/zou2022asking.pdf
