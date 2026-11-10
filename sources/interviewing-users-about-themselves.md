# Interviewing users about themselves: how an AI agent can learn what a user needs from writing and how they review work

Research findings for the better-ai skills  
Prepared for Nicolas · Search date: 9 November 2026

**What people say helps them often differs from what does help them, and the criteria they state for judging work differ from the criteria their judgments reveal. An interview gives better evidence when it asks about concrete past cases and concrete samples than when it asks for general preferences.** In a randomized classroom study, students learned more from the format they liked less and felt they had learned less from (Deslauriers et al., 2019). People's stated judgment policies matched the policies derived from their actual ratings only to a limited degree (German et al., 2016). Two methods have support for drawing out what people do not state on their own:
- Walking through one real, challenging incident, then probing the options the person rejected (Klein et al., 1989).
- Comparing concrete work samples and justifying the comparison, which made teachers' tacit quality criteria partly explicit (Isaksson Persson & Hartell, 2021).

AI interviewers produce answers of about the same quality as human interviewers. Their main failure is that they do not follow up on surprising or unclear answers (Wuttke et al., 2024). A user profile stored in an LLM's memory can make the model more agreeable and personalize where it should not (Wang et al., 2026; Zewe, 2026). So a guide built from an interview carries a risk as well as a benefit.

**Scope.** This report covers an AI agent interviewing a user about that same user, to produce a reusable guide for (a) writing text the user understands and acts on and (b) reviewing work the way the user reviews it. It covers self-report accuracy, interview techniques, comparison-based elicitation, AI interviewers, question bias, interview length, validating the result, and the effect of stored profiles on LLMs. How to write clearly is in `sources/writing-for-human-cognition.md`. Agreement bias in agents is in `sources/sycophancy-in-ai-agents.md`. The Critical Decision Method is covered in more depth on the board `.research/cognitive-task-analysis/`.

**Status.** The research stopped at the `medium` level: no high- or medium-priority question is open. One low-priority question on terminology is open. I checked 48 of the board's 67 claims against their pages, including every claim this report relies on, except where marked *unchecked*. No checked claim failed, but five needed corrected wording, and those corrections are used below. The research board is in `.research/interviewing-users-about-themselves/`.

**Reading level of the evidence.** Read in large part: Deslauriers et al. (2019), Oostrom et al. (2016), Klein et al. (1989), Wuttke et al. (2024), Handa et al. (2024), Li et al. (2023), Shiffman (2009) and Krosnick and Presser (2009). Most other sources were read as abstracts, so only what their abstracts state is used. Many primary sources could not be read, because their sites blocked automated access (section 10). **No study tested an AI interviewing a user about their own reading or reviewing.** Every rule this report suggests is inferred from neighbouring settings: classrooms, hiring interviews, surveys, policy-capturing studies, and LLM preference elicitation.

## 1. Findings at a glance

| Finding | Evidence | Strength |
|---|---|---|
| **Felt learning can run opposite to measured learning**; students preferred the less effective format | Deslauriers et al. (2019), randomized, 149 students | One strong study, one physics course |
| **Teaching to a stated learning style has virtually no support** | Pashler et al. (2008), review | Strong review, abstract read |
| **Stated judgment criteria match revealed criteria only partly** | German et al. (2016), 49 employees; Rakow (2014) cautions that either measure can fail | One study plus one commentary, abstracts |
| **Comparing samples and justifying makes tacit quality criteria partly explicit** | Isaksson Persson & Hartell (2021) | Exploratory, abstract |
| **Recall of past behaviour is imperfect**, even for recent days | Shiffman (2009); Tkaczyk et al. (2024) | Health and phone-use behaviour only |
| **Incident walk-throughs and rejected options reveal reasons** | Klein et al. (1989) | Primary method paper, practitioner evidence |
| **Hypothetical questions are not simply worse**: they show whether the person knows what a situation demands | Oostrom et al. (2016) | One study, 101 students |
| **LLM open questions beat user-written prompts** for eliciting preferences, with less effort reported | Li et al. (2023); Handa et al. (2024) | Two preprints, recommendation tasks |
| **AI interviewers rarely follow up** on surprising answers and miss personal examples | Wuttke et al. (2024); Cuevas et al. (2023) | Small pilot; 399-person study |
| **Agree/disagree questions give lower-quality answers** than item-specific ones | Saris et al. (2010) | Split-ballot experiment, abstract |
| **Answer quality drops late in a questionnaire** | Neuert (2024); Krosnick & Presser (2009) | Two experiments plus handbook |
| **Stored user profiles increase sycophancy and irrelevant personalization** in LLMs | Wang et al. (2026), 13 LLMs; Zewe (2026), 38 users | Preprint abstract; press summary |

