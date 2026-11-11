# Code review by AI agents

Research findings · Search date: 11 November 2026

LLM code reviewers find a minority of real defects and post many comments that developers do not act on. On defect benchmarks, current reviewers recall about 15–33% of known defects. In practice, developers act on fewer AI comments than human comments, and reject those that are generic, vague or wrong. AI reviewers comment on style and best practices more than humans do, and on correctness and security less. Every tested way to cut noise also cut real findings: verification passes drop true bugs, and more reviewers find more bugs and more false alarms. Models check their own work poorly without outside feedback such as test results. No study tests how an agent should review its own diff before handing it to the user.

**Scope.** How an AI agent reviews code so it finds real defects, avoids noise, verifies its findings, and reports them so the developer can act. The code may be the agent's own changes before delivery, or a user's or another agent's diff. Training review models and static-analysis internals are out of scope. These findings are input for a `code-better` skill. This report does not design it.

**Status.** 8 high- and medium-priority seed questions are answered. Of 3 follow-up questions, one is contested (section 5) and one found nothing (section 4.3). One low-priority question on false-positive thresholds is still open. 42 sources remain after merging the duplicates two workers found. Of 118 claims, I found the quotes of 115 on their source pages; the 3 I could not check are marked *unverified* below. Two sources are vendor blogs with self-reported numbers, and several are single-author preprints.

## Findings at a glance

| Finding | Evidence | Evidence boundary |
|---|---|---|
| Developers act on few AI review comments | Five industrial and open-source studies: 1%–40% acted on | Metrics differ per study |
| Reviewers recall about 15–33% of known defects | Two 2026 benchmarks | Preprints, LLM judges |
| Context beyond the diff is the main miss | Two benchmarks | Adding context did not always help |
| AI comments over-index on style, under-index on correctness and security | Meta, 18,000 human reviews compared | One company |
| Filtering raises precision but drops real bugs | Three industrial studies and one vendor report | Company-specific data |
| More reviewers or passes: more bugs and more noise | Two benchmarks, two small preprints | **Contested** for different models |
| Self-correction without outside feedback is weak | Four studies, 2023–2025 | Code generation, not review |
| Execution feedback makes self-checking work | Two studies | Not tested for review comments |
| Short comments with code are acted on more | One study of GitHub review actions | Observational |

## 1. How useful AI review comments are

Each study measures usefulness differently, so the figures do not compare directly.

| Setting | Acted-on rate for AI comments | Comparison | Source |
|---|---|---|---|
| Mozilla and Ubisoft (RevMate) | 8.1% and 7.2% accepted | — | Olewicki et al. (2024) |
| 16 GitHub AI review actions | 0.9%–4.2% (file level), 6.5%–19.2% (hunk level) addressed | 60% for human comments | Sun, Kuang, et al. (2026) |
| Open-source agentic review | 16.6% of suggestions adopted | 56.5% for humans | Zhong et al. (2026) |
| Atlassian | 30%–40% resolved | — | Goldman et al. (2025) |
| Google AutoCommenter | About 40% resolved (offline estimate); 54% rated useful | Team target 80% | Vijayvergiya et al. (2024) |
| ByteDance BitsAI-CR | 75.0% precision; 26.7% of flagged Go code later changed | — | Sun, Xu, et al. (2025) |

Reviewers described rejected comments as superficial, obvious, generic, vague or wrong (Olewicki et al., 2024). Refactoring comments were accepted far more than functional ones in the same study. At Atlassian, comments on readability (43.3%), bugs (41.9%) and maintainability (36.2%) were resolved more than design comments (28.6%), and the authors attribute unresolved comments to lack of clarity, relevance and simplicity (Goldman et al., 2025). Google raised its useful rate from 54% to 66% by suppressing 17 non-actionable comment types (Vijayvergiya et al., 2024). Adopted AI suggestions increased code complexity and size more than adopted human ones (Zhong et al., 2026).

**AI reviewers focus on different things than humans.** In 18,000 human reviews at Meta, correctness was 44.4% of comments, code quality 19.2%, security 19.1% and best practices 7.2%. AI review comments were 25.5% correctness, 2.0% security and 30.8% best practices. "AI code review under-indexes on the themes humans value most while over-indexing on lower-priority concerns" (Maddila et al., 2026).

## 2. Defects found and missed

