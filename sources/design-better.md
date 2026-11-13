# Designing interfaces that people can use, when an AI agent builds them

Research findings · Search date: 13 November 2026

The evidence supports a `/design-better` skill, but a different one from most design guidance. Few visual design rules have controlled evidence behind them, and several popular ones were tested and not supported. The strongest findings are about the agent's own work: where generated interfaces fail, and which checks the agent can and cannot trust. Generated interfaces fail most on the parts of accessibility that automated checkers cannot judge. Automated checks, screenshot review by a model and conformance with WCAG each catch only part of what stops people. No study found tests a generated interface with users doing tasks.

**Scope.** Interfaces and pages an AI agent builds, such as web pages, app UIs and rendered reports: which design choices change measured outcomes for the people using them (task success, time, errors, reading speed, comprehension, access for disabled users), and which defects generated interfaces show. Software design and the choice of chart or diagram forms are out of scope. The goal is to decide whether to build `/design-better` and which rules it can state firmly.

**Status.** No high- or medium-priority question is open. Of 67 questions, 31 are answered, 8 are contested, 7 found nothing, 10 were merged or set out of scope, and 11 low-priority questions were not researched. Twenty-one Sonnet workers and one coordinator ran the research: 144 sources and 199 claims. Five Sonnet verifiers opened the source pages: 189 claims are verified and 10 are unverified. Of the verified ones, the coordinator set 20 after a verifier flagged them: 18 by correcting the claim to match the copied passage, and 2 where only the recorded quote differed in wording. This report does not rely on the unverified claims. About half of the sources (70 of 144) were read only as abstracts, because publishers blocked the full text. Most answers are therefore thin, and this report says where.

## How firmly the evidence supports each kind of rule

| Rule a skill could state | Support | Section |
|---|---|---|
| Check generated UI for accessibility semantics by reading the markup, not only with a checker | Several studies, all on generated UIs | 1, 3 |
| Feed checker output back and fix it | One study family, automated measures only | 2 |
| Do not treat a model's screenshot review as evidence of usability | Three preprints | 2 |
| Do not treat a clean checker run or WCAG conformance as "accessible" | Several independent studies, dated | 3 |
| Put each error message next to its field | One large study; one smaller study found no time difference | 4 |
| Do not validate a field before the user finishes typing | One practitioner test and vendor sessions | 4 |
| Keep text contrast high and prefer dark text on a light background for small text | Controlled studies; the 4.5:1 number is a calculation | 6 |
| Do not use colour as the only signal | One real-world search study; no interface study found | 6 |
| Body text size: larger helps up to a point; no single best size or typeface | Reviews and controlled studies | 5 |
| Line length: avoid very short lines; about 55 to 70 characters is preferred, longer reads faster | Two studies and one review | 5 |
| Lower visual complexity for search tasks | Two studies, speed-only tasks; depends on task and user | 7 |
| Make clickable elements look clickable; make touch targets about 9 mm or more | One practitioner experiment; two studies read as abstracts | 7 |
| Label placement, validation timing, loading indicator style, response-time thresholds | Contested or not found | 4, 8 |
| Three-click rule, shallow menus always, dyslexia typefaces, serif versus sans serif | Tested and not supported | 5, 7 |

## 1. Where generated interfaces go wrong

- The measured defects are almost all about accessibility. Layout, hierarchy and visual design defects are described only qualitatively (Sawicki et al., 2026) or as compile errors (Xiao et al., 2025). No study found gives a rate for them.
- Generated code does well on what checkers measure and badly on meaning. Two models produced more accessible code than humans on contrast and alt text, and struggled with ARIA, font size CSS, table scope and heading organisation (Suh et al., 2025). Across 300 UIs from three commercial models, 541 semantic violations were found, such as alt text that passes a check and says nothing useful (Calò et al., 2026).
- Checker counts and expert ratings can point in opposite directions. In 80 generated UIs, an accessibility-oriented prompt cut the expert-rated violation rate from 58% to 19%, while automated testing showed a slightly higher rate (17.32% against 15.93%). Alt text and page language kept failing (Gurita & Vatavu, 2025).
- Blind raters of AI-generated and human-made prototypes (92 participants) scored the AI ones positively on usability and efficiency and neutral or negative on originality (Romero et al., 2026).
- An older, often-cited figure (84% of ChatGPT-generated sites with accessibility problems) comes from GPT-3.5 and one study, read here only through an index record (Semantic Scholar, 2024).

**Challenge.** The challenge question looked for studies with human raters or user tests that contradict "weak on accessibility". It found that prompts change the rate a lot in small expert-rated samples (Gurita & Vatavu, 2025; Ahmed et al., 2025), and found no study with real users doing tasks.

**What this means for the skill (my reading):** the skill's defect list can name accessibility semantics firmly: names and roles of controls, headings, landmarks, labels, alt text that describes, page language, keyboard operation and focus. It cannot give evidence-based rates for visual design defects.