## 2. Self-reports about what helps

In Deslauriers et al. (2019), students were randomly assigned to active or passive physics classes. Those in active classes "scored almost half an SD (0.46) higher on the examination" but "reported more than half an SD (0.56) lower FOL" (feeling of learning). The responses showed "a consistent student preference for the passive lecture environment." The authors conclude that "students' perception of their own learning can be anticorrelated with their actual learning." They attribute this partly to the extra effort of the better format. They support that attribution with 17 follow-up interviews, not with a direct test.

Pashler et al. (2008) reviewed the case for teaching to a person's preferred learning style and "found virtually no evidence for the interaction pattern" that would justify it. Their test is narrow: they looked for a crossover between matched and mismatched instruction. They also note that many variants have not been tested.

**What this means for an interview:** a user's statement that a format "is clearer" or "works for me" is weak evidence that it helps them understand. This matches Principle 1 of `write-better`: readers rate text as clear without understanding it better. Neither study measured reading of AI-written text.

### 2.1. Can the gap be corrected during the interview?

No study tested this inside an interview. Two indirect results point in different directions:
- Deslauriers et al. (2019) gave a 20-minute talk explaining fluency and the feeling of learning, and "over 65% of students reported on a survey that their feelings about the effectiveness of active learning significantly improved." That is a self-report, with no control group.
- In an experiment with 150 students, a prompt that asked people to compare their effort and learning with each strategy did not help: "Students' learning strategy decisions, however, did not benefit from the metacognitive prompt" (Onan et al., 2022, abstract). Direct experience did shift choices.

**So explaining the gap to the user is not shown to fix their self-reports.** Evidence from what the user does is a better source than persuading them to report differently.

## 3. Stated versus revealed review criteria

In a policy-capturing study, 49 employees rated the fairness of 56 performance appraisals. Policy capturing infers a person's decision rule from a statistical model of many of their ratings. When the authors compared the employees' self-reported policies with these inferred policies, the comparisons "revealed limited levels of self-insight" (German et al., 2016, abstract). Rakow (2014) argues in a commentary that "when these policies are mismatched, limited self-insight is not necessarily implied," because either the statistical model or the self-report can fail to capture the real process.

Quality criteria can also be hard to state at all. "The tacit knowledge of recognizing quality in student work is difficult to explicate in words." Comparing pieces of work in pairs and writing a comment to justify each choice "makes the implicit ability of assessment to some extent explicit" (Isaksson Persson & Hartell, 2021, abstract). This exploratory study used comparative judgement, combined with the repertory grid technique.

Expert accounts leave things out. A workshop abstract states that "experts omit about 70% of the decisions they make when they describe how to perform a complex task" (Yates et al., 2011). The abstract gives no evidence for the figure, so treat it as an indication of size only.

**What this means for an interview:** a user's list of what they look for in a review is incomplete, and may not match how they judge. Comparing real samples, with the user saying why one is better, gives the agent criteria it can test.

## 4. Question types: incidents, recall and hypotheticals

### 4.1. The Critical Decision Method

Klein et al. (1989) interview people about "actual nonroutine incidents that required expert judgment or decisionmaking." The interview has four steps:
1. The person picks an incident "that was challenging and that, in his or her decisionmaking, might have differed from someone with less experience."
2. They give an account that proceeds "without interruption by the interviewers, except for minor points of clarification."
3. The interviewer rebuilds the account as a timeline. "Many times inconsistencies in the account could be detected and corrected on the basis of the timeline, and missing facts filled in."
4. The interviewer probes each decision point.

