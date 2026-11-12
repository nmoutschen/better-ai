# How research agents add questions, and how to make them add more

Research register · Search date: 12 November 2026

**Scope.** How deep-research systems and human evidence-synthesis methods generate new questions during a run: widening the frontier, searching for disconfirming evidence, citation chaining, and scaling the run. Also covers the risks (too many questions, drift, redundancy) and the controls that bound them. The goal is to change `/research-better` so that its workers and its coordinator add questions more ambitiously.

**Status.** 14 questions closed at `medium` or above; 1 low-priority question left open (section 4). Four Sonnet workers and one coordinator ran the research. The coordinator checked all 76 claim quotes against the source pages (pdftotext for PDFs). Most evidence on LLM agents comes from 2025–2026 arXiv preprints with one system or benchmark each. The evidence on human methods comes from Cochrane and from one software-engineering research group. Section 3 labels which skill changes are design inferences.

## 1. Findings

### 1.1. Which agent adds questions in deployed systems

In the documented systems, the lead agent adds questions and sub-agents do not. Anthropic's LeadResearcher "synthesizes these results and decides whether more research is needed—if so, it can create additional subagents or refine its strategy" (Anthropic, 2025). Its sub-agents cannot coordinate. Anthropic names asynchronous execution, with "agents working concurrently and creating new subagents when needed", as future work. In open_deep_research, the supervisor asks itself "Should I delegate more research or call ResearchComplete?", and sub-agents "can't see other agents' work" (LangChain, n.d.). GPT Researcher's planner writes the questions up front, and execution agents only answer them (GPT Researcher, n.d.). A survey treats "question developing" as a separate stage that turns each sub-goal into queries (Zhang et al., 2025).

### 1.2. Adaptive plans versus fixed plans

No study isolates follow-up question generation against a fixed plan on recall. The indirect evidence favours plans that change during the run:
- In FlowSearch, adding a dynamic refiner to the flow planner raised the GAIA average from 61.82 to 82.42. A sequential planner scored 55.76 (Hu et al., 2025).
- In WebWeaver, outline quality rose over three search-and-revise rounds, from 81.9 to 92.3 on DeepResearch Bench (LLM-judged). Its authors argue that a static outline "rigidly confines the research to the LLM's internal, often outdated knowledge, making it blind to emergent insights" (Li et al., 2025).
- FlashResearch adapts breadth and depth at runtime. It reports better reports within fixed time budgets, or up to 5× speedup, against GPT Researcher. It also reports that fixed deep or broad trees give diminishing returns. The comparison bundles several changes (FlashResearch authors, 2025).

### 1.3. Agents search too little more often than too much

- In DEFT's failure taxonomy, "insufficient external information acquisition" is the most frequent retrieval failure, at 16.30% (OPPO AI Agent Team, 2025). "Rigid planning strategy" accounts for 5.60%.
- DAS defines under-search as premature termination that yields wrong answers. The under-search rate rises with the number of reasoning steps on every dataset tested (Zhang et al., 2026).
- On BrowseComp-Plus, Qwen3-32B and SearchR1-32B made fewer than 2 search calls per query "despite being explicitly prompted" to search, while gpt-5 and o3 made more than 20. Models that searched more scored higher, but this compares models, not settings (Chen et al., 2025).
- Search agents generate "more than half of their search queries from internally produced hypotheses rather than retrieved leads". After failed searches, they "often only rephrase the previous query" (Fan et al., 2026).
- Agents also stagnate: most iterations add little, and agents do not know what they have gathered or when to stop (Soudani et al., 2026).
- Over-search also exists. KARL agents kept searching after they held the answer (Databricks AI Research, 2026). In DAS, outcome-based RL cut under-search (0.672 to 0.505) but raised over-search (0.196 to 0.263) (Zhang et al., 2026). Pushing agents to search more trades one error for the other.
- DeepSearchQA reports both failures: "premature stopping (under-retrieval)" and "hedging behaviors" that "cast an overly wide net of low-confidence answers" (Gupta et al., 2026).

No study found measures question explosion or topic drift in LLM research agents directly.

### 1.4. Confirmation bias and disconfirming questions

