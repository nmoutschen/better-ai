# Persona-based reviewer agents

Research findings · Search date: 13 November 2026

The evidence does not support LLM personas that stand in for neurodivergent (ND) or emotional readers, and it gives contested support for personas as a way to diversify a review panel. An assigned ND profile or emotion changes what an LLM writes, but the change matches real people poorly or was never compared with them. No study compares a simulated ND reader with real ND readers on text review or on usability problems. Studies measure stereotyped and idealized portrayals of disabled and autistic people, and the people concerned object to being simulated. For review panels, one ablation found that repeating one agent gave almost the same gain as structured personas. For feedback sent to an agent, the diagnosis carries most of the gain, and emotional pressure weakens correct positions; no study varies the emotional tone of feedback on an agent's own earlier output.

**Scope.** Three linked topics. (A) Simulated readers: an LLM agent takes the role of a reader or user with an emotional state or an ND profile, and reports where a written text or an interface fails for that reader. (B) Diverse critics: reviewer agents receive different temperaments or cognitive styles so that a panel finds more and different defects. (C) Generation method: how to generate and validate such personas. The user added a fourth topic during the run: emotional versus factual feedback given to AI agents. Review targets are written text and UX or design surfaces. These findings are input for a decision on whether and how to build persona-based reviewer agents. This report does not design them.

**Status.** 46 questions: 33 answered, 3 contested (sections 2, 3 and 5), 6 found nothing, 2 merged into other questions, and 1 low-priority question still open. 13 questions were seeds; workers raised the others from sources. The board holds 123 source entries, some for one work read at two depths. Separate verifier agents checked all 193 claims against the source pages: 177 verified and 16 unverified. Of the 16, I corrected 8 to the passage the verifier copied; the other 8 match their source but do not answer their question directly, and are used only as context. Most sources are preprints. Workers read many of them through a fetch tool's extraction, and some as abstracts only; the text marks abstract-only evidence where a finding rests on it.

## Findings at a glance

| Finding | Evidence | Evidence boundary |
|---|---|---|
| ND persona fidelity is thin and mixed | Two preprints | 26 adults, questionnaires only; 2 annotators and 15 sentences |
| No simulated ND reader was validated on text or UX review | Not found | Searches and citation chains |
| LLM portrayals of disabled and autistic people are flattened, idealized or stereotyped | Four studies | One low-vision, one social posts, two autism |
| The people concerned object to simulation | One community guideline, disability scholarship | The scholarship predates LLMs |
| Assigned emotion changes LLM output, with poor match to humans | Three full texts, one benchmark | **Contested** in the challenge question; no study of review output |
| Personas in review panels: gain is mostly repetition in the one study that tested it | Six studies | **Contested**; none reviews text or UX copy |
| Same-prompt AI reviewers repeat each other | One study, 82 papers | No persona condition |
| Rich person-level data beat demographic labels for persona fidelity | Three preprints | US or internet populations; no ND or emotional personas |
| Simulated users match real users partly | Six comparisons | No study counts shared usability problems |
| Diagnosis carries most of a critique's gain | One workshop abstract, one older study | Math and code tasks |
| Emotional pressure weakens correct positions | One study, 7 models | An LLM judged the drop |
| Tone of instructions has small or model-dependent effects | Five studies | **Contested**; none tests feedback on a prior output |

## 1. Simulated neurodivergent readers

### 1.1. Fidelity to real ND people

Two preprints compare an LLM with an ND persona to data from ND people.

| Study | Method | Result | Limit |
|---|---|---|---|
| Chiappone et al. (2026) | GPT-4o answers questionnaires as a person, from one interview with that person | Normalized error 0.25 against 0.45 for random answers; no significant difference from human scores on three of four instruments | 26 Italian adults; weak on the Attention to Detail subscale of the Autism Quotient and on social subscales; questionnaires only |
| Rizvi et al. (2026) | LLMs rewrite text under an autistic persona; compared with text by autistic people | Persona rewrites diverge from autistic people's text and often collapse into the neurotypical output | Human comparison used 2 autistic annotators and 15 sentences; small effect sizes; the authors call it exploratory |

Neither study compares the free-text behaviour of an ND persona with real ND people. The citation chains found one citing work for Chiappone et al., which does not test ND fidelity, and none for Rizvi et al., so the evidence on ND persona fidelity rests on these two papers.