## 2. What improves generated interfaces, and what only looks like it does

- Asking for accessibility in the prompt gives no dependable gain on automated measures. In 26,100 generated form components from five models, guidance in the system prompt moved the axe pass rate from 0.95 to 0.97, and the direction differed by model. The authors conclude that prompts gave "no dependable recipe" (Ma et al., 2026). A second benchmark (150 tasks, 19 models, not peer reviewed) found that a short "Make it accessible" nudge cut mean errors from 3.22 to 2.01, and expert-level guidance gave 2.17, worse than the nudge for several models (Kreer, 2026).
- Model choice mattered more than the prompt in the first benchmark: 0.78 to 0.99 axe pass rate across models (Ma et al., 2026).
- Feeding accessibility-tool output back to the model beat zero-shot, few-shot and self-criticism prompting. ARIA landmark problems remained, and some violation types rose (Suh et al., 2025).
- Rendering the page and having a vision model critique it raised model-judged scores: appearance 3.0 to 3.9 for a whole agent system (Lu et al., 2025), and up to 17.8% higher quality over three cycles (Sansford et al., 2026). Human annotators preferred refined output over one-shot output by 14 points of win rate (Chen et al., 2025). These are preferences and model scores, not task results.
- Model judges of UI quality are weak on fine judgments. They track crowd ratings on average (Pearson about 0.70), match exact scores 35–38% of the time, and agree with the crowd about 60% of the time when choosing between two UIs (Luera et al., 2025). On 300 UI pairs whose winner was set by real A/B tests, models chose at near-chance level (Jeon et al., 2026). Trained designers also disagree with each other (Krippendorff alpha 0.248; Peng et al., 2025).

**Challenge.** No study was found that compares user task success or time for generated interfaces with and without a feedback loop. A 2026 systematic review of language models for web accessibility reports no pooled effect of prompting (Aljedaani & Mollik, 2026).

**What this means for the skill (my reading):** a render-and-review loop and a checker loop are worth doing, and the skill should say what each one shows: fewer tool-detected violations and a better-looking page. Neither shows that people can use the page. The skill should not present a screenshot self-review as a usability check.

## 3. What accessibility conformance and automated tools cover

- WCAG covers part of what stops disabled users. With 32 blind users on 16 sites, only about half of the problems they met were covered by WCAG 2.0 success criteria, and on 16.7% of sites the recommended techniques did not solve the covered problem (Power et al., 2012). With disabled users in another study, WCAG 1.0 would have caught 27% of the problems, and WCAG 2.0 added a marginal 5% (Rømen & Svanæs, 2012).
- Automated tools find a minority. Tools covered 23–50% of success criteria (Vigo et al., 2013). On a page of planted barriers, the best single tool found 37–41% and all tools together about 71% (Duran, 2017). Nine tools each found issues all the others missed (Pool, 2023). A vendor reports 57.38% by issue volume, in audits where contrast was the largest category (Deque Systems, 2021).
- Conformance itself is measured unreliably: experienced evaluators did not reach 80% agreement when auditing WCAG 2.0 (Brajnik et al., 2012).
- Conformance still helps. High WCAG 2.0 conformance gave better task time and completion for nondisabled users than low conformance (Schmutz et al., 2016), and a second study from the same group reports benefits for nondisabled and visually impaired users alike (Schmutz et al., 2017).
- W3C states that its guidance for cognitive and learning disabilities covers barriers outside normative WCAG 2.x (Seeman-Horwitz et al., 2021).
- Single practices have little controlled evidence. A skip-link table of contents halved screen reader task times in its authors' study (Ferdous et al., 2021). In an audit, three blind testers completed 55.6% of 90 job-application attempts, and unlabeled fields and buttons were among the blockers (Reuschel et al., 2023). Alt text on important images only gave better task performance than none or on all images (Zhong et al., 2020; abstract only). No controlled study was found for visible keyboard focus.

**Challenge.** No study was found in which conformance had a null or reversed effect on tasks. The limits are coverage and measurement. No user study of WCAG 2.2 was found, and none with deaf participants or participants with cognitive disabilities.

**What this means for the skill (my reading):** the skill can require the standard practices as a floor, and must not let the agent report "accessible" from a clean checker run. The honest report is which checks ran and what they cannot see: keyboard order, screen reader output, and whether names and alt text mean anything.

## 4. Forms