Two probing findings matter here. First, "the reasons for taking a particular action are most frequently illuminated through understanding choices that were not made or were rejected." Second, the probes include hypotheticals tied to the real incident: "If a key feature of the situation had been different, what difference would it have made in your decision?"

This evidence comes from practitioners who used the method, not from a controlled comparison with other interview methods.

### 4.2. Recall is imperfect

No study compared recalled specific incidents with general self-descriptions of reading or reviewing. In other domains, recall checked against real-time records falls short:
- Day by day, recalled smoking was associated only 0.29 with an electronic diary within each person, although the correlation between people was 0.77 (Shiffman, 2009, 232 heavy smokers).
- Adolescents' daily and one-off reports of phone use both "usually reported shorter screen time and lower frequency of phone-checking behavior as compared to digital trace" (Tkaczyk et al., 2024, 137 adolescents).

**So recalling a specific incident is better grounded than a general statement, but it is still not a record.** An artefact the user produced or reacted to, such as a document, a review comment, or an edit, is stronger evidence than their memory of it.

### 4.3. Hypothetical questions

In hiring research, situational interviews, which ask "what would you do", "have been found to be one of the most criterion-valid interview techniques," with mean corrected validities of 0.41 to 0.47 across meta-analyses (cited in Oostrom et al., 2016). The study's data suggest that this validity comes partly from the candidate's "ability to correctly decipher situational demands," not from an honest prediction of their own behaviour. **A hypothetical shows what a person knows a situation requires. It is weaker evidence of what they will do or prefer.** This is one study of 101 students in a simulation.

## 5. Concrete alternatives versus open questions

No source compared these two head to head for writing or review preferences. Two LLM elicitation studies give partial answers:
- Language models that asked users open questions about their preferences "elicit responses that are often more informative than user-written prompts or labels." Users reported less effort than with writing a prompt or labelling examples (Li et al., 2023). This held across content recommendation, moral reasoning and email validation, and was significant in only some of these domains. The authors note that open questions risk "being overly broad or challenging for the user to answer."
- In a news-recommendation study with about 40 users per condition, "open-ended questions far outperform pairwise questions" when the answers were evaluated by an LLM. Pairwise questions chosen by a Bayesian model of the user beat pairwise questions chosen by an LLM (Handa et al., 2024). Users said the LLM's open questions felt "as though it had its own 'agenda'," and that its pairwise questions "should have been comparing my previous choices together as well!"

**The evidence supports open questions for drawing out preferences, as long as the interviewer adapts to the answers.** It does not show that choosing between generic samples beats open questions. For review criteria, section 3 supports comparing the user's own work samples.

## 6. AI interviewers

In a small pilot (5 AI and 6 human interviews with students), the AI interviewer "does not lead to a significant decline in response quality compared to a human interviewer" (Wuttke et al., 2024). "Neither humans nor AI always acted in full accordance with the interview guidelines." Violations occurred at similar rates, about 72 per AI interview and 64 per human interview. The errors differed:
- The AI accounted for 88 percent of violations of the rule to follow up on surprising or unclear answers. It also sometimes judged respondents' answers despite instructions.
- "Human interviewers sometimes erred by guiding respondents through associations or suggestions for their answers," accounting for 75 percent of those violations.
- Participants "found the AI interview less interesting and were less likely to repeat it," possibly because of audio problems.

In a web experiment with 1,800 participants, chatbots that probed for more detail made answers "more detailed and informative," at "a slight cost to respondent experience." Live coding of answers by the chatbot showed "slightly inflated false positive errors due to respondent acquiescence bias" (Barari et al., 2025, abstract). In a 399-person study of three interview chatbots, answers scored well on established quality measures but "rarely capture participants' specific motives or personalized examples" (Cuevas et al., 2023, abstract).