### 1.2. Stereotyped and flattened portrayals

- LLMs that replace human participants misportray and flatten identity groups, including personas with impaired vision that read as an outsider's imitation (Wang et al., 2024).
- LLM-simulated posts by disabled people are idealized compared with real posts (Bombieri et al., 2026; abstract only).
- Interviews with 11 autistic participants found that LLMs steered users who disclosed autism away from stressful situations. Participants were split on whether that was affirming or infantilizing (Wohn et al., 2026; abstract only).
- In a multi-agent simulation, ChatGPT treated autistic agents as socially dependent (Park et al., 2026; abstract only, no comparison with autistic people).
- A persona generator for Down syndrome added a stereotype detector. Ten caregivers and therapists judged it, not people with Down syndrome, and one participant said everything was positive even when the content did not call for it (Wu et al., 2025).

**Challenge result.** The search for contrary evidence found no study that validates a disability or ND persona's portrayal against the people concerned, and no mitigation that removes flattening for these groups. Mitigation evidence exists only for sociodemographic groups. A diagnostic paper reports that standard fidelity metrics miss flattening: in four runs of one model, simulated agents scored full marks on a reasoning test whatever reflection level the persona assigned (Weatherhead et al., 2026; abstract only).

### 1.3. Objections from the people concerned

- A neurodivergent community guideline states that AI must not generate or ghost-write lived-experience narratives on a person's behalf without their direction (Stimpunks Foundation, n.d.).
- Disability scholarship argues that simulation and persona creation can help designers distance themselves from disabled people (Bennett & Rosner, 2019; read through a third-party copy). This work addresses human role-play and personas, not LLM substitutes.

### 1.4. Other methods for the same aim

The W3C guidance on cognitive and learning disabilities gives design patterns and advises involving people with these disabilities in research and design; it is supplemental to WCAG (Seeman-Horwitz et al., 2021). No source compares guidance-based review with persona-based review.

### 1.5. Which conditions the studies cover

Studies of ND personas address autism and ADHD most, then dyslexia. One study each addresses combined autism and ADHD, and cognitive disengagement syndrome. Workers found nothing on dyscalculia, dyspraxia, Tourette syndrome or intellectual disability beyond the Down syndrome study, and no ND persona study outside English and Italian. Tasks are questionnaires, text rewriting, advice, lecture slides and conversation, not review.

## 2. Emotional characteristics (contested)

An assigned or induced emotion changes LLM output.

- Six of the 12 models that passed checks scored higher on an anxiety inventory after anxiety-inducing prompts, and induced anxiety raised bias (Coda-Forno et al., 2023).
- Across seven models, positive or negative emotion shifted moral ratings by about 1 point on a 7-point scale in small models (Saim & Jiang, 2026).

The match with human data is poor or untested.

- A check with 4 annotators and 100 items found no matching drop for negative emotion in humans (Saim & Jiang, 2026).
- In a gambling task, induced emotion did not shift LLM decisions on average, and effects were inconsistent across models (Ho et al., 2026).
- A benchmark with more than 1,200 humans and seven LLMs found that LLMs respond appropriately to some emotional situations but fall short of human emotional behaviour (Huang et al., 2024; abstract only).

Effects shrink in larger models (Saim & Jiang, 2026). The challenge question ended contested, because the sources disagree on how human-like the responses are.

**No study tests an emotional reviewer.** Workers found no study that induces an emotion in an LLM and measures its critique or review of text or interfaces. Two adjacent studies of LLM judges exist, both read as abstracts: a strict judge role shifts scores down, and multi-agent consensus does not correct it (Song et al., 2026); Big Five personas change relevance scores and confidence (Chen et al., 2026). In agent teams on code tasks, fear and high-conscientiousness profiles raised revision activity and cost without consistent performance gains (Ding et al., 2026).

## 3. Diverse critics in a review panel (contested)