- Error message placement: an online study with 303 participants found messages near the erroneous field did better than messages at the top or bottom of the form (Seckler et al., 2012). An independent eye-tracking study with 32 participants found errors were noticed fastest to the right of the field, with no significant difference in completion or correction time (Inal, 2016).
- A bundle of 20 form guidelines made real company forms faster to complete, with fewer submission attempts, in an experiment with 65 participants (Bargas-Avila & Seckler, 2014). The bundle was tested together, first with 23 participants (Seckler et al., 2013), so it does not show which single guideline helps.
- Validation timing is contested. Two experiments (77 and 90 participants) found that showing errors after the whole form was completed worked best and immediate feedback worst (Bargas-Avila et al., 2007). A practitioner test with 22 users found the best inline version beat validation on submit, and the version that validated before and while typing did worse (Wroblewski, 2009). A study of Arabic smartphone forms reports immediate feedback as best (Alsalamen et al., 2024). Vendor test sessions saw users frustrated when validation fired before they finished typing (Scott, 2024).
- Label placement has no supported winner. A 312-participant eye-tracking study found left-aligned labels noticed fastest and top and in-field labels better on fixations (Tangmanee & Ruchikachorn, 2018). The paper reported to favour right alignment could not be read.
- Required fields marked with colour led to fewer errors and faster completion than asterisks, with 24 participants, in a study by the group that wrote the guidelines (Pauwels et al., 2009).

**What this means for the skill (my reading):** firm enough to state: put the message at the field, and never validate before the user has finished typing. Timing beyond that, and label position, are choices to make and state, not findings.

## 5. Typography

- Size: reading speed is at its maximum across a wide range of print sizes, about 0.2 to 2 degrees of x-height (Legge & Bigelow, 2011). On small screens, near-maximum speed needed at least about 13 characters per line, and 8 for low-vision readers (Atilgan et al., 2020).
- Line length: on screen, 100-character lines were read faster than 25-character lines, readers rated 55 characters easiest, and their ratings did not predict their performance (Dyson & Kipping, 1998). A review reports a common recommendation of no more than about 70 characters (Nanavati & Bias, 2005).
- Typeface: a review of 42 empirical studies finds serifs are not a significant legibility factor and that no single size or typeface suits everyone (Ho Sang & Petrarca, 2025). Dyslexia typefaces gave no benefit over Arial in controlled studies (Kuster et al., 2017; Wery & Diliberto, 2017).
- Line spacing did not affect reading performance in one study but changed preference (Chaparro et al., 2004). No controlled study was found for alignment or letter spacing in adults.

**Challenge (contested).** Population and script change the size finding. Two studies read only through review pages report 18-point text as best, for readers with dyslexia and for older and younger readers on a tablet. With Chinese text, older adults preferred larger size and spacing, and larger values tended to slow reading and add errors (Hou et al., 2018).

**What this means for the skill (my reading):** the skill can warn against small body text and very short lines, and can say that typeface choice between ordinary serif and sans serif faces is the user's taste. It should not give one size as correct.

## 6. Colour and contrast

- Readers with normal vision tolerate contrast loss: reading speed fell by less than half for a tenfold contrast reduction (Legge et al., 1987). Low-vision readers need more: in 16 of 19, the contrast at which reading rate halves was higher than for normal observers (Rubin & Legge, 1989).
- Dark text on a light background gave better performance than the reverse, more so at small sizes (Piepenbrock et al., 2014; Dobres et al., 2016).
- On web pages, higher-contrast colour combinations were generally more readable and did not change retention (Hall & Hanna, 2004).
- The WCAG thresholds are calculated, not measured. The 3:1 baseline comes from older display standards, and 4.5:1 multiplies it by a 1.5 contrast-sensitivity loss linked to 20/40 acuity (W3C, 2026). The one reference WCAG gives for that factor could not be found.
- People with colour vision deficiency searched much worse for red targets in a real-world search task (Kugler et al., 2015). No study of colour-only signals in interfaces was found.

**Challenge.** No independent peer-reviewed comparison of the WCAG 2 contrast ratio with the proposed APCA method against measured readability was found.

**What this means for the skill (my reading):** more contrast helps, most for low-vision readers and small text, and 4.5:1 is a convention with a reasoned basis. This supports a rule that a user's existing palette is kept and the agent reports where it falls below the convention.

## 7. Layout, complexity and navigation

- Higher visual complexity reduced search efficiency and recall in a 165-participant study. People who prefer simple sites were hurt more, and the task was speed-only (Baughan et al., 2020).
- The effect depends on task and user. On a complex task, a medium-complexity site did worst (Wang et al., 2014). The cost of complexity was larger for Japanese than for US participants (Baughan et al., 2021).
- In page mockups, many links and uneven density hurt search, uniform density helped, and alignment gave no clear gain (Parush et al., 2005). No replication on real pages was found among the citing works.
- Click count did not predict task success in 620 tasks by 44 users (Porter, 2003). A medium breadth and depth structure beat the broadest shallow one (Larson & Czerwinski, 1998), and more links per page with fewer levels gave shorter task times (Zaphiris, 2000). Low literacy predicted worse navigation of hierarchies even without text (Medhi Thies et al., 2013).
- Prominent elements can be missed. Attention to banners depended on the task: people browsing aimlessly noticed them better than people searching (Pagendarm & Schaumburg, n.d.).
- Pages with weak clickability cues took about 22% longer to view, with 25% more fixations, in a practitioner experiment (Moran, 2017). Thumb targets of 9.2 to 9.6 mm were recommended from a speed study (Parhi et al., 2006), and a dataset of about 120 million touches measured error by target size (Henze et al., 2011). Both target studies were read as abstracts.