- Across eleven LLMs, models "often [propose] triples to confirm their hypothesis rather than trying to falsify it". Prompts that ask for counterexamples raised rule discovery from 42% to 56% on average (Jhaveri et al., 2026). The task is synthetic.
- Deep-research agents show "verification inertia": they defer to a planted answer-like document. "Generic verification prompts reduce but do not close this gap" (Nie et al., 2026; abstract only).
- When a prompt implies a preferred answer, "models often reinforce that bias rather than explore alternatives". Multi-agent debate can create echo chambers (Kim & Torr, 2025; abstract only). Debate among proponent, opponent and judge agents has also been applied at the retrieval stage (Hu et al., 2025b; abstract only).
- Cochrane makes searching trial registers and checking reference lists mandatory, and rates grey literature and contacting experts as highly desirable, all to reduce publication bias (Cochrane, n.d.). Funnel-plot tests apply only with at least 10 studies and "should not be considered to be diagnostic" (Page et al., 2024).

No controlled test of a counter-evidence question or red-team sub-agent inside a research loop was found.

### 1.5. Citation chaining

- A hybrid of database search and snowballing "identified 30 percent more primary studies" than database search alone in a replication (Wohlin et al., 2023). In simulations over three reviews, Scopus search plus snowballing gave "the most appropriate balance of precision and recall" (Mourão et al., 2020).
- Automated one-hop citation searching had a median recall of 35.79% and a median precision of 2.57% across 27 reviews. It did worse than the original search strategies on recall, so it is a supplement, not a replacement. Performance varied by field (Rajit et al., 2025).
- The snowballing guideline stops at saturation: "Once no new papers are found in the iterations using both backward and forward snowballing, the loop is ended" (Wohlin, 2014). With a low-yield round, "we risk that the procedure stops early" (Wohlin et al., 2023). To update a review, a single forward iteration from the original review and its studies was the most cost-effective search (Wohlin et al., 2020).
- Reference-list checking has "utility … to supplement poorly developed search strategies" (Horsley et al., 2009). The underlying studies have weak designs.

### 1.6. Widening by language and discipline

- Dropping non-English references from 59 Cochrane reviews removed studies from 27% of them but changed 0.0% of conclusions (Nussbaumer-Streit et al., 2019; abstract only). A systematic review found no systematic bias from English-only restriction in conventional medicine and called for field-specific research ("The effect of English-language restriction", 2012; abstract only).
- A cross-disciplinary search framework reported higher sensitivity than discipline-specific searches in one worked example (Ciemer et al., 2025).
- Nothing was found that tests historical tracing or stakeholder perspectives as search strategies.

Widening by language changed no conclusions in clinical medicine. Whether it changes conclusions in other fields is untested.

### 1.7. Controls that bound growth and drift

- **Sufficiency criteria.** One system defines sufficiency conditions for each research step before it runs. Removing the explicit termination criteria caused the largest quality drop of any ablated component, and runs then stopped earlier with fewer tool calls (Choubey et al., 2026).
- **Novelty and an anchor to the question.** RAAC measures novelty as the fraction of retrieved documents not seen in earlier iterations. It also keeps a similarity guardrail between each query and the original question, so that novelty-seeking queries do not drift. It cut search calls by 14 on average and raised accuracy by up to 10% (Soudani et al., 2026).
- **Selective expansion.** In classical retrieval, automatic query expansion drifts from the original need, and applying it selectively improves results (Datta et al., 2024; abstract only).
- **Distinct tasks.** Vague sub-agent tasks caused duplicated searches. Anthropic fixed this with explicit objectives, output formats and task boundaries (Anthropic, 2025).
- **Effort rules.** Early Anthropic agents spawned "50 subagents for simple queries". Anthropic embedded scaling rules in the prompt: one agent for fact-finding, 2–4 for comparisons, more than 10 for complex research. open_deep_research caps iterations and parallel agents. No ablation of these caps was found.
- **Question value.** BED-LLM ranks candidate questions by expected information gain and more than doubles success over implicit LLM choice on 20 Questions (Choudhury et al., 2025). InForage uses information gain as an RL reward (Qian & Liu, 2025). Neither ranks a shared question queue.