| Study | Task | Result |
|---|---|---|
| Jung and Na (2026) | Agent-based evaluation, 96 sessions | 13.2 insights per session with structured personas, 8.6 with no persona, 12.8 for one agent repeated 8 times |
| Yu et al. (2026) | App GUI testing | Nine persona agents found more distinct crash bugs than nine runs without personas; no single-persona condition |
| Chan et al. (2023) | Judging text quality | Diverse roles 60.0% accuracy against 53.8% for same-role agents, at temperature 0 |
| Wang, X., et al. (2026) | Reasoning benchmarks | Reviewer personas gave no accuracy gain; the authors credit model randomness for diversity |
| Zheng et al. (2024) | 2,410 factual questions, 162 personas, 9 open models | No improvement; per-persona effects look random |
| Muralidharan et al. (2025) | Team tasks | Demographic personas lowered flat-team accuracy (d = -0.21) |
| Ferreira et al. (2026) | Debate, small open models | Personas lowered accuracy; debate tied with or lost to sampling |

**Repetition explains most of the gain** in the one study that tested it (Jung & Na, 2026). The text that workers read does not define the repeated condition, and the study counts insights from agent diaries, not verified defects.

**What may explain the disagreement.** No study isolates the cause. The full texts show two differences. First, personas helped where the output is a set of findings or a judgment, and added nothing where one answer is correct. Second, the judging study ran at temperature 0, so same-role agents could not differ by sampling, while two other studies attribute diversity to sampling.

**Panels are less independent than they look.** Three frontier-model reviewers with one prompt overlapped on 21% of their criticisms of 82 papers; human reviewers overlapped on 3% (Kim et al., 2026). That study has no persona condition. A separate study reports that model-family diversity, not personas, brought coverage, and that interaction between agents erased it (Ann et al., 2026).

**Not found.** No study tests persona reviewers against repeated runs of one reviewer on defects in written text or interface copy. No study measures whether personas reduce the overlap of criticisms. No study compares persona diversity with model-family diversity on a review task. One ideation study found that separate per-persona prompts beat a no-persona prompt on concept diversity, while one combined prompt scored lowest; it does not test critique.

## 4. Generating and validating personas

Three methods report validation against people.

| Method | Data | Result | Limit |
|---|---|---|---|
| Park et al. (2024) | Two-hour interviews with 1,052 Americans | Interview agents reached 0.83 of people's own test-retest accuracy; 0.74 with demographics; 0.71 with a self-written paragraph | An underpowered replication test |
| Venkit et al. (2026) | 141-item protocol, 124 US participants | Correlation with each person's answers: 0.448 with no persona, 0.624 with demographics, 0.667 with full conditioning | US participants |
| Hu et al. (2025) | Persona summaries mined from social media, filtered, resampled to the Big Five distribution of over one million respondents | Alignment error fell 49.8% against LLM-generated personas, on one model | Internet population; stereotype leakage reported |

Both comparisons favour rich person-level data over demographic labels. None of the three covers ND or emotional characteristics.

**Challenge result.** Persona prompting does not always beat a baseline. A generic-reader prompt beat a ten-persona panel on headline ranking (Maiorano, 2026; abstract only). Persona variables explained under 10% of annotation variance in one study (Hu & Collier, 2024; abstract only). Works that cite Park et al. report that descriptions recover 53–67% of between-person variation; workers read three citing abstracts out of the first 40.

## 5. Validity for the two review targets

### 5.1. Written text

Workers found no study that compares feedback from LLM reader personas on prose with feedback from the human readers they represent. The closest study used a five-persona reader simulator against 30 STEM undergraduates on abstracts, news articles and tweets. The simulator got the direction of one system comparison right, but not absolute learning gains or per-topic results, and the study has no no-persona baseline (Soós et al., 2026).

Adjacent studies of reactions to short texts, all read as abstracts, show weak to moderate match: persona agents reached a correlation of 0.29 with real social media reactions and a text classifier did better (Bojic et al., 2026); agents were poor proxies for replies to news (Buitrago López et al., 2026); simulated audiences agreed with human raters in 5 of 8 scenarios (Liu et al., 2023).

### 5.2. UX and design surfaces

| Study | Comparison | Result |
|---|---|---|
| Sharma et al. (2026) | LLM personas against a 150-person study | Matched themes on trust, control and clarity; no numeric agreement; personas were more rationalized and less emotional |
| Zhong et al. (2025) | LLM cognitive walkthrough against 10 human evaluators | Agents completed tasks more often and found fewer failure points |
| Natalie et al. (2025) | Vision models against 40 people with low vision | Agreement 0.59 with minimal prompts, 0.70 with vision information and an example (abstract only) |
| Kuric et al. (2026) | GPT click predictions against real clicks (n = 3,431) | Significantly different in 53% of 12 first-click tests (abstract only) |
| Zhou et al. (2026) | 31 LLM user simulators against 451 humans, agent dialogue | Simulators were too cooperative and uniform, and inflated agent success (abstract only) |
| Guerino et al. (2025) | GPT-4o heuristic evaluation against human experts, no persona | Found 21.2% of the experts' issues and added 27 new ones (abstract only) |