**What this means for the skill (my reading):** rules here must be soft and tied to the task: fewer competing elements when the user has to find one thing, even density, clear signs of what can be clicked. The skill should not state rules about click counts or menu depth.

## 8. States, waiting and feedback

- Response-time thresholds disagree. The 0.1, 1 and 10 second limits are stated without an experiment on the page read (Nielsen, 1993). A 196-student experiment found performance flattening from about 4 seconds of delay and attitudes from about 8, with delay explaining 2–7% of variance (Galletta et al., 2004). Another study estimates tolerable waiting at about 2 seconds (Nah, 2004). Mobile search users tolerated more, up to a 7–10 second threshold (Arapakis et al., 2021), and tolerance differed by culture (Rose et al., 2003).
- Progress bar design changes perceived duration by about 12% (Harrison et al., 2010; 16 participants in the key test).
- Skeleton screens against spinners are contested, and no direct comparison could be read first-hand. In two crowdsourced studies, a page that shows a screenshot of the finished page while loading led to faster task completion and better speed ratings than both a spinner and a skeleton screen (Dufresne, 2026).
- Presentation of an error message matters: visual variants of one message substantially improved comprehension and resolution (Khandwala & Dong, 2019).
- No controlled study was found for empty states, confirmations or undo.

**What this means for the skill (my reading):** the evidence supports showing that something is happening and writing errors people can act on. It does not support numeric thresholds or a preferred loading pattern.

## 9. Visual appeal

- Two meta-analyses find a small positive effect of interface aesthetics on objective performance: g = 0.12 across 25 studies (Thielsch et al., 2019) and g = 0.29 across 31 studies (Schlamann et al., 2026), both with high heterogeneity.
- People judge attractive interfaces as more usable regardless of actual usability (Tractinsky et al., 2000).
- The same content was judged more credible with a better visual treatment, in a study with 20 students (Robins & Holmes, 2008). A later analysis of comments found a weaker effect of appearance on credibility than earlier reports (Kakol & Nielek, 2015).

**What this means for the skill (my reading):** appeal is worth some care and does not replace the checks above. People will rate a good-looking page as usable, so the user's approval of how a page looks is not evidence that it works.

## What the research does not cover

- No study tests an agent-built interface with users doing tasks. Every measure of generated UIs is a checker, a model judge, an expert rating or a preference vote.
- Rates of layout and visual design defects in generated UIs.
- Controlled tests of Gestalt grouping, alignment, letter spacing, empty states, confirmations and undo in interfaces.
- User studies of WCAG 2.2, and studies with deaf participants or participants with cognitive disabilities.
- Many primary papers were blocked (ACM, Springer, Elsevier, Taylor & Francis), so about half of the sources rest on abstracts. Numbers from abstracts are as the abstract states them.
- Findings on older adults are mostly preferences, not performance. One review finds older adults prefer larger fonts, up to a limit (Hou et al., 2022).

## Open questions

Eleven low-priority questions were left unresearched: touch target size for older adults; scripts without word spacing and right-to-left scripts; a size above which reading slows; same-language captions; automated coverage by issue type; later replications for model judges, checker loops, the second accessibility benchmark, progress indicators and skeleton screens; and behavioural tests of design and credibility.

Blocked sources that could change an answer: the paper reported to favour right-aligned labels (Das et al., 2008), the skeleton screen study by Mejtoft et al. (2018), the two 2007 studies of headings and skip links for blind users, and the full text of the 2026 aesthetics meta-analysis.

The research board is at `.research/design-better/` in the main checkout.

## References

Ahmed, A., Fresco, M., Forsberg, F., & Grotli, H. (2025). *From code to compliance: Assessing ChatGPT's utility in designing an accessible webpage – A case study*. arXiv. https://arxiv.org/html/2501.03572v1

Aljedaani, W., & Mollik, R. H. (2026). *Large language models for web accessibility: A systematic literature review*. arXiv (Web4All 2026). https://arxiv.org/html/2605.13873

Alsalamen, R. R., Shahin, G. O., & Al-Qawasmi, K. (2024). Error messages timing and graphical presentation for smartphones Arabic forms. In *Frontiers of human centricity in the artificial intelligence-driven society 5.0* (pp. 835–847). Springer. https://www.paluniv.edu.ps/eng/?p=140533

Arapakis, I., Park, S., & Pielot, M. (2021). *Impact of response latency on user behaviour in mobile web search*. arXiv (CHIIR 2021). https://arxiv.org/abs/2101.09086

Atilgan, N., Xiong, Y.-Z., & Legge, G. E. (2020). Reconciling print-size and display-size constraints on reading. *Proceedings of the National Academy of Sciences, 117*(48), 30276–30284. https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7720185/fullTextXML