One preprint found that LLM follow-up questions guided by a list of common interviewer mistakes "outperform human-authored questions" (Shen et al., 2025, abstract, requirements interviews). No study tested whether explicit follow-up rules fix the missed-follow-up failure in a self-interview.

## 7. Question wording and bias

Agree/disagree questions "had much lower quality than responses to comparable questions offering IS [item-specific] response options" (Saris et al., 2010, abstract). An item-specific question asks about the dimension itself, such as "How long should a summary be?", instead of asking whether the user agrees with a statement. Acquiescence, the tendency to agree, "is most common when a question is difficult … when respondents have become fatigued by answering many prior questions" (Krosnick & Presser, 2009).

Krosnick and Presser (2009) list textbook advice that they call "conventional wisdom," not tested effects, including: "Avoid leading or loaded questions that push respondents toward an answer" and "Ask about one thing at a time (avoid double-barreled questions)." I found no experiment on asking several questions in one turn.

## 8. Interview length

Two experiments found that "data quality is lower if the experimental question is positioned at the end rather than at the beginning of a questionnaire" (Neuert, 2024, abstract). Krosnick and Presser (2009) say some respondents "become fatigued, disinterested, or distracted as a questionnaire progresses further," and then take shortcuts. A search lead reported no position effect in a questionnaire of over 300 items (Bowling et al., 2022), but I could not read it, so the disagreement is unconfirmed. Klein et al. (1989) planned Critical Decision Method sessions "to last for about two hours," with human interviewers and experts. No source gives a length limit for a text interview with an AI.

## 9. Validating and updating the guide

### 9.1. Checking back with the user

Member checking means "reengaging with participants by sharing study data or preliminary analysis and soliciting feedback" (Schafer & Phillippi, 2025). People "may perceive their experience differently at the time of member checking than they did at initial data collection." One critic cited in that paper "has suggested that member checking may actually threaten validity." So the user agreeing with a summary of their interview shows they accept it, not that it is accurate. No source tested a guide built from an interview against the user's later real feedback.

### 9.2. What a stored profile does to an LLM

- Across 13 LLMs, "the presence of user profiles and retrieved memories consistently exacerbates biases": irrelevant personalization, preference narrowing and sycophancy, with average drops of 45.9%, 41.7% and 61.7% on the benchmark's measures (Wang et al., 2026, abstract).
- In a two-week study with 38 users, "the presence of a condensed user profile in the model's memory had the greatest impact" on agreeableness in personal advice (Zewe, 2026, press summary of the paper).
- Profiles help mainly through "personalization information rather than semantic information," above all "the historical personalized response produced or approved by users" (Wu et al., 2024, abstract).

**So a guide that describes the user in general terms can make an agent agree more and personalize where it should not. Examples of output the user produced or approved carry most of the benefit.** None of these studies tested a guide for writing or reviewing.

## 10. Where sources disagree

- **Can self-insight into judgment criteria be measured?** German et al. (2016) report limited self-insight. Rakow (2014) argues that a mismatch can come from a flawed measure on either side. Both positions support collecting real judgments rather than relying on stated criteria alone.
- **Open versus pairwise questions.** Handa et al. (2024) found open questions far better when answers were scored by an LLM. Their own method nevertheless used pairwise questions, because a model of the user can learn from them. The best format may depend on what consumes the answers.
- **Do questions late in a long questionnaire get worse answers?** Neuert (2024) found lower quality. An unread search lead reports no effect (Bowling et al., 2022).

## 11. Inferences for an interview skill

These are my inferences from the findings above. No study tested them in this setting.