- On CR-Bench, the best agent recalled 32.76% of known defects, at 5.10% precision. Single-shot review with the same model recalled 27.01% at 3.56% precision (Pereira et al., 2026).
- On a benchmark built from human PR comments, eight frontier models found 15%–31% of the issues human reviewers flagged (Kumar, 2026). That study uses 100 PRs and no human baseline.
- On AACR-Bench, one model in agent mode reached 39.90% precision but 10.10% recall, against 8.70% precision with no context (L. Zhang et al., 2026). Agents posted 0.08–0.15 comments per patch.
- Running all existing review agents together solved about 40% of the tasks of a test-graded review benchmark (Y. Zhang et al., 2026).

**What they miss.** Agents found high-severity, performance and reliability defects more often, and low-severity, usability and functional-suitability defects least, the latter needing context beyond the diff. "Recall of memory issues is zero for all agents" (Pereira et al., 2026). Adding context did not reliably help: on one benchmark more context lowered detection for all eight models (Kumar, 2026), while on another, agent mode raised precision and lowered recall (L. Zhang et al., 2026).

For security review, LLMs outperformed static analysis tools, and reasoning models did better, but answers had vague wording and inaccurate code details. Detection was better in smaller files (Yu et al., 2026).

Human review is also not mainly about defects. In 570 review comments at Microsoft, code improvements were 29% and defects 14%, mostly simple logic errors (Bacchelli & Bird, 2013). About 75% of defects found in review concern evolvability rather than visible behaviour (Mäntylä & Lassenius, 2009; abstract only).

## 3. Noise and how to reduce it

Unfiltered LLM review output is dominated by nitpicks and hallucinated comments (Lu et al., 2025). Raw output did not reach production precision even after fine-tuning (Sun, Xu, et al., 2025).

| Technique | Effect | Cost | Source |
|---|---|---|---|
| Taxonomy of review rules guiding the model | Precision 16.83% → 57.03% | — | Sun, Xu, et al. (2025) |
| Second LLM pass that verifies comments | Precision 57.03% → 65.59% | — | Sun, Xu, et al. (2025) |
| Validator role re-checking comments | Fewer false alarms | Key bugs dropped (31.11 → 20.00) | Lu et al. (2025) |
| Context from program slices, line numbers inline | Best of the context options tested | — | Lu et al. (2025) |
| Bounded context, diff-only check that tries to refute each finding | 25.10% vs 11.57% SEM-F1 for the same model | — | Z. Li et al. (2026) |
| Static analysis plus LLM reasoning on alarms | 94%–98% of false alarms removed | Recall below the enterprise threshold | Du et al. (2026) |
| Reasoning before findings, specialised sub-agents | 51% fewer false positives | Vendor, self-reported | Sanglé-Ferrière (2025) |

**Verification trades recall for precision.** A validator role "improves precision by reducing false alarms", but the share of key bugs kept fell, so the authors warn against removing important bug-detecting comments (Lu et al., 2025). A vendor found that a verifier discarding findings it could not confirm removed real bugs, and changed it to discard only with a concrete refutation; its high-recall setting found 12 more of 136 known bugs and added 158 false positives (Malinosqui, 2026; vendor, low trust). Prompt tuning alone did not reduce noise in another vendor's report (Sanglé-Ferrière, 2025).

**LLM judges of review quality.** A judge detected hallucinated comments with F1 0.85, but agreed with developer preference only 67% of the time (Tantithamthavorn et al., 2026). LLMs also judge correct code as non-compliant with requirements, and prompts asking for explanations and fixes increase this. Running the original and the proposed fix against tests cut false rejections, for example from 54.8% to 16.3% on HumanEval (Jin & Chen, 2026).

## 4. Checking one's own work

### 4.1. Without outside feedback, self-checking is weak

- "Without external feedback", LLMs struggle to self-correct their reasoning and sometimes get worse (Huang et al., 2023).
- Models fail to fix errors in their own output that they fix when the same error is attributed to the user, a blind spot of 64.5% across 14 models. Appending "Wait" cut it by 89.3% (Tsui, 2025).
- Self-repair of code gives modest, inconsistent gains, limited by the model's ability to give feedback on its own code. Feedback from a stronger model or a human gives larger gains (Olausson et al., 2023).
- LLM evaluators score their own outputs higher than others' that humans rate as equal (Panickssery et al., 2024; Wataoka et al., 2024). This was tested on text, not code.

### 4.2. Execution feedback helps

Self-debugging with execution results and unit tests gave up to 12% accuracy gains, against 2–3% without tests (Chen et al., 2023). Tests the model writes itself carry its own bias; using intermediate runtime states reduced it (Chen, Tao, et al., 2025). A Reflexion-style re-review raised recall from 27.01% to 32.76% but cut the signal-to-noise ratio from 5.11 to 1.95 and lowered reviewers' usefulness scores (Pereira et al., 2026).