### 1.8. Scaling the number of workers

- Anthropic reports that token usage explains 80% of the variance in BrowseComp performance, that its multi-agent system beat a single agent by 90.2% on an internal eval, and that multi-agent runs cost about 15× the tokens of a chat (Anthropic, 2025).
- A controlled study of 180 configurations found diminishing returns once the single-agent baseline is high. On BrowseComp-Plus the best multi-agent design gained up to 9.2%, against 80.8% on a parallelizable finance task. Independent agents amplified errors 17.2×, against 4.4× with central verification (Kim et al., 2025).

### 1.9. This run

14 questions: 13 from the coordinator (12 seeds and 1 added mid-run), 1 from a worker. The earlier tutoring run (blackboard report, 1.10) had 15 of 29 questions from workers, before the rule against source-detail questions. In this run, workers closed questions and stopped. The first worker stopped after one question, citing a budget the brief did not set. A later worker found no question left, so it did no work. No worker proposed a disconfirming question, a citation chain, or a question from another field or region.

## 2. Changes made to research-better

| Change | Source |
| --- | --- |
| After each question, the worker runs a frontier check: one question per lens (newer work, origins, adjacent fields, other regions or languages, critics and rival explanations) if a source it read points there, else "none" in its log | 1.2; 1.3 under-search and rigid plans; 1.9; Design inference for the lens list |
| Each new question names the source that raised it, states how its answer could change the conclusion, and gets a priority from that | 1.3 queries from own hypotheses; 1.7 query anchor, selective expansion |
| For each answered question the conclusion depends on, a challenge question asks what would contradict the answer. A different worker takes it. Searches target critiques, failed replications, negative or unpublished results, registers and boundary conditions, not negations | 1.4 |
| Chain questions: for each primary source the conclusion depends on, check what it cites and what cites it, one round at a time, until a round adds no new relevant source | 1.5 |
| Each question gets a `done-when` line: what evidence would answer it. Workers stop a question when it holds, not before | 1.7 sufficiency criteria; 1.3 over-search |
| The coordinator reviews gaps after each batch of closed questions and adds questions against the GOAL, not only conflict questions | 1.1; 1.2 |
| Worker count scales with the open questions at or above the stop level, instead of "up to a handful". The coordinator still verifies centrally | 1.8; 1.6 of the blackboard report. No fixed number: the earlier report rejected default budget numbers |
| Workers have no budget of searches or questions, and log a reason if they stop while questions remain. The coordinator replaces workers that stop early | 1.9; 1.3 premature termination |
| Challenge questions only after high-priority answers; a frontier or chain question with no stated stakes gets low priority | 1.3 over-search; 1.7 selective expansion. Design choice for the thresholds |
| Final findings state what each main claim's challenge question found | 1.4 |
| A chain ends when a round adds no relevant source. The existing stop rule (results add no new sources, terms, or questions) already covers saturation for the whole board | 1.5; 1.7 novelty |
| Questions record `kind` (seed, frontier, challenge, chain, conflict) so the coordinator can see whether challenge and chain work happened | Design choice |
| The rule against questions that check details of a known source stays | Blackboard report 1.10 |

## 3. Design inferences not tested

- The frontier lenses mix things that worked (adjacent disciplines, one case) with lenses that showed no effect in medicine (language) and lenses with no evidence (history, stakeholders). They are prompts for where to look, gated by a source pointing there, not required searches.
- Giving challenge questions to a different worker rests on the echo-chamber and motivated-dismissal findings, not on a test of that assignment.
- Saturation stopping comes from systematic reviews in software engineering, not from LLM agents.
- No evidence shows that prompt wording alone stops LLM workers from ending early (1.3: models searched little even when told to search). The "no budget" rule may not be enough. The coordinator's replacement rule is the fallback.

## 4. Open questions

- [Q-coordinator-12, low] Does multilingual querying change research findings outside clinical medicine?
- Does a challenge question taken by a separate worker find more disconfirming evidence than one taken by the worker who answered? Untested.
- Does a frontier check after every question improve coverage, or only cost? The next research-better runs can measure this from the board: questions per kind, and how many frontier questions reached high priority.

