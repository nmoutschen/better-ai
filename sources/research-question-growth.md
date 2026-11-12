# How to rank and bound the questions research agents add, and whether the coordinator should arbitrate them

Research register · Search date: 12 November 2026

**Scope.** Two open design points for `/research-better`, raised after the `human-cognition` board in `../nicopedia` grew from 16 to 80 questions in 17 minutes. (1) How should a question added during a run get its priority, and how should growth be bounded, without cutting off important questions far from the seeds, and with finer control than three priority levels? (3) Should the coordinator arbitrate proposed questions (merge duplicates, set priority, reject), and what does that cost? Removing challenge questions on challenge questions is settled and out of scope.

**Status.** 18 questions closed at `medium` or above; 1 low-priority chain question left open (section 4). Five Sonnet workers and three Sonnet verifiers ran on the board at `.research/research-question-growth/`. Verifiers checked all 77 claims against the source pages; 67 passed, and the coordinator corrected the 10 that failed to match what the page says. About half the sources were read as abstracts only, and most evidence on LLM agents comes from 2025–2026 arXiv preprints, each testing one system. None of the sources tests a research-question board directly, so every application to the skill in section 3 is my inference.

## 1. Findings on point 1: priority and bounds for added questions

### 1.1. Inheriting the parent's priority is the baseline that focused crawling replaced

A focused crawler faces the same problem as the board: it must rank links it has not visited yet. The early design gave an unvisited page the priority of its parent page (Chakrabarti et al., 2002). Relevance to a topic drops within a few links of a relevant start page (Chakrabarti et al., 2002), so a priority tied to the parent decays with distance.

Later designs score each link on its own features:
- Chakrabarti et al. (2002) report that scoring links on their own features cut the loss rate by 30–90% compared with the parent-inheriting baseline, and found crawl paths the baseline never expanded.
- In Pirkola and Talvensaari (2009), the strategy where an unseen page takes its parent's relevance probability did not perform well against query-based strategies that score link-context words.
- Tunneling, which lets a crawler pass through irrelevant pages to reach relevant ones further on, did better later in the crawl but worse early in one preliminary single-topic test (Tsoi et al., 2003). A block-scoring variant reports a higher harvest rate than best-first and breadth-first, in the authors' abstract only (Luo & Zuo, 2007).
- Three later studies that cite Chakrabarti et al. (2002) all support per-link scoring, but none repeats the 30–90% figure, and all were read as abstracts (Barbosa & Freire, 2007; Pant & Srinivasan, 2005; Batsakis et al., 2009).

The challenge question found no direct comparison in which inherited priority wins. Two indirect results qualify the finding: plain breadth-first order found high-quality pages early, though quality declined later in the crawl (Najork & Wiener, 2001), and a per-page classifier was costlier and did worse than cheaper query-based scoring (Pirkola & Talvensaari, 2009). So per-item scoring wins when the per-item score is cheap and relevant, not whenever it is used.

No source tested a rule like "a new question cannot outrank its origin". That rule is the crawler baseline in a new setting.

### 1.2. Deep-research systems bound growth with caps, pruning and stop signals, with small or unmeasured effects

- Static-DRA limits its tree with a depth parameter and a breadth parameter that shrinks at each level; its text says breadth is halved, its algorithm subtracts 2. The rule was not ablated and no cost was measured (Prateek, 2025).
- FlashResearch caps breadth at 6, deepens a node only when gain per latency passes a threshold, and prunes low-yield nodes and their descendants once an LLM judges the goal satisfied (Nie et al., 2025). In its ablation at 10 minutes, quality was 83.90 with planning and orchestration and 82.69 without, with 98.43 versus 68.00 nodes and $0.6811 versus $0.5629 per question. Pruning was not isolated.
- Anthropic added effort-scaling rules to its lead agent's prompt because early versions over-spawned subagents. Multi-agent runs use about 15 times the tokens of chat, and token usage explains 80% of the variance in BrowseComp performance (Hadfield et al., 2025).
- A controller that stops deep-research agents on novelty and coverage signals (RAAC) cut search calls by 14 on average and raised accuracy by 3% on BrowseComp-Plus (Soudani et al., 2026). A related exhaustion gate saved up to 39% of tokens with no reported loss (Kausik et al., 2026).