### 4.3. Not found: running code to verify review findings

No study compares running tests or reproducing a bug to verify a review finding with LLM-only verification. Cursor lists "letting Bugbot run code to verify its own bug reports" as future work, and its shipped pipeline used a validator model and majority voting across passes (Cursor, n.d.).

## 5. One reviewer or several (contested)

- Aggregating several independent reviews of the same PR raised F1 by up to 43.67% (Zeng et al., 2025).
- More reviewers raise key bug inclusion and false alarms together (Lu et al., 2025).
- With planted errors, a fresh-session same-model reviewer did not differ significantly in F1 from a top-tier different model; the two found partly different errors (Song, 2026). Single author, low trust.
- On one team's code, no single model exceeded about 64% recall, 56.5% of confirmed defects were found by exactly one model, and adding a second provider raised coverage from 33.6% to 57.1% (Stone, 2026). Single author, one organization; the author calls the conclusions "directional".

No study compares a reviewer that shares the author agent's context with a fresh-context reviewer.

## 6. Reporting findings

No study tested severity ranking, caps on the number of comments, or the format of suggested fixes. Observational evidence:

- Concise comments with code snippets were more likely to lead to code changes (Sun, Kuang, et al., 2026).
- Useful comments share vocabulary with the changed code and name relevant code elements (Rahman et al., 2018).
- Usefulness depends on comprehensible and polite wording as well as technical content, and falls as changes grow (Turzo & Bosu, 2023). *Unverified:* a Microsoft study is reported to find a lower share of useful comments on changes with more files (Bosu et al., 2015); its page could not be read in full.
- Meta's reviewer for AI-generated diffs triages the diff into classified, severity-ranked regions; it beat its baseline AI reviewer on Meta's own benchmark (Maddila et al., 2026).
- Inline comments can lose findings, because a comment must attach to a changed line (Malinosqui, 2026; vendor).

## 7. Reviewing agent-written pull requests

Human reviewers exchanged 11.8% more rounds on AI-generated code than on human code (Zhong et al., 2026). More reviewer comments go with lower merge odds for agent PRs but higher odds for human PRs (Yoshioka et al., 2026). Of 8,106 agent fix PRs, 65.0% merged; reviewers most often cited failing tests as the reason for not integrating, and some agent PRs were closed with no reviewer engagement (Alam et al., 2026). Meta states that agents generate code "at volumes that exceed the capacity of traditional peer review" (Maddila et al., 2026). No source measured reviewer time per agent PR.

## 8. Benchmarks and their limits

Benchmarks built from raw PR comments have noisy, incomplete labels: expert annotation raised the issues covered by one benchmark by 285% (L. Zhang et al., 2026). Review datasets remain noisy after heuristic cleaning (Liu et al., 2025; Ben Sghaier et al., 2025). BLEU agreed with human preference worse than chance, and direct LLM scoring only moderately (Zeng et al., 2025). Newer benchmarks score with an LLM judge, so the judge is part of the measurement, and several cover one language (L. Zhang et al., 2026). Production systems use proxies instead: ByteDance counts flagged code later changed, Google estimates resolution (Sun, Xu, et al., 2025; Vijayvergiya et al., 2024). AIDev provides 932,791 agent PRs for such studies (H. Li et al., 2026).

## 9. What the research could not find

- Any study of an agent reviewing its own diff before handing it to the user.
- A comparison of same-context self-review with fresh-context or different-model review.
- Execution-based verification of review findings on real PRs.
- Tests of severity ranking, comment caps, or suggested-fix formats.
- Security-specific recall on realistic PRs.
- Full texts of Bosu et al. (2015) and Beller et al. (2014) were blocked; Mäntylä and Lassenius (2009) was read as abstract only. Vendor benchmarks (Qodo, Martian, Greptile) were seen only in search results and not used.

Open question (low priority): which false-positive thresholds practitioners report, from primary sources.

The research board is in `.research/code-better-review/`.

## References

Alam, K., Mondal, S., & Roy, B. (2026). *Why are AI agent involved pull requests (fix-related) remain unmerged? An empirical study*. arXiv. https://arxiv.org/abs/2602.00164

Bacchelli, A., & Bird, C. (2013). Expectations, outcomes, and challenges of modern code review. In *Proceedings of the 35th International Conference on Software Engineering (ICSE 2013)*. https://web.eecs.umich.edu/~weimerw/2018-481/readings/codereview.pdf

Ben Sghaier, O., Weyssow, M., & Sahraoui, H. (2025). *Harnessing large language models for curated code reviews*. arXiv. https://arxiv.org/abs/2502.03425