Bargas-Avila, J. A., Oberholzer, G., Schmutz, P., de Vito, M., & Opwis, K. (2007). Usable error message presentation in the World Wide Web: Do not show errors right away. *Interacting with Computers*. https://edoc.unibas.ch/8009/

Bargas-Avila, J., & Seckler, M. (2014, July 14). *Simple is better – Making your web forms easy to use pays off*. Google Research Blog. https://research.google/blog/simple-is-better-making-your-web-forms-easy-to-use-pays-off/

Baughan, A., August, T., Yamashita, N., & Reinecke, K. (2020). Keep it simple: How visual complexity and preferences impact search efficiency on websites. *Proceedings of the 2020 ACM CHI Conference on Human Factors in Computing Systems*. https://experts.illinois.edu/en/publications/keep-it-simple-how-visual-complexity-and-preferences-impact-searc/

Baughan, A., Oliveira, N., August, T., Yamashita, N., & Reinecke, K. (2021). Do cross-cultural differences in visual attention patterns affect search efficiency on websites? *Proceedings of CHI 2021*. ACM. https://experts.illinois.edu/en/publications/do-cross-cultural-differences-in-visual-attention-patterns-affect/

Brajnik, G., Yılmaz, Y., & Harper, S. (2012). Is accessibility conformance an elusive property? A study of validity and reliability of WCAG 2.0. *ACM Transactions on Accessible Computing, 4*(2). https://avesis.ncc.metu.edu.tr/yayin/0ef09ca9-9005-4b5b-aaf9-e59e35926fc3/is-accessibility-conformance-an-elusive-property-a-study-of-validity-and-reliability-of-wcag-2-0

Calò, T., Gurita, A., & De Russis, L. (2026). Measuring the semantic accessibility gap in LLM-generated web UIs. *Extended Abstracts of the 2026 CHI Conference on Human Factors in Computing Systems*. https://tommasocalo.github.io/papers/semacces

Chaparro, B., Baker, J. R., Shaikh, A. D., Hull, S., & Brady, L. (2004). Reading online text: A comparison of four white space layouts. *Usability News, 6*. https://portfolio.erau.edu/en/publications/reading-online-text-a-comparison-of-four-white-space-layouts/

Chen, J., Zhang, Y., Zhang, Y., Shao, Y., & Yang, D. (2025). *Generative interfaces for language models*. arXiv. https://arxiv.org/html/2508.19227

Deque Systems. (2021). *The automated accessibility coverage report*. https://www.deque.com/automated-accessibility-coverage-report/

Dobres, J., Chahine, N., Reimer, B., Gould, D., Mehler, B., & Coughlin, J. F. (2016). Utilising psychophysical techniques to investigate the effects of age, typeface design, size and display polarity on glance legibility. *Ergonomics*. https://doi.org/10.1080/00140139.2015.1137637