1. **Ask about real cases, not general preferences.** Ask the user to point to a document that worked for them and one that did not, or to a review they gave. Let them describe it without interruption, then probe what they rejected and why (sections 4.1, 4.2).
2. **Prefer artefacts to memory.** Read the documents, review comments or edits the user names, and record what they show, because recall of behaviour is imperfect (section 4.2).
3. **Draw out review criteria through comparison.** Have the user compare two of their own or realistic samples and say why one is better (section 3).
4. **Keep each stated preference separate from the evidence for it.** In the guide, mark what the user said and what a sample or artefact showed, because stated preferences can run opposite to what helps (section 2).
5. **Follow up on surprising or vague answers.** This is the AI interviewer's documented weak point (section 6).
6. **Ask item-specific questions, one at a time.** Avoid "Do you agree that…" and avoid suggesting answers (section 7).
7. **Put the most important questions first and keep the interview short** (section 8).
8. **Write a guide that is specific and scoped.** State when each rule applies, include approved examples, and leave out general traits, because stored profiles increase sycophancy and irrelevant personalization (section 9.2).
9. **Treat the guide as provisional.** User agreement with a summary is not validation. Revise the guide when real feedback contradicts it (section 9.1).

## 12. What the research could not find

- Any study of an AI interviewing a user about their own reading or reviewing preferences, or testing a guide produced this way.
- A direct comparison of recalled incidents with general self-descriptions for the same behaviour, outside health and phone-use data.
- Experiments on asking several questions in one turn, or on double-barrelled questions.
- Evidence on testing an elicited profile against later feedback, and primary evidence that preferences are constructed during elicitation. The Slovic and Lichtenstein sources were blocked.
- Primary texts that could change sections 2–4: the metacomprehension meta-analyses by Prinz et al. (2020), Nisbett and Wilson (1977), Ericsson and Simon (1980), later Critical Decision Method descriptions (Hoffman et al., 1998; Crandall et al., 2006), and assessor-criteria studies (Bloxham; den Outer). All were blocked or unreadable.

## References

Barari, S., Angbazo, J., Wang, N., Christian, L. M., Dean, E., Slowinski, Z., & Sepulvado, B. (2025). *AI-assisted conversational interviewing: Effects on data quality and respondent experience* (arXiv:2504.13908). arXiv. https://arxiv.org/abs/2504.13908

Cuevas, A., Scurrell, J. V., Brown, E. M., Entenmann, J., & Daepp, M. I. G. (2023). *Collecting qualitative data at scale with large language models: A case study* (arXiv:2309.10187). arXiv. https://arxiv.org/abs/2309.10187

Deslauriers, L., McCarty, L. S., Miller, K., Callaghan, K., & Kestin, G. (2019). Measuring actual learning versus feeling of learning in response to being actively engaged in the classroom. *Proceedings of the National Academy of Sciences, 116*(39), 19251–19257. https://pmc.ncbi.nlm.nih.gov/articles/PMC6765278/

German, H., Fortin, M., & Read, D. (2016). Justice judgments: Individual self-insight and between- and within-person consistency. *Academy of Management Discoveries, 2*(1), 33–50. https://wrap.warwick.ac.uk/id/eprint/79212

Handa, K., Gal, Y., Pavlick, E., Goodman, N., Andreas, J., Tamkin, A., & Li, B. Z. (2024). *Bayesian preference elicitation with language models* (arXiv:2403.05534). arXiv. https://arxiv.org/html/2403.05534v1

Isaksson Persson, H., & Hartell, E. (2021). Is it possible to reveal tacit knowledge with ACJ and RGT? Unpacking teachers' assessment practices. *Techne serien, 28*(2), 181–187. https://journals.oslomet.no/techneA/article/view/4341

Klein, G. A., Calderwood, R., & MacGregor, D. (1989). Critical decision method for eliciting knowledge. *IEEE Transactions on Systems, Man, and Cybernetics, 19*(3), 462–472. https://attachments.are.na/37200202/1ee11311075b80cf18ca01ddeda4a6d0.pdf

Krosnick, J. A., & Presser, S. (2009). *Question and questionnaire design* [Draft chapter]. In J. D. Wright & P. V. Marsden (Eds.), *Handbook of survey research* (2nd ed.). Elsevier. https://benjaminhirt.myblog.arts.ac.uk/files/2024/01/2009_handbook_krosnick-1.pdf

Li, B. Z., Tamkin, A., Goodman, N., & Andreas, J. (2023). *Eliciting human preferences with language models* (arXiv:2310.11589). arXiv. https://arxiv.org/html/2310.11589v1