Bosu, A., Greiler, M., & Bird, C. (2015). Characteristics of useful code reviews: An empirical study at Microsoft. In *Proceedings of the 12th Working Conference on Mining Software Repositories*. IEEE. https://www.microsoft.com/en-us/research/publication/characteristics-of-useful-code-reviews-an-empirical-study-at-microsoft/

Chen, X., Lin, M., Schärli, N., & Zhou, D. (2023). *Teaching large language models to self-debug*. arXiv. https://arxiv.org/abs/2304.05128

Chen, X., Tao, Z., Zhang, K., Zhou, C., Gu, W., He, Y., Zhang, M., Cai, X., Zhao, H., & Jin, Z. (2025). *Revisit self-debugging with self-generated tests for code generation*. arXiv. https://arxiv.org/abs/2501.12793

Cursor. (n.d.). *Building a better Bugbot*. Cursor blog. https://cursor.com/blog/building-bugbot

Du, X., Feng, J., Zou, Y., Xu, W., Ma, J., Zhang, W., Liu, S., Peng, X., & Lou, Y. (2026). *Reducing false positives in static bug detection with LLMs: An empirical study in industry*. arXiv. https://arxiv.org/abs/2601.18844

Goldman, S., Lin, H. Y., Pasuksmit, J., Thongtanunam, P., Tantithamthavorn, K., Wang, Z., Zhang, R., Behnaz, A., Jiang, F., Siers, M., Jiang, R., Buller, M., Jeong, M., & Wu, M. (2025). *What types of code review comments do developers most frequently resolve?* arXiv. https://arxiv.org/abs/2510.05450

Huang, J., Chen, X., Mishra, S., Zheng, H. S., Yu, A. W., Song, X., & Zhou, D. (2023). *Large language models cannot self-correct reasoning yet*. arXiv. https://arxiv.org/abs/2310.01798

Jin, H., & Chen, H. (2026). *Are LLMs reliable code reviewers? Systematic overcorrection in requirement conformance judgement*. arXiv. https://arxiv.org/abs/2603.00539

Kumar, D. (2026). *SWE-PRBench: Benchmarking AI code review quality against pull request feedback*. arXiv. https://arxiv.org/abs/2603.26130

Li, H., Zhang, H., & Hassan, A. E. (2026). *AIDev: Studying AI coding agents on GitHub*. arXiv. https://arxiv.org/abs/2602.09185

Li, Z., Zhang, L., Wu, X., Zhuang, Z., Xu, Y., Wang, B., Zhu, S., Wang, C., Zhao, P., Zheng, X., & Rong, G. (2026). *OpenCodeReview: Determinism over non-determinism for cost-effective agent-based code review*. arXiv. https://arxiv.org/abs/2608.09290

Liu, C., Lin, H. Y., & Thongtanunam, P. (2025). *Too noisy to learn: Enhancing data quality for code review comment generation*. arXiv. https://arxiv.org/abs/2502.02757

Lu, J., Jiang, L., Li, X., Fang, J., Zhang, F., Yang, L., & Zuo, C. (2025). *Towards practical defect-focused automated code review*. arXiv. https://arxiv.org/abs/2505.17928

Maddila, C., Rashik, M., Khan, E. M., Jha, S., Saindon, J., Nagappan, N., & Rigby, P. C. (2026). *From code review to code critique: Intent, drift, and spotlight for AI-generated diffs at scale*. arXiv. https://arxiv.org/abs/2607.29516

Malinosqui, G. (2026, August 18). *We ran 20 experiments to improve AI code review recall*. Kodus blog. https://kodus.io/en/ai-code-review-recall/

Mäntylä, M. V., & Lassenius, C. (2009). What types of defects are really discovered in code reviews? *IEEE Transactions on Software Engineering, 35*(3). https://mmantyla.github.io/wiki/What+Types+of+Defects+Are+Really+Discovered+in+Code+Reviews%253F.html

Olausson, T. X., Inala, J. P., Wang, C., Gao, J., & Solar-Lezama, A. (2023). *Is self-repair a silver bullet for code generation?* arXiv. https://arxiv.org/abs/2306.09896

Olewicki, D., Da Silva, L., Mujahid, S., Amini, A., Mah, B., Castelluccio, M., Habchi, S., Khomh, F., & Adams, B. (2024). *Impact of LLM-based review comment generation in practice: A mixed open-/closed-source user study*. arXiv. https://arxiv.org/abs/2411.07091

Panickssery, A., Bowman, S. R., & Feng, S. (2024). *LLM evaluators recognize and favor their own generations*. arXiv. https://arxiv.org/abs/2404.13076