No study compares simulated ND users with real ND users on usability problems, and no study counts how many usability problems simulated and real users share.

## 6. Emotional and factual feedback to AI agents

### 6.1. What makes feedback effective

- Specific, actionable feedback beat generic feedback, which beat none, with older models: 27.5, 26.0 and 24.8 on code optimization (Madaan et al., 2023).
- When a critique was split into parts, diagnosis-only feedback recovered 98.8% of the full critique's gain with 30.9% of its tokens. Location-only feedback recovered 62.3% and verdict-only 42.6% (Ryu et al., n.d.; abstract only).
- For factual consistency of summaries, feedback with reasoning and a fix beat error localization alone (Wadhwa et al., 2025).
- Feedback that named the failed checklist items lifted three current models from about 20–30% to about 95%, where no feedback did not (Lee et al., 2025). This compares feedback with none, not wording.

Not found: a study that varies severity labels, quoted evidence or reader-impact statements and measures the revision.

### 6.2. Pressure on a correct position

In 1,200 runs across 7 models, emotional appeals lowered a model's position strength in 44.3% of tactic turns, against 25.6% for credibility appeals, 21.6% for a plain direct challenge and 20.0% for logic-based pressure (Tang et al., 2026). The measure is a drop in position strength that an LLM judged, not a change to a wrong answer, and the study has no factual-evidence condition. When users rebutted a model's answer, simple rebuttals led to more corrections toward the right answer, and citation-style rebuttals to more changes toward a wrong one (Fanous et al., 2025); that study varies the content of the rebuttal, not its emotion.

### 6.3. Emotional tone of instructions (contested)

| Study | Result |
|---|---|
| Li et al. (2023) | Emotional stimuli added to prompts raised benchmark scores (abstract only) |
| Yin et al. (2024) | Impolite prompts often lowered performance in English, Chinese and Japanese (abstract only) |
| Dobariya and Kumar (2026) | 570 questions, four models: effects depend on the model; a threatening tone was the only one clearly worse on one model |
| Vaugrante et al. (2024) | Replication of the emotional-stimuli study: no significant gain for any model or benchmark |
| Zhao et al. (2026) | Six benchmarks: emotional prefixes usually change accuracy only slightly |
| Cai et al. (2026) | Three models, three tones, 10 runs: significant effects only in a subset of Humanities tasks |

All six studies vary the wording of the instruction in a single turn. **No study varies the emotional tone of feedback on a model's own previous output**; three citation chains found none.

## 7. What the research could not find

- A comparison of a simulated ND reader or user with real ND people on text review or usability problems.
- A study of an emotional reviewer persona's effect on critique of text or interfaces.
- A test of persona reviewers against repeated runs of one reviewer on text or interface defects, or of personas' effect on criticism overlap.
- A comparison of persona-based review with guidance-based review for ND readers.
- A mitigation for flattening, tested on disability or ND personas against the people concerned.
- A study of the emotional tone of feedback on an agent's earlier output, or of severity labels and quoted evidence in feedback.
- The audit of LLM portrayals of eight ND identities by Toxtli and Delaflor (AIES 2026) was blocked and is not used; it could change section 1.
- One citation index refused requests during the run, so the citation chains used a second index that can lag for 2026 preprints. "No citing work" results are uncertain.
- Nario-Redmond et al. (2017) on disability simulation was seen only through a news report and is not used.

Open question (low priority): how well LLM personas hold in non-English languages, measured against human data.

The research board is in `.research/persona-reviewer-agents/`.

## References

Ann, S. E., Liu, H., & Tan, C. (2026). *The interaction tax: When communication erases diversity in multi-agent teams*. arXiv. https://arxiv.org/html/2608.23541

Bennett, C. L., & Rosner, D. K. (2019). The promise of empathy: Design, disability, and knowing the "other". In *ACM CHI 2019* (Paper 298). Copy read at https://www.readkong.com/page/the-promise-of-empathy-design-disability-and-knowing-the-2909982