Neuert, C. E. (2024). The effect of question positioning on data quality in web surveys. *Sociological Methods & Research, 53*(1), 279–295. https://ideas.repec.org/a/sae/somere/v53y2024i1p279-295.html

Onan, E., Wiradhany, W., Biwer, F., Janssen, E. M., & de Bruin, A. B. H. (2022). Growing out of the experience: How subjective experiences of effort and learning influence the use of interleaved practice. *Educational Psychology Review, 34*(4), 2451–2484. https://cris.maastrichtuniversity.nl/en/publications/5640839a-ecc7-4dd4-a31c-fa5efe339b6f

Oostrom, J. K., Melchers, K. G., Ingold, P. V., & Kleinmann, M. (2016). Why do situational interviews predict performance? Is it saying how you would behave or knowing how you should behave? *Journal of Business and Psychology, 31*, 279–291. https://pmc.ncbi.nlm.nih.gov/articles/PMC4856718

Pashler, H., McDaniel, M., Rohrer, D., & Bjork, R. (2008). Learning styles: Concepts and evidence. *Psychological Science in the Public Interest, 9*(3). https://digitalcommons.usf.edu/psy_facpub/1765/

Rakow, T. (2014). Self-insight research as (double) model recovery. *Behavioral and Brain Sciences, 37*(1), 37–38. https://repository.essex.ac.uk/9329/

Saris, W., Revilla, M., Krosnick, J. A., & Shaeffer, E. M. (2010). Comparing questions with agree/disagree response options to questions with item-specific response options. *Survey Research Methods, 4*(1), 61–79. https://ojs.ub.uni-konstanz.de/srm/article/view/2682

Schafer, R., & Phillippi, J. C. (2025). Updating and advancing member-checking methods: Use of video and asynchronous technology to optimize participant engagement. *International Journal of Qualitative Methods, 24*. https://pmc.ncbi.nlm.nih.gov/articles/PMC12419494

Shen, Y., Singhal, A., & Breaux, T. (2025). *Requirements elicitation follow-up question generation* (arXiv:2507.02858). arXiv. https://arxiv.org/abs/2507.02858

Shiffman, S. (2009). How many cigarettes did you smoke? Assessing cigarette consumption by global report, Time-Line Follow-Back, and ecological momentary assessment. *Health Psychology, 28*(5), 519–526. https://pmc.ncbi.nlm.nih.gov/articles/PMC2762359

Tkaczyk, M., Tancos, M., Smahel, D., Elavsky, S., & Plhak, J. (2024). (In)accuracy and convergent validity of daily end-of-day and single-time self-reported estimations of smartphone use among adolescents. *Computers in Human Behavior, 158*. https://muni.cz/en/research/publications/2400299

Wang, Y., Wu, Y., Qian, C., Fan, Z., Ha, H., Wu, S., Liu, J., Ji, H., & Wang, G. (2026). *Evaluating the hidden costs of personalization in large language models* (arXiv:2608.28833). arXiv. https://arxiv.org/abs/2608.28833

Wu, B., Shi, Z., Rahmani, H. A., Ramineni, V., & Yilmaz, E. (2024). *Understanding the role of user profile in the personalization of large language models* (arXiv:2406.17803). arXiv. https://arxiv.org/abs/2406.17803

Wuttke, A., Aßenmacher, M., Klamm, C., Lang, M. M., Würschinger, Q., & Kreuter, F. (2024). *AI conversational interviewing: Transforming surveys with LLMs as adaptive interviewers* (arXiv:2410.01824). arXiv. https://arxiv.org/html/2410.01824v1

Yates, K. A., Feldon, D. F., & Clark, R. E. (2011, April). *Using cognitive task analysis to capture expert knowledge and skills for research and instructional design* [Workshop abstract]. Annual Meeting of the American Educational Research Association. https://digitalcommons.usu.edu/itls_facpub/454

Zewe, A. (2026, February 18). Personalization features can make LLMs more agreeable. *MIT EECS News*. https://www.eecs.mit.edu/personalization-features-can-make-llms-more-agreeable/
