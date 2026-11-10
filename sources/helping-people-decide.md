# Helping people make better decisions: what an AI agent can do

Research findings for the better-ai skills  
Prepared for Nicolas · Search date: 9 November 2026

**Giving people an AI's answer does not reliably improve their decisions, and on decision tasks it tends to make them worse than the better of the person or the AI alone. What helps is structure that keeps the person's own judgment in play.** In a meta-analysis of 106 experiments, human–AI combinations did worse on average than the better of the two alone, and the loss was in decision tasks (Vaccaro et al., 2024). Three things have better support:
- Clarifying what the person values improves how well their choice fits those values (Witteman et al., 2021; Stacey et al., 2024).
- Having people form their own judgment before they see advice makes them more accurate (Association for Psychological Science, 2015, summarizing Rader et al.).
- Designs that make people think before they accept AI output reduce overreliance, though users like those designs least (Buçinca et al., 2021).

Unconventional designs have small, early tests:
- An AI arguing the other side reduced overreliance (Ma et al., 2024).
- An assistant that only asks questions guided decisions better than advice-giving agents (Park et al., 2024).
- Two AIs debating in front of a human judge beat a single advising AI (Rahman et al., 2025).
- Showing evidence for and against without a recommendation is contested. Its proposers report gains, and an independent test found none (Le et al., 2025; Kornowicz, 2024).

**Scope.** This report covers how an AI agent can help an individual user make a decision themselves: what counts as a better decision, whether AI help improves decisions, interaction designs, debiasing, decision aids and coaching, advice-taking, deskilling, and unconventional designs. It does not repeat `sources/ethics-through-questioning.md` or `sources/ai-agents-moral-improvement.md`. Effects of agreeing with the user are in `sources/sycophancy-in-ai-agents.md`.

**Status.** The research stopped at the `medium` level: no high- or medium-priority question is open. One low-priority question is open (section 11). I checked 38 of the board's 61 claims against their pages. Two could not be found in the text read and are marked unverified; neither is used below. The research board is in `.research/decision-support/`.

**Reading level of the evidence.** Many key sources were read in large part: Vaccaro et al. (2024), Goh et al. (2024), Witteman et al. (2021), Kornowicz (2024), Buçinca et al. (2021), Ma et al. (2024), Fogliato et al. (2022), and Bailey et al. (2022). Others were read as abstracts. Three findings come only from press summaries, because the papers could not be read: advice timing (Association for Psychological Science, 2015), forecasting training (Mellers et al., 2014), and the Future You study. Most AI studies are crowd-worker lab tasks with a known right answer, which is unlike most personal decisions.

## 1. Findings at a glance

| Finding | Evidence | Strength |
|---|---|---|
| **Human + AI is worse than the better of the two on decision tasks** (g = −0.27); it helps when the human alone is stronger | Vaccaro et al. (2024), meta-analysis of 106 experiments | Strong |
| **Clarifying values helps choices fit values**; multicriteria analysis did best | Witteman et al. (2021); Stacey et al. (2024), 209 trials | Strong, health decisions only |
| **Judging before seeing advice is more accurate** than seeing advice first | Rader et al., summarized by Association for Psychological Science (2015) | One series, paper not read |
| **Thinking first reduces overreliance**, but users rate it worst | Buçinca et al. (2021), N = 199 | One study |
| **AI as devil's advocate reduced overreliance**, and raised underreliance | Ma et al. (2024), 140 participants | Small, exploratory |
| **An assistant that asks rather than answers** guided decisions better | Park et al. (2024), N = 80 | Abstract only |
| **AI debate judged by a person** beat a single AI adviser by 4–10% | Rahman et al. (2025) | Preprint, factual claims |
| **Evidence for and against, no recommendation** | Gains reported by proposers (Le et al., 2025); no gain in an independent test (Kornowicz, 2024) | **Contested** |
| **Using AI help lowered performance once it was removed** | Liu et al. (2026), N = 1,222; Wu et al. (2026) | Two preprints, puzzles and maths |
| **Debiasing works partly; transfer to real life is weak** | Ludolph and Schulz (2018) | Systematic review |
| **People judge decisions by their outcomes** even when they say they shouldn't | Aiyer et al. (2023), N = 692 | Pre-registered replication |

## 2. What counts as a better decision