Bojic, L., Felfernig, A., Dinic, B., Ilic, V., Rettinger, A., Mevorah, V., & Trilling, D. (2026). *LLM agents predict social media reactions but do not outperform text classifiers: Benchmarking simulation accuracy using 120K+ personas of 1511 humans*. arXiv. https://arxiv.org/abs/2604.19787

Bombieri, M., Ponzetto, S. P., & Rospocher, M. (2026). *Shiny stories, hidden struggles: Investigating the representation of disability through the lens of LLMs*. arXiv. https://arxiv.org/abs/2605.20191

Buitrago López, A., Ortega Pastor, A., Pastor-Galindo, J., & Ruipérez-Valiente, J. A. (2026). *Evaluating the realism of LLM-powered social agents: A case study of reactions to Spanish online news*. arXiv. https://arxiv.org/abs/2605.28598

Cai, H., Shen, B., Jin, L., Hu, L., & Fan, X. (2026). *Does tone change the answer? Evaluating prompt politeness effects on modern LLMs: GPT, Gemini, and LLaMA*. arXiv. https://arxiv.org/html/2512.12812

Chan, C.-M., Chen, W., Su, Y., Yu, J., Liu, Z., Fu, J., Xue, W., & Zhang, S. (2023). *ChatEval: Towards better LLM-based evaluators through multi-agent debate*. arXiv. https://arxiv.org/html/2308.07201

Chen, N., Fang, H., Wang, P., Liu, J., Sakai, T., & Wu, X.-M. (2026). *Judging with personality and confidence: A study on personality-conditioned LLM relevance assessment*. arXiv. https://arxiv.org/abs/2601.01862

Chiappone, F., Marocco, D., & Milano, N. (2026). *Large language models as simulative agents for neurodivergent adult psychometric profiles*. arXiv. https://arxiv.org/pdf/2601.15319

Coda-Forno, J., Witte, K., Jagadish, A. K., Binz, M., Akata, Z., & Schulz, E. (2023). *Inducing anxiety in large language models can induce bias*. arXiv. https://arxiv.org/abs/2304.11111

Ding, Y., Zimmermann, T., & Ahmed, I. (2026). *Agents with feelings? Personality and emotion in multi-agent software teams*. arXiv. https://arxiv.org/abs/2607.05659

Dobariya, O., & Kumar, A. (2026). *Mind your tone: Does tone alter LLM performance?* Americas Conference on Information Systems (AMCIS 2026). https://arxiv.org/pdf/2605.29027

Fanous, A., Goldberg, J., Agarwal, A., Lin, J., Zhou, A., Xu, S., Bikia, V., Daneshjou, R., & Koyejo, S. (2025). *SycEval: Evaluating LLM sycophancy*. arXiv. https://arxiv.org/html/2502.08177v4

Ferreira, L., Liu, G., & Zheng, K. (2026). *Beyond symmetric agents: Cognitive diversity and multi-agent debate in small language models*. arXiv. https://arxiv.org/html/2609.35875

Guerino, G., Rodrigues, L., Capeleti, B., Mello, R. F., Freire, A., & Zaina, L. (2025). *Can GPT-4o evaluate usability like human experts? A comparative study on issue identification in heuristic evaluation*. arXiv. https://arxiv.org/abs/2506.16345

Ho, M. K., Zhu, Z., Zhu, R., Li, L., Fan, Z., Wang, Z., & Hong, J. (2026). *Can induced emotion bias LLM behaviors in sequential decision making?* arXiv. https://arxiv.org/abs/2607.12631

Hu, T., & Collier, N. (2024). *Quantifying the persona effect in LLM simulations*. arXiv. https://arxiv.org/abs/2402.10811

Hu, Z., Lian, J., Xiao, Z., Xiong, M., Wang, T., Xiao, T., Lei, Y., Jiang, F., Ding, K., Xiao, Z., Yuan, N. J., Xie, X., & Poovendran, R. (2025). *Population-aligned persona generation for LLM-based social simulation*. arXiv. https://arxiv.org/pdf/2509.10127

Huang, J., Lam, M. H., Li, E. J., Ren, S., Wang, W., Jiao, W., Tu, Z., & Lyu, M. R. (2024). *Emotionally numb or empathetic? Evaluating how LLMs feel using EmotionBench*. arXiv. https://arxiv.org/abs/2308.03656