The challenge question found that stopping too early costs quality:
- Removing agent-level termination criteria lowered quality from 82.09 to 73.67 and coverage from 4.31 to 4.02, which the authors attribute to premature termination. The result is limited to one enterprise setting (Choubey et al., 2026).
- A 20-episode search cap is estimated to concede at most 14% of accuracy, because evidence that arrives late is lost. The estimate assumes the answer would not change under early stopping, so hard truncation may lose more (Liu et al., 2026).

These measure caps on steps and termination, not caps on added questions.

### 1.3. More priority levels do not reliably give finer control

The evidence on LLM rating scales is mixed:
- With a fine-grained scale, pointwise LLM scoring closes much of the gap to listwise ranking, and the gap is often not statistically significant (Godfrey et al., 2025).
- In one judge, widening the scale from 5 to 100 points reduced conflicts between pointwise scores and pairwise preferences (Wang et al., 2025).
- Among three tested scales, 0–5 gave the best human–LLM agreement, and the choice of scale shifted agreement substantially (Li et al., 2026).
- Single LLM ratings are unstable under sampling and compress near the top of the scale, with frequent ties (Girrbach et al., 2025).
- A 2026 study found that finer scales often agreed more with human labels in argument-quality assessment (Marchetti et al., 2026).

A judge that sees the whole list is not a clean fix: input order affects LLM scores, pairwise preferences and rankings (Bito et al., 2026). Shuffling the order and aggregating rankings improved listwise ranking (Tang et al., 2023), and averaging sampled judge scores correlated best with humans (Yamauchi et al., 2025); neither source gives a call count.

No study tests a three-level scale against finer ones for research-question priority. Direct studies of LLM task-priority agreement are scarce; one study of LLM user-story prioritization reports moderate agreement with experts and variability across runs, read as an abstract (Sami et al., 2025).

### 1.4. Choosing questions by expected effect on the answer beats prompting alone, in toy tasks

Choosing the next question by expected information gain beat prompting-based question generation on 20 Questions and preference inference (Choudhury et al., 2025). Uncertainty of Thoughts, which rewards questions by information gain, improved task completion by 38.1% on average over direct prompting, at about 9.2k GPT-4 tokens against 4.7k for its pruned version, and limits lookahead to three steps because of cost (Hu et al., 2024). Neither tests research questions.

### 1.5. Human reviews fix the question and let the search evolve

In scoping studies the research question is stated up front and the search is refined from what early results show (Levac et al., 2010). Cochrane requires changes after a review starts to be documented and reported, with sensitivity analyses of their impact when possible (Cochrane, 2023). Of 15 stopping methods for screening records, evaluated on 81 reviews, only one reliably reached the recall target (Repke et al., 2026). No source gives a rule for admitting new questions during a review.

## 2. Findings on point 3: the coordinator as arbitrator

### 2.1. Workers proposing and a lead deciding did best in the two comparisons found

- In LATTE, workers propose changes to the task graph and a lead accepts or rejects them. It reached 80% accuracy against 70% for a leader–worker team and 74% for a decentralized team (Mieczkowski et al., 2026; figures from its Table 2, read through a fetch tool). The paper names a bottleneck and a single point of failure as costs of centralization.
- In multi-robot planning, a hybrid design beat both pure designs; a single central planner scaled worse as agents were added, and the decentralized design had the lowest success and highest token use (Chen et al., 2024).
- In an LLM blackboard system, runs without the control unit that picks which agents act used about 2.9 to 4.5 times the tokens, with accuracy within about 0.5 points (Han & Zhang, 2025).
- Anthropic's lead agent decides alone whether more subagents are needed; early versions over-spawned, and synchronous central control caused bottlenecks (Hadfield et al., 2025).

No independent test of LATTE exists among its three citing works (read as abstracts).

### 2.2. Central review helps only when the reviewer can check the work