- **Informed and value-congruent.** In health research, decision quality is "the extent to which patients choose and/or receive health care interventions" that fit their informed values (IPDAS Collaboration, 2024). Instruments combine a knowledge score with how well the choice matches stated goals. In one validation, the concordance part was weak: "its ability to measure concordance with patient goals is limited" (Lee et al., 2014).
- **Not the outcome.** In a pre-registered replication, "decisions which resulted in successful outcomes were rated more favorably" than identical decisions that failed (Aiyer et al., 2023). Authors propose judging a decision by "the information available to the decision-maker at the time" and measuring quality "at the time of decision making and not in terms of any subsequent change or outcome" (Kaltoft et al., 2014). This is an argument, not a tested finding.
- **Calibration, when the outcome can be scored.** In forecasting, probability training, teaming and tracking "improved both calibration and resolution" (Mellers et al., 2014). Probability training beat scenario training, which beat none (Association for Psychological Science, 2014).

## 3. Does AI help improve decisions?

- **On average, no.** Human–AI combinations "performed significantly worse than the best of humans or AI alone" (overall g = −0.23). Decision tasks lost (g = −0.27), while creation tasks showed a non-significant gain. "When the human alone outperformed the AI alone, the combined human-AI system outperformed both alone" (Vaccaro et al., 2024).
- **Single trials agree.** Physicians given GPT-4 scored no better than those with conventional resources: "an adjusted difference of 2 percentage points (95% CI, −4 to 8 percentage points; P = .60)" (Goh et al., 2024). In a bail trial, AI recommendations "do not improve the classification accuracy of a judge's decision to impose cash bail" (Ben-Michael et al., 2024).
- **Personal decisions are untested.** Most experiments have a right answer. Conlon and Schwardmann (2026) found chatbot advice "depolarizes choices on average", but did not measure whether choices improved.

## 4. Interaction designs that keep the person's judgment

| Design | Result |
|---|---|
| Think before seeing AI output (cognitive forcing) | "significantly reduced overreliance compared to the simple explainable AI approaches", but "people assigned the least favorable subjective ratings to the designs that reduced the overreliance the most". It helped people high in Need for Cognition most (Buçinca et al., 2021) |
| Record a provisional decision first | Lowered anchoring on the AI at no time cost, but made people "less likely to agree with the AI regardless of whether the advice is accurate" (Fogliato et al., 2022; 19 radiologists) |
| Form own judgment before advice | "those who came to a decision independently before getting advice were the more accurate group"; both orders beat no advice (Association for Psychological Science, 2015, summarizing Rader et al.) |
| Show AI confidence | Improved trust calibration, but "trust calibration alone is not sufficient to improve AI-assisted decision making" (Zhang et al., 2020) |
| Always-on second opinion | Cut overreliance but raised underreliance; second opinions on request avoided that in some cases (Lu et al., 2024) |

## 5. Advice-taking

- People move about a third to a half of the way toward advice: 32%, 37% and 48% for low, neutral and high perceived advice quality. "Information about the advisor(s) that is suggestive of advice quality was the only unique predictor" of how much advice is used (Bailey et al., 2022).
- Advice is taken more "for subjective and uncertain estimates" (Bailey et al., 2022).

## 6. Values clarification, decision aids and coaching

- **Decision aids** "led to large increases in knowledge, accurate risk perceptions, and an active role in decision-making", and "probably increase the congruence between informed values and care choices" (moderate certainty; Stacey et al., 2024).
- **Explicit values clarification** "decreased the frequency of values-incongruent choices". "Multicriteria decision analysis led to more values-congruent decisions than other values clarification methods." Authors conclude aids "should include an explicit values clarification method" (Witteman et al., 2021).
- **Decision coaching** improves knowledge; "the effect on other outcomes was mixed" (Ottawa Hospital Research Institute, 2024).

## 7. Debiasing