Jung, H., & Na, W. (2026). *Logarithmic scores, power-law discoveries: Disentangling measurement from coverage in agent-based evaluation*. arXiv. https://arxiv.org/abs/2604.00477

Kim, S., Yoon, D., Gashteovski, K., et al. (2026). *On the limits and opportunities of AI reviewers: Reviewing the reviews of Nature-family papers with 45 expert scientists*. arXiv. https://arxiv.org/html/2605.20668

Kuric, E., Demcak, P., & Krajcovic, M. (2026). *What would GPT click: Practical effects of human-AI behavioral misalignment and the cost of synthetic participants in user experience*. arXiv. https://arxiv.org/abs/2605.18302

Lee, Y.-J., Kim, S., Lee, B.-K., Moon, M., Hwang, Y., Kim, J. M., Neubig, G., Welleck, S., & Choi, H.-J. (2025). *RefineBench: Evaluating refinement capability of language models via checklists*. arXiv. https://arxiv.org/html/2511.22173

Li, C., Wang, J., Zhang, Y., Zhu, K., Hou, W., Lian, J., Luo, F., Yang, Q., & Xie, X. (2023). *Large language models understand and can be enhanced by emotional stimuli*. arXiv. https://arxiv.org/abs/2307.11760

Liu, R., Yen, H., Marjieh, R., Griffiths, T. L., & Krishna, R. (2023). *Improving interpersonal communication by simulating audiences with language models*. arXiv. https://arxiv.org/abs/2311.00687

Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., Alon, U., Dziri, N., Prabhumoye, S., Yang, Y., Gupta, S., Majumder, B. P., Hermann, K., Welleck, S., Yazdanbakhsh, A., & Clark, P. (2023). *Self-Refine: Iterative refinement with self-feedback*. arXiv. https://arxiv.org/html/2303.17651v2

Maiorano, A. C. (2026). *Do synthetic personas predict real audience response? A headline-ranking study with a generic-reader baseline*. arXiv. https://arxiv.org/abs/2609.25010

Muralidharan, R., Kwak, H., & An, J. (2025). *Can lessons from human teams be applied to multi-agent systems? The role of structure, diversity, and interaction dynamics*. arXiv. https://arxiv.org/html/2510.07488v2

Natalie, R., Xu, W., Chang, R.-C., Mihalcea, R., & Guo, A. (2025). *Not there yet: Evaluating vision language models in simulating the visual perception of people with low vision*. arXiv. https://arxiv.org/abs/2508.10972

Park, J. S., Zou, C. Q., Kamphorst, J., Egan, N., Shaw, A., Hill, B. M., Cai, C., Morris, M. R., Liang, P., Willer, R., & Bernstein, M. S. (2024). *LLM agents grounded in self-reports enable general-purpose simulation of individuals*. arXiv. https://arxiv.org/pdf/2411.10109

Park, S., Beltran, J. A., Min, A., Ritt-Olson, A., & Hayes, G. R. (2026). *Exploring implicit perspectives on autism in large language models through multi-agent simulations*. arXiv. https://arxiv.org/abs/2601.15437

Rizvi, N., Rizvi, M., Ahmedi, S., Bidon, H. G. R., Strickland, H., & Ousidhoum, N. (2026). *Algorithmic fragility and persona bias in LLM-generated autistic communication*. arXiv. https://arxiv.org/pdf/2605.26397

Ryu, H., Oh, J., Ahn, S., & Yun, S.-Y. (n.d.). *Diagnose, then select: What makes critique-based refinement effective?* NeurIPS 2026 Workshop on Resource-Aware Agentic AI. https://neurips.cc/virtual/2026/170672

Saim, M., & Jiang, T. (2026). Do emotions influence moral judgment in large language models? In *Findings of the Association for Computational Linguistics: ACL 2026* (pp. 26996–27013). https://aclanthology.org/2026.findings-acl.1346/

Seeman-Horwitz, L., Montgomery, R. B., Lee, S., & Ran, R. (Eds.). (2021). *Making content usable for people with cognitive and learning disabilities*. W3C. https://www.w3.org/TR/coga-usable/

Sharma, K., Phatak, A., Petrosyan, T., & Tripathy, C. (2026). AI personas for UX research in large scale retail. In *CEUR Workshop Proceedings, ACM CHI'26 Workshop on Responsible Use of AI Personas in Human-Centered Design and Research*. https://ceur-ws.org/Vol-4249/paper2.pdf