## 5. Sources

- Anthropic. (2025, June 13). *How we built our multi-agent research system*. Anthropic. https://www.anthropic.com/engineering/multi-agent-research-system
- The effect of English-language restriction on systematic review-based meta-analyses: A systematic review of empirical studies. (2012). *International Journal of Technology Assessment in Health Care, 28*(2), 138–144. https://www.cambridge.org/core/journals/international-journal-of-technology-assessment-in-health-care/article/effect-of-englishlanguage-restriction-on-systematic-reviewbased-metaanalyses-a-systematic-review-of-empirical-studies/993D98171701AEE0D97D68C324BFC82E (authors not listed in the page text read)
- Chen, Z., Ma, X., Zhuang, S., et al. (2025). *BrowseComp-Plus: A more fair and transparent evaluation benchmark of deep-research agent*. arXiv. https://arxiv.org/html/2508.06600
- Choubey, P. K., Huang, K.-H., Venkit, P. N., et al. (2026). *Don't stop early: Scalable enterprise deep research with controlled information flow and evidence-aware termination*. arXiv. https://arxiv.org/html/2604.24978
- Choudhury, D., Williamson, S., Goliński, A., et al. (2025). *BED-LLM: Intelligent information gathering with LLMs and Bayesian experimental design*. arXiv. https://arxiv.org/html/2508.21184v2
- Ciemer, C., Klotzbier, T. J., Ghellal, S., & Schott, N. (2025). Introducing CRIS: A unified framework for systematic literature searches across disciplines. *Frontiers in Public Health, 13*. https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2025.1489161/full
- Cochrane. (n.d.). *Searching for studies (C24–C38)*. MECIR Manual. https://www.cochrane.org/authors/handbooks-and-manuals/mecir-manual/standards-conduct-new-cochrane-intervention-reviews-c1-c75/performing-review-c24-c75/searching-studies-c24-c38
- Databricks AI Research. (2026). *KARL: Knowledge agents via reinforcement learning*. arXiv. https://arxiv.org/html/2603.05218
- Datta, S., Ganguly, D., MacAvaney, S., & Greene, D. (2024). *A deep learning approach for selective relevance feedback*. arXiv. https://arxiv.org/abs/2401.11198
- Fan, H., Wang, X., Chu, Z., et al. (2026). *LiveBrowseComp: Are search agents searching, or just verifying what they already know?* arXiv. https://arxiv.org/html/2605.28721
- FlashResearch authors. (2025). *FlashResearch: Real-time agent orchestration for efficient deep research*. arXiv. https://arxiv.org/html/2510.05145v1
- GPT Researcher. (n.d.). *Introduction*. https://docs.gptr.dev/docs/gpt-researcher/getting-started/introduction
- Gupta, N., Chatterjee, R., Haas, L., Tao, C., et al. (2026). *DeepSearchQA: Bridging the comprehensiveness gap for deep research agents*. arXiv. https://arxiv.org/pdf/2601.20975
- Horsley, T., Dingwall, O., Tetzlaff, J., & Sampson, M. (2009). *Checking reference lists to find additional studies for systematic reviews* [Oral presentation abstract]. Cochrane Colloquium, Singapore. https://abstracts.cochrane.org/2009-singapore/checking-reference-lists-find-additional-studies-systematic-reviews
- Hu, W., Zhang, W., Jiang, Y., Zhang, C. J., Wei, X., & Li, Q. (2025b). *Removal of hallucination on hallucination: Debate-augmented RAG*. arXiv. https://arxiv.org/abs/2505.18581
- Hu, Y., Ma, R., Fan, Y., Shi, J., Cao, Z., et al. (2025). *FlowSearch: Advancing deep research with dynamic structured knowledge flow*. arXiv. https://arxiv.org/html/2510.08521
- Jhaveri, A. R., GX-Chen, A., Sucholutsky, I., & Choi, E. (2026). *Failing to falsify: Evaluating and mitigating confirmation bias in language models*. arXiv. https://arxiv.org/html/2604.02485
- Kim, H., & Torr, P. (2025). *Single LLM debate, MoLaCE: Mixture of latent concept experts against confirmation bias*. arXiv. https://arxiv.org/abs/2512.23518
- Kim, Y., et al. (2025). *Towards a science of scaling agent systems*. arXiv. https://arxiv.org/html/2512.08296
- LangChain. (n.d.). *prompts.py* [open_deep_research repository]. GitHub. https://raw.githubusercontent.com/langchain-ai/open_deep_research/main/src/open_deep_research/prompts.py
- Li, Z., Guan, X., Zhang, B., Huang, S., Zhou, H., Lai, S., et al. (2025). *WebWeaver: Structuring web-scale evidence with dynamic outlines for open-ended deep research*. arXiv. https://arxiv.org/html/2509.13312
- Mourão, E., Pimentel, J. F., Murta, L., Kalinowski, M., Mendes, E., & Wohlin, C. (2020). *On the performance of hybrid search strategies for systematic literature reviews in software engineering*. arXiv. https://arxiv.org/abs/2004.09741
- Nie, J., Yang, Z., Tang, Z., Zhang, Y., Chu, X., Tian, X., & Han, B. (2026). *DRNOISE: Benchmarking deep research agents in misleading evidence environments*. arXiv. https://arxiv.org/abs/2607.17291
- Nussbaumer-Streit, B., Klerings, I., Persad, E., Dobrescu, A. I., Affengruber, L., & Gartlehner, G. (2019). *Excluding non-English studies from systematic reviews does not change conclusions: A meta-epidemiological study* [Poster abstract]. Cochrane Colloquium, Santiago. https://abstracts.cochrane.org/2019-santiago/excluding-non-english-studies-systematic-reviews-does-not-change-conclusions-meta
- OPPO AI Agent Team. (2025). *How far are we from genuinely useful deep research agents?* arXiv. https://arxiv.org/html/2512.01948
- Page, M. J., Higgins, J. P. T., & Sterne, J. A. C. (2024). Chapter 13: Assessing risk of bias due to missing evidence in a meta-analysis. In *Cochrane handbook for systematic reviews of interventions* (Version 6.5). Cochrane. https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-13
- Qian, H., & Liu, Z. (2025). *Scent of knowledge: Optimizing search-enhanced reasoning with information foraging*. arXiv. https://arxiv.org/html/2505.09316
- Rajit, D., Du, L., Teede, H., & Enticott, J. (2025). Automated citation searching in systematic review production: A simulation study. *Research Synthesis Methods, 16*, 211–227. https://www.cambridge.org/core/services/aop-cambridge-core/content/view/8B102232B819BB01644FB37BA1376CCA/S1759287924000152a.pdf/automated-citation-searching-in-systematic-review-production-a-simulation-study.pdf
- Soudani, H., Lingg, E., & Hasibi, F. (2026). *When deep research agents stagnate: Enhancing reasoning with retrieval-aware agent control*. arXiv. https://arxiv.org/html/2608.15191
- Wohlin, C. (2014). Guidelines for snowballing in systematic literature studies and a replication in software engineering. In *Proceedings of EASE '14*. ACM. http://www.wohlin.eu/ease14.pdf
- Wohlin, C., Kalinowski, M., Romero Felizardo, K., & Mendes, E. (2023). *Successful combination of database search and snowballing for identification of primary studies in systematic literature studies*. arXiv. https://arxiv.org/abs/2307.02612
- Wohlin, C., Mendes, E., Romero Felizardo, K., & Kalinowski, M. (2020). *Guidelines for the search strategy to update systematic literature reviews in software engineering*. arXiv. https://arxiv.org/pdf/2006.05542
- Zhang, W., Dong, K., Li, J., et al. (2026). *To search or not to search: Aligning the decision boundary of deep search agents via causal intervention*. arXiv. https://arxiv.org/html/2602.03304
- Zhang, W., Li, X., Zhang, Y., Jia, P., Wang, Y., Guo, H., Liu, Y., & Zhao, X. (2025). *Deep research: A survey of autonomous research agents*. arXiv. https://arxiv.org/html/2508.12752v1