- **Most interventions work partly.** "The majority of debiasing interventions (n = 60) was at least partially successful", but the review flags weak transfer to real life and "a lack of conceptual rigor" (Ludolph & Schulz, 2018).
- **Premortem.** The prospective-hindsight experiments behind it found that imagining the event had already happened mattered less than outcome uncertainty: "outcome uncertainty strongly affected the nature of explanations for events" (Mitchell et al., 1989).
- **Checklists: mixed.** One checklist raised confidence and cut wrong co-morbid diagnoses, but "clinicians were less likely to diagnose MDD even when the criteria were met" (Cwik et al., 2016). A forcing checklist showed "no difference in error rates between groups" (O'Sullivan & Schofield, 2019; N = 76, possibly underpowered).
- **Not read:** devil's advocacy and dialectical inquiry meta-analyses, the outside view, and evidence that consider-the-opposite backfires.

## 8. Deliberation and choice

- **Deliberation is not worse than distraction.** There is "no reliable support for the claim that a momentary diversion of thought leads to better decision making" (Nieuwenstein et al., 2015).
- **Searching more alternatives** related positively to life satisfaction in one sample, while decision difficulty related to regret (Moyano-Díaz et al., 2014). The choice-overload meta-analyses could not be read.

## 9. Dependence and deskilling

- People "who request AI assistance during the AI-access phase perform worse at the task after assistance is removed", and "greater independent problem-solving effort is associated with larger gains in latent ability" (Wu et al., 2026; logic puzzles).
- Across randomized trials with 1,222 participants, "people perform significantly worse without AI and are more likely to give up" (Liu et al., 2026; maths and reading).
- No study covers decision skill over months.

## 10. Unconventional designs

| Design | Result | Caveat |
|---|---|---|
| **AI as devil's advocate** | "consistently reduces over-reliance, albeit increasing under-reliance" (Ma et al., 2024) | "Our study's main limitation is its small participant sample" |
| **Assistant that asks instead of answering** | "better able to guide users to make important decisions" than agents that answer (Park et al., 2024) | N = 80, abstract only |
| **Two AIs debate; the person judges** | "debate consistently improves human judgment accuracy and confidence calibration, outperforming consultancy by 4-10%" (Rahman et al., 2025) | Factual claims with known answers |
| **Evidence for and against, no recommendation** | Proposers: "promising results in improving human decisions" (Le et al., 2025). Independent test: no difference in accuracy; "participants engaged only superficially with the provided pro and con evidence" (Kornowicz, 2024) | Contested |
| **Conversation with a simulated future self** | 344 users; lower anxiety, more continuity with their future self (Zewe, 2024) | Press article; not decision quality; "could backfire if the simulation moves in a negative direction" |
| **Forecasting practice** | Training, teams and tracking improved calibration (Mellers et al., 2014) | Size of gain not read |
| **Decision journals** | No controlled test found | Gap |

## 11. Where sources disagree

- **Evaluative AI.** Its proposers report gains and an independent pre-registered test found none. The disagreement tracks who ran the study.
- **Reducing reliance.** Every design that cut overreliance also raised underreliance or lowered agreement with correct advice, except on-request second opinions in some cases.
- **Task type.** Nearly all AI evidence comes from tasks with a known answer; values research comes from health. No study covers personal or career decisions with an AI.

## 12. Inferences for a decide-better skill

These are inferences from sections 2 to 10. No source tests them as agent instructions.

| Finding | Possible rule |
|---|---|
| Combinations lose when the AI's answer dominates | Do not lead with a recommendation; get the user's own leaning first |
| Judging before advice is more accurate | Ask for the user's provisional choice and reason before giving any view |
| Values clarification improves fit | Make the user state what matters and how much, then check options against it |
| Outcome bias | Judge the decision by what was known at the time; say so when the user judges past decisions by outcome |
| Devil's advocate and debate reduce overreliance | Argue the strongest case against the user's leaning, or present two opposing cases and let the user judge |
| Asking beat answering | Prefer questions to verdicts when the decision rests on the user's values |
| Forcing designs are disliked | Keep the structure short; let the user skip it, and say what they skip |
| Dependence lowers later performance | End with what the user can reuse on the next decision, not only the answer |

## 13. What the research could not find

- A test of AI support for personal or career decisions with a measure of decision quality.
- A controlled test of decision journals, or of the outside view at the individual level.
- The full texts of Rader et al., Mellers et al. (2014), Schwenk (1990) on devil's advocacy, and the choice-overload meta-analyses.
- A study of decision skill after months of AI use.
- **Open, low priority:** what non-English sources add.

## References

Aiyer, S., Kam, H. C., Ng, K. Y., Young, N. A., Shi, J., & Feldman, G. (2023). Outcomes affect evaluations of decision quality: Replication and extensions of Baron and Hershey's (1988) outcome bias Experiment 1. *International Review of Social Psychology, 36*(1), 12. https://pmc.ncbi.nlm.nih.gov/articles/PMC12372742/

Association for Psychological Science. (2014, May 19). *Predicting uncertain events on a global scale*. APS Observer. https://www.psychologicalscience.org/publications/observer/obsonline/predicting-uncertain-events-on-a-global-scale.html

Bailey, P. E., Leon, T., Ebner, N. C., Moustafa, A. A., & Weidemann, G. (2022). A meta-analysis of the weight of advice in decision-making. *Current Psychology, 42*(28), 24516–24541. https://pmc.ncbi.nlm.nih.gov/articles/PMC11661855/

Ben-Michael, E., Greiner, D. J., Huang, M., Imai, K., Jiang, Z., & Shin, S. (2024). *Does AI help humans make better decisions? A methodological framework for experimental evaluation*. arXiv. https://arxiv.org/html/2403.12108v2

Buçinca, Z., Malaya, M. B., & Gajos, K. Z. (2021). To trust or to think: Cognitive forcing functions can reduce overreliance on AI in AI-assisted decision-making. *Proceedings of the ACM on Human-Computer Interaction, 5*(CSCW1). https://ar5iv.labs.arxiv.org/html/2102.09692

Conlon, J. J., & Schwardmann, P. (2026). *AI sycophancy and decisions*. arXiv. https://arxiv.org/abs/2607.28133

Cwik, J. C., Papen, F., Lemke, J.-E., & Margraf, J. (2016). An investigation of diagnostic accuracy and confidence associated with diagnostic checklists as well as gender biases in relation to mental disorders. *Frontiers in Psychology, 7*, 1813. https://pmc.ncbi.nlm.nih.gov/articles/PMC5118628/

Fogliato, R., Chappidi, S., Lungren, M., Fitzke, M., Parkinson, M., Wilson, D., Fisher, P., Horvitz, E., Inkpen, K., & Nushi, B. (2022). Who goes first? Influences of human-AI workflow on decision making in clinical imaging. *ACM FAccT '22*. https://ar5iv.labs.arxiv.org/html/2205.09696

Goh, E., Gallo, R., Hom, J., et al. (2024). Large language model influence on diagnostic reasoning: A randomized clinical trial. *JAMA Network Open, 7*(10), e2440969. https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2825395

IPDAS Collaboration. (2024). *What are patient decision aids?* Ottawa Hospital Research Institute. https://decisionaid.ohri.ca/IPDAS/what.html

Kaltoft, M., Cunich, M., Salkeld, G., & Dowie, J. (2014). Assessing decision quality in patient-centred care requires a preference-sensitive measure. *Journal of Health Services Research & Policy, 19*(2), 110–117. https://pmc.ncbi.nlm.nih.gov/articles/PMC4025621/

Kornowicz, J. (2024). *An empirical examination of the evaluative AI framework*. arXiv. https://arxiv.org/html/2411.08583v1

Le, T., Miller, T., Sonenberg, L., Singh, R., & Soyer, H. P. (2025). *From evidence to decision: Exploring evaluative AI*. arXiv. https://arxiv.org/html/2402.01292v4

Lee, C. N., Wetschler, M. H., Chang, Y., Belkora, J. K., Moy, B., Partridge, A., & Sepucha, K. R. (2014). Measuring decision quality: Psychometric evaluation of a new instrument for breast cancer chemotherapy. *BMC Medical Informatics and Decision Making, 14*(1), 73. https://cdr.lib.unc.edu/concern/articles/fx719p65p

Liu, G., Christian, B., Dumbalska, T., Bakker, M. A., & Dubey, R. (2026). *AI assistance reduces persistence and hurts independent performance*. arXiv. https://arxiv.org/abs/2604.04721

Lu, Z., Wang, D., & Yin, M. (2024). Does more advice help? The effects of second opinions in AI-assisted decision making. *CSCW 2024*. https://ar5iv.labs.arxiv.org/html/2401.07058

Ludolph, R., & Schulz, P. J. (2018). Debiasing health-related judgments and decision making: A systematic review. *Medical Decision Making, 38*(1), 3–13. https://pure.ewha.ac.kr/en/publications/debiasing-health-related-judgments-and-decision-making-a-systemat/

Ma, S., Zhang, C., Wang, X., Ma, X., & Yin, M. (2024). *Beyond recommender: An exploratory study of the effects of different AI roles in AI-assisted decision making*. arXiv. https://ar5iv.labs.arxiv.org/html/2403.01791

Mellers, B., Ungar, L., Baron, J., Ramos, J., Gurcay, B., Fincher, K., Scott, S. E., Moore, D., Atanasov, P., Swift, S. A., Murray, T., Stone, E., & Tetlock, P. E. (2014). Psychological strategies for winning a geopolitical forecasting tournament. *Psychological Science, 25*(5), 1106–1115. https://profiles.wustl.edu/en/publications/psychological-strategies-for-winning-a-geopolitical-forecasting-t/

Mitchell, D. J., Russo, J. E., & Pennington, N. (1989). Back to the future: Temporal perspective in the explanation of events. *Journal of Behavioral Decision Making, 2*(1), 25–38. https://colab.ws/articles/10.1002%2Fbdm.3960020103

Moyano-Díaz, E., Martínez-Molina, A., & Ponce, F. P. (2014). The price of gaining: Maximization in decision-making, regret and life satisfaction. *Judgment and Decision Making, 9*(5), 500–509. https://www.cambridge.org/core/journals/judgment-and-decision-making/article/price-of-gaining-maximization-in-decisionmaking-regret-and-life-satisfaction/C3CB62F3EB5B7E8A9B428D78819A1BCB

Nieuwenstein, M. R., Wierenga, T., Morey, R. D., Wicherts, J. M., Blom, T. N., Wagenmakers, E.-J., & van Rijn, H. (2015). On making the right choice: A meta-analysis and large-scale replication attempt of the unconscious thought advantage. *Judgment and Decision Making, 10*(1), 1–17. https://www.cambridge.org/core/journals/judgment-and-decision-making/article/on-making-the-right-choice-a-metaanalysis-and-largescale-replication-attempt-of-the-unconscious-thought-advantage/A31405A97BC221C10153E9CF78A94DB6

O'Sullivan, E. D., & Schofield, S. J. (2019). A cognitive forcing tool to mitigate cognitive bias – a randomised control trial. *BMC Medical Education, 19*, 12. https://pmc.ncbi.nlm.nih.gov/articles/PMC6325867/

Ottawa Hospital Research Institute. (2024). *Decision coaching*. Patient Decision Aids. https://decisionaid.ohri.ca/coaching.html

Park, S., Subramonyam, H., & Kulkarni, C. (2024). *Thinking assistants: LLM-based conversational assistants that help users think by asking rather than answering*. arXiv. https://arxiv.org/abs/2312.06024v4

Association for Psychological Science. (2015, September 22). *Some advice on advice: Timing matters* [Summary of Rader, Soll, & Larrick, 2015, *Organizational Behavior and Human Decision Processes, 130*, 26–43]. https://www.psychologicalscience.org/news/minds-business/some-advice-on-advice-timing-matters.html

Rahman, S., Issaka, S., Suvarna, A., et al. (2025). *AI debate aids assessment of controversial claims*. arXiv. https://arxiv.org/abs/2506.02175

Stacey, D., Lewis, K. B., Smith, M., et al. (2024). *Patient decision aids to help people who are facing decisions about health treatment or screening*. Cochrane. https://www.cochrane.org/evidence/CD001431_patient-decision-aids-help-people-who-are-facing-decisions-about-health-treatment-or-screening

Vaccaro, M., Almaatouq, A., & Malone, T. (2024). *When combinations of humans and AI are useful: A systematic review and meta-analysis*. arXiv. https://arxiv.org/html/2405.06087

Witteman, H. O., Ndjaboue, R., Vaisson, G., et al. (2021). Clarifying values: An updated and expanded systematic review and meta-analysis. *Medical Decision Making, 41*(7), 801–820. https://pmc.ncbi.nlm.nih.gov/articles/PMC8482297/

Wu, S., Belem, C. G., Fu, S., Steyvers, M., & Smyth, P. (2026). *How AI assistance affects human skill development: A study of learning with logic puzzles*. arXiv. https://arxiv.org/abs/2608.23543

Zewe, A. (2024, October 1). *AI simulation gives people a glimpse of their potential future self*. MIT News. https://news.mit.edu/2024/ai-simulation-gives-people-glimpse-potential-future-self-1001

Zhang, Y., Liao, Q. V., & Bellamy, R. K. E. (2020). Effect of confidence and explanation on accuracy and trust calibration in AI-assisted decision making. *ACM FAT* '20*. https://ar5iv.labs.arxiv.org/html/2001.02114