The challenge question found conditions where central review hurts:
- In a paired experiment, flat teams wrote better reports than hierarchical teams whose manager could send work back. Manager authority improved quality when the manager could verify the work, and lowered it when the manager could only give feedback (Agachan et al., 2026; abstract).
- Across 180 runs, whether centralized coordination helps depends on its fit with the task, and mismatched coordination degrades performance. Designs without central verification propagated errors more (Kim et al., 2025; abstract).

### 2.3. Duplicate detection by LLMs is not measured for research questions

On the nearest task, a fine-tuned LLaMA-7B reached F1 84.9% on Quora Question Pairs duplicate detection (Han et al., 2025). In entity matching, LLMs fail on names in different scripts while rules over-match (Smith et al., 2026). Neither separates false merges from missed paraphrases.

### 2.4. Local evidence from the nicopedia board

On the `human-cognition` board, the coordinator, told by the user to arbitrate, merged 13 questions into others, about 1 in 5 of the questions workers added. One worker had started on a question when it was withdrawn as a duplicate.

### 2.5. Classic blackboard schedulers

How Hearsay-II and BB1 rated pending work could not be established: the primary papers were scanned, blocked or unreadable (Hayes-Roth, 1985, blocked). The Hearsay-II builders' retrospective reports a workable focus-of-attention scheme, read as an abstract (Lesser & Erman, 1977).

## 3. What this means for the skill (my inferences)

1. **Score each added question on its own stakes, not its parent's priority.** The crawler evidence (1.1) is the closest test of the inherit-and-drop rule, and it favours per-item scoring. This drops the rule I proposed.
2. **Bound growth by what the goal still needs, not by depth or count.** Fixed caps lose late evidence (1.2), and human reviews bound work by the question (1.5). The tested bounds that work stop on goal satisfaction, novelty or gain (FlashResearch, RAAC).
3. **More levels are not the way to get finer control.** Scale evidence is mixed (1.3). Finer control can come from the admission test instead: what conclusion for the goal would this answer change, and does another question already cover it (1.4).
4. **Arbitration fits the design that did best (2.1), under one condition (2.2):** the coordinator decides against something it can check, such as the board's existing questions and the goal, rather than judging the research itself. Its whole-board view brings order effects (1.3), so it should compare a proposal with the goal and with similar questions, not rank the full list.
5. **Merges can be wrong (2.3).** A merged question should stay on the board, marked with the question it was merged into, so a false merge can be undone.

## 4. Open questions

- Q-w5-1 (low): references and citing works of Marchetti et al. (2026).
- Q-w2-4 and Q-coordinator-7 (not found): how Hearsay-II and BB1 schedulers rated pending activations. Hayes-Roth (1985) and the scanned AAAI-82 paper could not be read; OCR was not available.
- Garousi et al.'s grey-literature guidelines, which give saturation criteria, were blocked.

## References

Agachan, B., van Duijn, M., & Zohrehvand, A. (2026). *Loop-back authority in LLM agent teams: A paired experiment on flat and hierarchical coordination* (arXiv:2609.14767). arXiv. https://arxiv.org/abs/2609.14767

Barbosa, L., & Freire, J. (2007). An adaptive crawler for locating hidden-web entry points. *WWW2007*. ACM. https://archives.iw3c2.org/www2007/paper429.php.html

Batsakis, S., Petrakis, E. G. M., & Milios, E. (2009). Improving the performance of focused web crawlers. *Data and Knowledge Engineering, 68*(10). https://pure.hud.ac.uk/en/publications/improving-the-performance-of-focused-web-crawlers/

Bito, E., Ren, Y., & He, E. (2026). *Position bias undermines preference consistency in listwise LLM-based reranking* (arXiv:2608.03091). arXiv. https://arxiv.org/abs/2608.03091

Chakrabarti, S., Punera, K., & Subramanyam, M. (2002). Accelerated focused crawling through online relevance feedback. *WWW2002*. ACM. https://archives.iw3c2.org/www2002/CDROM/refereed/336.html

Chen, Y., Arkin, J., Zhang, Y., Roy, N., & Fan, C. (2024). *Scalable multi-robot collaboration with large language models: Centralized or decentralized systems?* (arXiv:2309.15943v2). arXiv. https://arxiv.org/html/2309.15943v2