Dufresne, T. (2026). *Using false front pages to improve the user experience of loading time on the web* [Master's thesis, University of Saskatchewan]. https://harvest.usask.ca/server/api/core/bitstreams/70835f52-2060-4167-b41f-accb8c8b34ce/content

Duran, M. (2017, February 24). *What we found when we tested tools on the world's least accessible webpage*. Accessibility in government, GOV.UK. https://accessibility.blog.gov.uk/2017/02/24/what-we-found-when-we-tested-tools-on-the-worlds-least-accessible-webpage/

Dyson, M. C., & Kipping, G. J. (1998). The effects of line length and method of movement on patterns of reading from screen. *Visible Language, 32*(2). https://journals.uc.edu/index.php/vl/article/view/5671

Ferdous, J., Uddin, S., & Ashok, V. (2021). Semantic table-of-contents for efficient web screen reading. *Proceedings of the Symposium on Applied Computing*, 1941–1949. https://pmc.ncbi.nlm.nih.gov/articles/PMC8903019

Galletta, D. F., Henry, R., McCoy, S., & Polak, P. (2004). Web site delays: How tolerant are users? *Journal of the Association for Information Systems, 5*(1). https://aisel.aisnet.org/jais/vol5/iss1/1

Gurita, A.-E., & Vatavu, R.-D. (2025). When LLM-generated code perpetuates user interface accessibility barriers, how can we break the cycle? *Proceedings of the 22nd International Web for All Conference*. https://mintviz.usv.ro/publications/2025.W4A.3.pdf

Hall, R. H., & Hanna, P. (2004). The impact of web page text-background colour combinations on readability, retention, aesthetics, and behavioural intentions. *Behaviour and Information Technology*. https://scholarsmine.mst.edu/bio_inftec_facwork/103

Harrison, C., Yeo, Z., & Hudson, S. E. (2010). *Faster progress bars: Manipulating perceived duration with visual augmentations*. CHI 2010 note, Carnegie Mellon University. https://www.chrisharrison.net/projects/progressbars2/ProgressBarsHarrison.pdf

Henze, N., Rukzio, E., & Boll, S. (2011). 100,000,000 taps: Analysis and improvement of touch performance in the large. *Proceedings of MobileHCI 2011*, 133–142. https://eprints.lancs.ac.uk/id/eprint/57576

Ho Sang, B., & Petrarca, D. (2025). Beyond (type)face value: A systematic literature review examining design factors influencing the legibility and readability of typography. *Visible Language, 59*(3). https://journals.uc.edu/index.php/vl/article/view/8855

Hou, G., Anicetus, U., & He, J. (2022). How to design font size for older adults: A systematic literature review with a mobile device. *Frontiers in Psychology, 13*, 931646. https://pmc.ncbi.nlm.nih.gov/articles/PMC9376262/

Hou, G., Dong, H., Ning, W., & Han, L. (2018). Larger Chinese text spacing and size: Effects on older users' experience. *Ageing & Society, 40*(2), 389–411. https://www.cambridge.org/core/journals/ageing-and-society/article/larger-chinese-text-spacing-and-size-effects-on-older-users-experience/C2F98C618E5630B055783C2BC999A809

Inal, Y. (2016). User-friendly locations of error messages in web forms: An eye tracking study. *Journal of Eye Movement Research, 9*(5). https://bop.unibe.ch/JEMR/article/view/2821

Jeon, J., Kim, M. S., Yoon, J. H., Shim, S., Choi, Y., Kim, H., Kim, D. H., & Yu, Y. (2026). *Do MLLMs capture how interfaces guide user behavior? A benchmark for multimodal UI/UX design understanding*. arXiv. https://arxiv.org/html/2505.05026v4

Kakol, M., & Nielek, R. (2015). What affects web credibility perception? An analysis of textual justifications. *Computer Science, 16*(3), 295–310. https://journals.agh.edu.pl/csci/article/download/1348/1279/5836

Khandwala, K., & Dong, T. (2019). The impact of cosmetic changes on the usability of error messages. *CHI 2019 Extended Abstracts*. ACM. https://research.google/pubs/the-impact-of-cosmetic-changes-on-the-usability-of-error-messages/

Kreer, C. (2026). *WebAccessBench: Digital accessibility reliability in LLM-generated web interfaces* [Whitepaper]. https://conesible.de/wab/whitepaper_webaccessbench.pdf

Kugler, G., 't Hart, B. M., Kohlbecher, S., Bartl, K., Schumann, F., Einhauser, W., & Schneider, E. (2015). Visual search in the real world: Color vision deficiency affects peripheral guidance, but leaves foveal verification largely unaffected. *Frontiers in Human Neuroscience, 9*. https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2015.00680/full

Kuster, S. M., van Weerdenburg, M., Gompel, M., & Bosman, A. M. T. (2017). Dyslexie font does not benefit reading in children with or without dyslexia. *Annals of Dyslexia, 68*(1), 25–42. https://pmc.ncbi.nlm.nih.gov/articles/PMC5934461

Larson, K., & Czerwinski, M. (1998). Web page design: Implications of memory, structure and scent for information retrieval. *CHI '98 Human Factors in Computing Systems*. ACM. https://www.microsoft.com/en-us/research/publication/web-page-design-implications-memory-structure-scent-information-retrieval/

Legge, G. E., & Bigelow, C. A. (2011). Does print size matter for reading? A review of findings from vision science and typography. *Journal of Vision, 11*(5), 8. https://doi.org/10.1167/11.5.8

Legge, G. E., Rubin, G. S., & Luebker, A. (1987). Psychophysics of reading. V. The role of contrast in normal vision. *Vision Research*. https://doi.org/10.1016/0042-6989(87)90028-9

Lu, Z., Ren, H., Yang, Y., Wang, K., Zong, Z., Pan, J., Zhan, M., & Li, H. (2025). *WebGen-Agent: Enhancing interactive website generation with multi-level feedback and step-level reinforcement learning*. arXiv. https://arxiv.org/abs/2509.22644

Luera, R. A., Rossi, R., Dernoncourt, F., et al. (2025). *MLLM as a UI judge: Benchmarking multimodal LLMs for predicting human perception of user interfaces*. arXiv. https://arxiv.org/html/2510.08783v1

Ma, Y., Wobbrock, J. O., Devon, J., Gustafson, A., Fairchild, M., Mankoff, J., & Potluri, V. (2026). Prompt and circumstance: Evaluating accessibility in LLM-generated HTML form components. *ASSETS '26*. ACM. https://faculty.washington.edu/wobbrock/pubs/assets-26.04.pdf

Medhi Thies, I., Lakshmanan, M., Toyama, K., & Cutrell, E. (2013). Some evidence for impact of limited education on hierarchical user interface navigation. *CHI 2013*. ACM. https://www.microsoft.com/en-us/research/?p=164235

Moran, K. (2017, September 3). *Flat UI elements attract less attention and cause uncertainty*. Nielsen Norman Group. https://www.nngroup.com/articles/flat-ui-less-attention-cause-uncertainty/

Nah, F. F.-H. (2004). A study on tolerable waiting time: How long are Web users willing to wait? *Behaviour and Information Technology, 23*(3). https://scholars.cityu.edu.hk/en/publications/a-study-on-tolerable-waiting-time-how-long-are-web-users-willing-/

Nanavati, A. A., & Bias, R. G. (2005). Optimal line length in reading — A literature review. *Visible Language, 39*(2). https://journals.uc.edu/index.php/vl/article/view/5765

Nielsen, J. (1993). *Response times: The 3 important limits*. Nielsen Norman Group. https://www.nngroup.com/articles/response-times-3-important-limits/

Pagendarm, M., & Schaumburg, H. (n.d.). Why are users banner-blind? The impact of navigation style on the perception of web banners. *Journal of Digital Information*. https://jodi-ojs-tdl.tdl.org/jodi/article/view/jodi-37/38

Parhi, P., Karlson, A., & Bederson, B. B. (2006). Target size study for one-handed thumb use on small touchscreen devices. *Proceedings of MobileHCI 2006*. ACM. https://www.microsoft.com/en-us/research/?p=155150

Parush, A., Shwarts, Y., Shtub, A., & Chandra, M. J. (2005). The impact of visual layout factors on performance in web pages: A cross-language study. *Human Factors, 47*(1), 141–157. https://pure.psu.edu/en/publications/the-impact-of-visual-layout-factors-on-performance-in-web-pages-a/

Pauwels, S. L., Hubscher, C., Leuthold, S., Bargas-Avila, J. A., & Opwis, K. (2009). Error prevention in online forms: Use color instead of asterisks to mark required-fields. *Interacting with Computers*. Record read via OpenAlex: https://api.openalex.org/works?search=Error%20prevention%20in%20online%20forms:%20Use%20color%20instead%20of%20asterisks%20to%20mark%20required-fields

Peng, Y.-H., Bigham, J. P., & Wu, J. (2025). *DesignPref: Capturing personal preferences in visual design generation*. arXiv. https://arxiv.org/html/2511.20513v1

Piepenbrock, C., Mayr, S., & Buchner, A. (2014). Positive display polarity is particularly advantageous for small character sizes: Implications for display design. *Human Factors*. https://doi.org/10.1177/0018720813515509

Pool, J. R. (2023). *Accessibility metatesting: Comparing nine testing tools*. arXiv. https://arxiv.org/abs/2304.07591

Porter, J. (2003, April 16). *Testing the three-click rule*. Center Centre. https://articles.centercentre.com/?p=17

Power, C., Freire, A. P., Petrie, H., & Swallow, D. (2012). Guidelines are only half of the story: Accessibility problems encountered by blind users on the web. *CHI 2012*. ACM. https://www.firah.org/upload/notices3/2012/2207676-2207736.pdf

Reuschel, W., McDonnall, M., & Burton, D. (2023). The accessibility and usability of online job applications for screen reader users. *Journal of Visual Impairment & Blindness, 117*(6), 479–490. https://pmc.ncbi.nlm.nih.gov/articles/PMC10961918/

Robins, D., & Holmes, J. (2008). Aesthetics and credibility in web site design. *Information Processing and Management, 44*, 386–399. https://makinggood.ac.nz/media/1276/robinsholmes_2008_aestheticsandcredibilityinwebdesign.pdf

Romero, K., Wiese, I., Balancieiri, R., Leal, G. C., & Guerino, G. (2026). *Usable but conventional: An empirical study on the UX of AI-generated interface prototypes*. arXiv. https://arxiv.org/abs/2605.15124

Rømen, D., & Svanæs, D. (2012). Validating WCAG versions 1.0 and 2.0 through usability testing with disabled users. *Universal Access in the Information Society, 11*(4), 375–385. https://researcher.itu.dk/en/publications/validating-wcag-versions-10-and-20-through-usability-testing-with/

Rose, G. M., Evaristo, R., & Straub, D. (2003). Culture and consumer responses to web download time: A four-continent study of mono and polychronism. *IEEE Transactions on Engineering Management, 50*(1), 31–44. https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/Culture-and-consumer-responses-to-web/99900546785601842

Rubin, G. S., & Legge, G. E. (1989). Psychophysics of reading. VI. The role of contrast in low vision. *Vision Research, 29*(1), 79–91. https://experts.umn.edu/en/publications/psychophysics-of-reading-vi-the-role-of-contrast-in-low-vision/

Sansford, H., Law, D. H. C., Liu, W., Tripathi, A., Agarwal, N., & van den Burg, G. J. J. (2026). *Vision-guided iterative refinement for frontend code generation*. arXiv. https://arxiv.org/abs/2604.05839

Sawicki, B., Les, T., Parzych, D., Wycisk-Ficek, A., Trebacz, P., & Zawadzki, P. (2026). *Qualitative evaluation of LLM-designed GUI*. arXiv. https://arxiv.org/abs/2601.22759

Schlamann, M., Nestler, S., & Thielsch, M. T. (2026). *Attractive things do work better: A meta-analysis on visual aesthetics and user performance: Online supplementary materials*. Zenodo. https://zenodo.org/records/18777943

Schmutz, S., Sonderegger, A., & Sauer, J. (2016). Implementing recommendations from web accessibility guidelines: Would they also provide benefits to nondisabled users. *Human Factors, 58*(4), 611–629. Abstract read via Europe PMC (PMID 27044605).

Schmutz, S., Sonderegger, A., & Sauer, J. (2017). Implementing recommendations from web accessibility guidelines: A comparative study of nondisabled users and users with visual impairments. *Human Factors, 59*(6), 956–972. https://doi.org/10.1177/0018720817708397

Scott, E. (2024, January 9). *Usability testing of inline form validation: 31% don't have it, 4% get it wrong*. Baymard Institute. https://baymard.com/blog/inline-form-validation

Seckler, M., Heinz, S., Opwis, K., Tuch, A. N., & Bargas-Avila, J. A. (2013). Empirical evaluation of 20 web form optimization guidelines. *CHI '13 Proceedings*, 1893–1898. ACM. https://research.google/pubs/empirical-evaluation-of-20-web-form-optimization-guidelines/

Seckler, M., Tuch, A. N., Opwis, K., & Bargas-Avila, J. A. (2012). User-friendly locations of error messages in web forms: Put them on the right side of the erroneous input field. *Interacting with Computers*. https://edoc.unibas.ch/21658/

Seeman-Horwitz, L., Bradley Montgomery, R., Lee, S., & Ran, R. (Eds.). (2021). *Making content usable for people with cognitive and learning disabilities*. W3C Working Group Note. https://www.w3.org/TR/coga-usable/

Semantic Scholar. (2024). *Does ChatGPT generate accessible code? Investigating accessibility challenges in LLM-generated source code* [Index record for Aljedaani, Habib, Aljohani, Eler, & Feng]. https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3677846.3677854

Suh, H., Tafreshipour, M., Malek, S., & Ahmed, I. (2025). *Human or LLM? A comparative study on accessible code generation capability*. arXiv. https://arxiv.org/html/2503.15885v1

Tangmanee, C., & Ruchikachorn, P. (2018). Online forms: An eye tracking exploration into fixation across three label alignments. *2018 International Computer Science and Engineering Conference (ICSEC)*. IEEE. https://doi.org/10.1109/icsec.2018.8712777

Thielsch, M. T., Scharfen, J., Masoudi, E., & Reuter, M. (2019). Visual aesthetics and performance: A first meta-analysis. *Mensch und Computer 2019 Tagungsband*. https://dl.gi.de/items/62d21781-de5f-4159-95f4-5410f80438df/full

Tractinsky, N., Katz, A. S., & Ikar, D. (2000). What is beautiful is usable. *Interacting with Computers, 13*(2), 127–145. https://academic.oup.com/iwc/article-abstract/13/2/127/898608

Vigo, M., Brown, J., & Conway, V. (2013). *Benchmarking web accessibility evaluation tools: Measuring the harm of sole reliance on automated tests* [Slides]. W4A 2013. https://pt.slideshare.net/markel_vigo/benchmarking-web-accessibility-evaluation-tools-measuring-the-harm-of-sole-reliance-on-automated-tests

W3C Web Accessibility Initiative. (2026). *Understanding success criterion 1.4.3: Contrast (minimum)*. https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html

Wang, Q. Z., Yang, S., Liu, M. L., Cao, Z., & Ma, Q. G. (2014). An eye-tracking study of website complexity from cognitive load perspective. *Decision Support Systems, 62*, 1–10. https://pure.eur.nl/en/publications/an-eye-tracking-study-of-website-complexity-from-cognitive-load-p/

Wery, J. J., & Diliberto, J. A. (2017). The effect of a specialized dyslexia font, OpenDyslexic, on reading rate and accuracy. *Annals of Dyslexia*. https://doi.org/10.1007/s11881-016-0127-1

Wroblewski, L. (2009, September 1). Inline validation in web forms. *A List Apart, 291*. https://alistapart.com/article/inline-validation-in-web-forms/

Xiao, J., Wang, M., Lam, M. H., Wan, Y., Liu, J., Huo, Y., & Lyu, M. R. (2025). *DesignBench: A comprehensive benchmark for MLLM-based front-end code generation*. arXiv. https://arxiv.org/html/2506.06251v1

Zaphiris, P. (2000). *Depth vs breath in the arrangement of web links*. Cyprus University of Technology repository. https://ktisis.cut.ac.cy/entities/publication/a79f4b00-40a0-412b-b126-d9066b9d3f24

Zhong, Y., Kobayashi, M., Matsubara, M., & Morishima, A. (2020). Effects of crowd-in-the-loop alt text addition on the performance of visually impaired workers in online microtasks. *The Transactions of Human Interface Society, 22*(3), 251–262. https://www.jstage.jst.go.jp/article/his/22/3/22_251/_article/-char/en