Pereira, K., Sinha, N., Ghosh, R., & Dutta, D. (2026). *CR-Bench: Evaluating the real-world utility of AI code review agents*. arXiv. https://arxiv.org/abs/2603.11078

Rahman, M. M., Roy, C. K., & Kula, R. G. (2018). *Predicting usefulness of code review comments using textual features and developer experience*. arXiv. https://arxiv.org/abs/1807.04485

Sanglé-Ferrière, P. (2025, June 19). *Learnings from building AI agents*. cubic blog. https://www.cubic.dev/blog/learnings-from-building-ai-agents

Song, T.-E. (2026). *When does a second model help? Cross-model review in LLM verification*. arXiv. https://arxiv.org/abs/2610.01471

Stone, T. (2026). *A single LLM is an incomplete code reviewer: Evidence that independent review by multiple LLM families recovers code defects any one model misses* [Preprint]. Zenodo. https://doi.org/10.5281/zenodo.20519585

Sun, K., Kuang, H., Baltes, S., Zhou, X., Zhang, H., Ma, X., Rong, G., Shao, D., & Treude, C. (2026). *Does AI code review lead to code changes? A case study of GitHub Actions*. arXiv. https://arxiv.org/abs/2508.18771

Sun, T., Xu, J., Li, Y., Yan, Z., Zhang, G., Xie, L., Geng, L., Wang, Z., Chen, Y., Lin, Q., Duan, W., & Sui, K. (2025). *BitsAI-CR: Automated code review via LLM in practice*. arXiv. https://arxiv.org/abs/2501.15134

Tantithamthavorn, K., Lin, H. Y., Thongtanunam, P., Charoenwet, W., Jeong, M., & Wu, M. (2026). *HalluJudge: A reference-free hallucination detection for context misalignment in code review automation*. arXiv. https://arxiv.org/abs/2601.19072

Tsui, K. (2025). *Self-Correction Bench: Uncovering and addressing the self-correction blind spot in large language models*. arXiv. https://arxiv.org/abs/2507.02778

Turzo, A. K., & Bosu, A. (2023). What makes a code review useful to OpenDev developers? An empirical investigation. *Empirical Software Engineering*. https://arxiv.org/abs/2302.11686

Vijayvergiya, M., Salawa, M., Budiselić, I., Zheng, D., Lamblin, P., Ivanković, M., Carin, J., Lewko, M., Andonov, J., Petrović, G., Tarlow, D., Maniatis, P., & Just, R. (2024). AI-assisted assessment of coding practices in modern code review. In *Proceedings of the 1st ACM International Conference on AI-Powered Software (AIware '24)*. https://arxiv.org/abs/2405.13565

Wataoka, K., Takahashi, T., & Ri, R. (2024). *Self-preference bias in LLM-as-a-judge*. arXiv. https://arxiv.org/abs/2410.21819

Yoshioka, H., Monno, T., Tokumasu, H., Wakamatsu, T., Ota, Y., Weeraddana, N., & Matsumoto, K. (2026). *Let's make every pull request meaningful: An empirical analysis of developer and agentic pull requests*. arXiv. https://arxiv.org/abs/2601.18749

Yu, J., Liang, P., Fu, Y., Tahir, A., Shahin, M., Wang, C., & Cai, Y. (2026). *An insight into security code review with LLMs: Capabilities, obstacles, and influential factors*. arXiv. https://arxiv.org/abs/2401.16310

Zeng, Z., Shi, R., Han, K., Li, Y., Sun, K., Wang, Y., Yu, Z., Xie, R., Ye, W., & Zhang, S. (2025). *SWR-Bench: Assessing LLM performance in real-world code review comment generation*. arXiv. https://arxiv.org/abs/2509.01494

Zhang, L., Yu, Y., Yu, M., Guo, X., Zhuang, Z., Rong, G., Shao, D., Shen, H., Kuang, H., Li, Z., Wang, B., Zhang, G., Xiang, B., & Xu, X. (2026). *AACR-Bench: Evaluating automatic code review with holistic repository-level context*. arXiv. https://arxiv.org/abs/2601.19494

Zhang, Y., Pan, Z., Yusuf, I. N. B., Ruan, H., Shariffdeen, R., & Roychoudhury, A. (2026). *Code review agent benchmark*. arXiv. https://arxiv.org/abs/2603.23448

Zhong, S., Noei, S., Zou, Y., & Adams, B. (2026). *Human-AI synergy in agentic code review*. arXiv. https://arxiv.org/abs/2603.15911