Choubey, P. K., Huang, K.-H., Venkit, P. N., Zhang, J., et al. (2026). *Don't stop early: Scalable enterprise deep research with controlled information flow and evidence-aware termination* (arXiv:2604.24978). arXiv. https://arxiv.org/html/2604.24978

Choudhury, D., Williamson, S., Golinski, A., Miao, N., Bickford Smith, F., et al. (2025). *BED-LLM: Intelligent information gathering with LLMs and Bayesian experimental design* (arXiv:2508.21184). arXiv. https://arxiv.org/abs/2508.21184

Cochrane. (2023). Chapter II: Planning a Cochrane review. In *Cochrane handbook for systematic reviews of interventions* (version 6.5). https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-ii

Girrbach, L., Su, C.-P., Saanum, T., Socher, R., Schulz, E., & Akata, Z. (2025). *Reference-free rating of LLM responses via latent information* (arXiv:2509.24678). arXiv. https://arxiv.org/abs/2509.24678

Godfrey, C., Nie, P., Ostapuk, N., Ken, D., Gao, S., & Inati, S. (2025). *Likert or not: LLM absolute relevance judgments on fine-grained ordinal scales* (arXiv:2505.19334). arXiv. https://arxiv.org/abs/2505.19334

Hadfield, J., Zhang, B., Lien, K., Scholz, F., Fox, J., & Ford, D. (2025, June 13). *How we built our multi-agent research system*. Anthropic. https://www.anthropic.com/engineering/multi-agent-research-system

Han, B., & Zhang, S. (2025). *Exploring advanced LLM multi-agent systems based on blackboard architecture* (arXiv:2507.01701). arXiv. https://arxiv.org/html/2507.01701v1

Han, S., Shi, L., & Tsui, F. (2025). Enhancing semantical text understanding with fine-tuned large language models: A case study on Quora Question Pair duplicate identification. *PLoS One, 20*(1), e0317042. https://pmc.ncbi.nlm.nih.gov/articles/PMC11723592/

Hayes-Roth, B. (1985). A blackboard architecture for control. *Artificial Intelligence, 26*(3), 251–321. https://www.sciencedirect.com/science/article/pii/0004370285900633

Hu, Z., Liu, C., Feng, X., Zhao, Y., Ng, S.-K., Luu, A. T., et al. (2024). *Uncertainty of thoughts: Uncertainty-aware planning enhances information seeking in large language models* (arXiv:2402.03271). arXiv. https://arxiv.org/html/2402.03271v3

Kausik, C., Swaminathan, A., & Kallus, N. (2026). *The context gathering decision process: A POMDP framework for agentic search* (arXiv:2605.07042). arXiv. https://arxiv.org/abs/2605.07042

Kim, Y., Gu, K., Park, C., et al. (2025). *Towards a science of scaling agent systems* (arXiv:2512.08296). arXiv. https://arxiv.org/abs/2512.08296

Lesser, V. R., & Erman, L. D. (1977). A retrospective view of the Hearsay-II architecture. In *Proceedings of IJCAI-77* (pp. 790–799). IJCAI. https://ijcai.org/proceedings/1977/191

Levac, D., Colquhoun, H., & O'Brien, K. K. (2010). Scoping studies: Advancing the methodology. *Implementation Science, 5*, 69. https://pmc.ncbi.nlm.nih.gov/articles/PMC2954944/

Li, W., Zhao, M., Dong, W., et al. (2026). *Grading scale impact on LLM-as-a-judge: Human-LLM alignment is highest on 0-5 grading scale* (arXiv:2601.03444). arXiv. https://arxiv.org/abs/2601.03444

Liu, Q., Mao, J., Zhu, F., & Chua, T.-S. (2026). *Diagnosing search behavior and failure modes in long-horizon search agents* (arXiv:2608.01913). arXiv. https://arxiv.org/html/2608.01913

Luo, N., & Zuo, W. (2007). Gray tunneling based on block relevance for focused crawling. In *ISKE 2007* (pp. 609–613). Atlantis Press. https://atlantis-press.com/proceedings/iske2007/1288