Song, M., Kim, C., Eo, S., & Park, C. (2026). *Beyond consensus: Downward bias and role asymmetry in multi-agent LLM judges for subjective evaluation*. arXiv. https://arxiv.org/abs/2608.30373

Soós, D., Jiang, M., & Wu, J. (2026). *KnowledgeGain: Evaluating and optimizing science news generation for reader learning*. arXiv. https://arxiv.org/html/2605.31099

Stimpunks Foundation. (n.d.). *AI collaboration at Stimpunks*. https://stimpunks.org/ethics/ai-collaboration/

Tang, L., Wei, K., Jiang, T., & Huang, R. (2026). *SPINE: Measuring LLM sycophancy under sustained multi-turn pressure*. arXiv. https://arxiv.org/abs/2609.09090

Vaugrante, L., Niepert, M., & Hagendorff, T. (2024). *A looming replication crisis in evaluating behavior in language models? Evidence and solutions*. arXiv. https://arxiv.org/pdf/2409.20303

Venkit, P. N., Li, Y., Pruksachatkun, Y., & Wu, C.-S. (2026). *The need for a socially-grounded persona framework for user simulation*. arXiv. https://arxiv.org/pdf/2601.07110

Wadhwa, M., Zhao, X., Li, J. J., & Durrett, G. (2025). *Learning to refine with fine-grained natural language feedback*. arXiv. https://arxiv.org/pdf/2407.02397

Wang, A., Morgenstern, J., & Dickerson, J. P. (2024). *Large language models that replace human participants can harmfully misportray and flatten identity groups*. arXiv. https://arxiv.org/abs/2402.01908

Wang, X., Wang, J., Wang, Y., Dang, P., Cao, S., & Zhang, C. (2026). *MARS: Toward more efficient multi-agent collaboration for LLM reasoning*. arXiv. https://arxiv.org/abs/2509.20502

Weatherhead, S., Newell, B., Belbasis, A., & Salim, F. (2026). *Imperfectly imperfect: Evaluating graded cognitive diversity in LLM persona simulations*. arXiv. https://arxiv.org/abs/2611.10508

Wohn, C., Çarık, B., Ding, X., Lee, S. W., Kim, Y.-H., & Rho, E. H. (2026). *"Are we writing an advice column for Spock here?" Understanding stereotypes in AI advice for autistic users*. arXiv. https://arxiv.org/abs/2601.12690

Wu, C., Wang, P., Nibras, N., Li, M., Yuan, D., Wang, Z., He, J., Ali, M., & Prpa, M. (2025). *Understanding Down syndrome stereotypes in LLM-based personas*. arXiv. https://arxiv.org/html/2512.02275

Yin, Z., Wang, H., Horio, K., Kawahara, D., & Sekine, S. (2024). *Should we respect LLMs? A cross-lingual study on the influence of prompt politeness on LLM performance*. arXiv. https://arxiv.org/abs/2402.14531

Yu, S., Ling, Y., Fang, C., Chen, Z., & Chen, C. (2026). *Towards automated crowdsourced testing via personified-LLM*. arXiv. https://arxiv.org/abs/2603.24160

Zhao, M., Yang, Y., Peng, C., Gonsalves, R., Li, W., Yang, R., Liu, Z., & Wang, M. (2026). *Do emotions in prompts matter? Effects of emotional framing on large language models*. arXiv. https://arxiv.org/html/2604.02236

Zheng, M., Pei, J., Logeswaran, L., Lee, M., & Jurgens, D. (2024). *When "a helpful assistant" is not really helpful: Personas in system prompts do not improve performances of large language models*. arXiv. https://arxiv.org/html/2311.10054v3

Zhong, R., McDonald, D. W., & Hsieh, G. (2025). *Synthetic cognitive walkthrough: Aligning large language model performance with human cognitive walkthrough*. arXiv. https://arxiv.org/html/2512.03568v1

Zhou, X., Sun, W., Ma, Q., Xie, Y., Liu, J., Du, W., Welleck, S., Yang, Y., Neubig, G., Wu, S. T., & Sap, M. (2026). *Mind the sim2real gap in user simulation for agentic tasks*. arXiv. https://arxiv.org/abs/2603.11245