Marchetti, G. A., Rocha, G., & Lopes Cardoso, H. (2026). Calibrating LLM-as-a-judge for argument quality assessment through prompting and scoring scale design. In *Proceedings of LUHME 2026* (pp. 197–214). Association for Computational Linguistics. https://aclanthology.org/2026.luhme-1.16/

Mieczkowski, E., Ku, A., Eisape, T., Arumugam, D., et al. (2026). *Improving the efficiency of language agent teams with adaptive task graphs* (arXiv:2605.06320). arXiv. https://arxiv.org/html/2605.06320v1

Najork, M., & Wiener, J. L. (2001). Breadth-first search crawling yields high-quality pages. *WWW10*. ACM. https://archives.iw3c2.org/www10/cdrom/papers/208/index.html

Nie, L., Lipka, N., Rossi, R. A., & Chaudhuri, S. (2025). *Efficient tree-structured deep research with adaptive resource allocation (FlashResearch)* (arXiv:2510.05145). arXiv. https://arxiv.org/html/2510.05145v2

Pant, G., & Srinivasan, P. (2005). Learning to crawl: Comparing classification schemes. *ACM Transactions on Information Systems, 23*. https://experts.illinois.edu/en/publications/learning-to-crawl-comparing-classification-schemes/

Pirkola, A., & Talvensaari, T. (2009). Effects of crawling strategies on the performance of focused web crawling. In *WEBIST 2009*. SCITEPRESS. https://scitepress.org/Papers/2009/20376/pdf/index.html

Prateek, S. (2025). *A hierarchical tree-based approach for creating configurable and static deep research agent (Static-DRA)* (arXiv:2512.03887). arXiv. https://arxiv.org/html/2512.03887v2

Repke, T., Tinsdeall, F., Danilenko, D., Graziosi, S., Müller-Hansen, F., et al. (2026). Don't stop me now, 'cause I'm having a good time screening: Evaluation of stopping methods for safe use of priority screening. *Cochrane Evidence Synthesis and Methods, 4*(1), e7. https://pmc.ncbi.nlm.nih.gov/articles/PMC12825451/

Sami, M. A., Zhang, Z., Waseem, M., Kemell, K. K., et al. (2025). A multi-agent LLM system for automated requirements analysis: A study on user story generation and prioritization. In *SEAA 2025* (LNCS 16082). Springer. https://researchportal.tuni.fi/en/publications/a-multi-agent-llm-system-forautomated-requirements-analysis-a-stu/

Smith, C., Sesodia, M., Lindenberg, F., & Schroeder de Witt, C. (2026). *OpenSanctions pairs: Large-scale entity matching with LLMs* (arXiv:2603.11051). arXiv. https://arxiv.org/abs/2603.11051

Soudani, H., Lingg, E., Hasibi, F., & Rekabsaz, N. (2026). *When deep research agents stagnate: Enhancing reasoning with retrieval-aware agent control* (arXiv:2608.15191). arXiv. https://arxiv.org/abs/2608.15191

Tang, R., Zhang, X., Ma, X., Lin, J., & Ture, F. (2023). *Found in the middle: Permutation self-consistency improves listwise ranking in large language models* (arXiv:2310.07712). arXiv. https://arxiv.org/abs/2310.07712

Tsoi, A. C., Forsali, D., Gori, M., Hagenbuchner, M., & Scarselli, F. (2003). A simple focused crawler. *WWW2003 poster*. https://archives.iw3c2.org/www2003/cdrom/papers/poster/p181/p181-tsoi/p181-tsoi.html

Wang, Y., et al. (2025). *TrustJudge: Inconsistencies of LLM-as-a-judge and how to alleviate them* (arXiv:2509.21117). arXiv. https://arxiv.org/html/2509.21117v2

Yamauchi, Y., Yano, T., & Oyamada, M. (2025). *An empirical study of LLM-as-a-judge: How design choices impact evaluation reliability* (arXiv:2506.13639). arXiv. https://arxiv.org/html/2506.13639v1
