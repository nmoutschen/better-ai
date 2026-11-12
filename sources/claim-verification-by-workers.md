# Verifying claims with separate worker agents

Research findings · Search date: 12 November 2026

A research coordinator does not need to open source pages to verify claims. Separate, cheaper verifier agents can do it, if each verifier checks claims it did not record, opens the page itself, copies the passage the claim rests on, and judges the claim from that passage. On average, cheap and frontier models judge whether a passage supports a claim about equally well. All models accept passages on the same topic that do not state the claim. All models miss changed numbers and wrong locations more often than other errors. Reading only the claims a verifier flags misses what it did not flag. **No study tests this exact design;** the findings come from citation-judge benchmarks, fact-verification studies, multi-agent ablations, and one test run on this research's own board (section 7).

**Scope.** Who should check that a claim's quote is on its source page, supports the claim, and answers its question, in a coordinator-and-worker research workflow; with which model tier; and what the coordinator still checks. The user had already chosen verifier agents over string matching. The goal is to decide how `/research-better` section 7.2 and its templates run verification.

**Status.** No high- or medium-priority question is open. Four questions are contested (sections 1 and 2), and four found nothing, including the two challenge questions on verifier designs (section 3). Seven Sonnet workers and one coordinator ran the research: 33 questions, 69 sources, 124 claims. Four Haiku verifiers checked every claim with the design this report proposes. 87 claims were verified and 37 unverified. The coordinator narrowed 6 claims to match their passage and used only verified claims below. Almost all sources are 2024–2026 preprints. The research board is in `.research/claim-verification-by-workers/`.

## 1. Cheap verifiers judge support about as well as frontier ones, on average

- Eight judges from three model families, cheap to frontier, were statistically indistinguishable on factual support of deep-research citations, and judge cost did not predict accuracy (Leung et al., 2026).
- A 770M fine-tuned checker reached Claude-3 Opus level and came close to GPT-4 on grounding verification (Tang et al., 2024).
- Fine-tuned 1B and 4B checkers scored 75.7–78.1 balanced accuracy on the same benchmark, level with the GPT-4o and Claude 3.5 Sonnet scores on its leaderboard (Rao et al., 2026; Bergeron et al., 2025).

**Challenge (contested).** On the 378 hard cases where the reference judges disagreed, no judge reliably matched the human label, and the model rankings changed (Leung et al., 2026). At equal F1, judges differed in how often they accepted a bad citation. In 2023, ChatGPT and 7–13B open models trailed GPT-4 by a wide margin as zero-shot attribution judges (Yue et al., 2023). Small checkers fail on multi-step reasoning, arithmetic and long inputs (Seo et al., 2026; Rao et al., 2026). None of these studies scores current frontier models against current cheap models on a quote-from-page task.

**What this means for the skill:** the cheaper worker model can verify. The coordinator still checks the claims where verifiers are weak: numbers the passage does not state.

## 2. The verifier should not be the agent that recorded the claim

LLM judges rate their own output higher than humans do. GPT-4 recognized its own text 73.5% of the time, and showed significant self-preference (Panickssery et al., 2024; Wataoka et al., 2024). GPT-4o and Claude 3.5 Sonnet rated their own and same-family output higher after controlling for quality (Spiliopoulou et al., 2025). Without outside feedback, models fail to correct their own reasoning (Huang et al., 2023).

**Challenge (contested).** In a grounded test, where the judge sees the source and must find an injected contradiction, a judge from the same model as the generator was not measurably better or worse (Selvam & Ghosh, 2026). Errors of different models are correlated, so a different model does not catch all of the author's errors (Kim et al., 2025; Kohli, 2026). In two multi-agent ablations, a separate verifier added nothing or made results worse: an independent reviewer gave no detectable gain (Schneppen et al., 2026; abstract only), and verifier agents approved 49% of submissions that failed a deterministic grader (Kim et al., 2026). The first study concludes that a verifier helps in proportion to the information it holds that the generator did not.

**What this means for the skill:** a separate context removes the author's bias toward its own work. It is not enough on its own. The verifier must bring new information, which here is the source page it reads itself.

## 3. What makes a verifier miss errors, and which designs help

**Failure modes:**
- A judge that sees only search snippets wrongly rejects true claims and accepts false ones (Fan et al., 2026).
- LLM fact-checkers output "supports" for passages that share the claim's topic but do not state it (Dey & Collomosse, 2026).
- Given the right legal document, models caught 93–100% of citations to the wrong case, but only 37–61% of citations to the wrong page in court opinions and 52–83% in briefs. They accepted the citation on topical overlap. GPT-5.4 with high reasoning effort still missed 40% of wrong-page citations in court opinions (Verma, 2026).
- Changing numbers in claims or evidence cut the accuracy of leading models by up to 62% (Aarnes & Setty, 2025).
- An NLI-based verifier, TRUE T5, handled full support well but struggled when a document supported a claim only in part (Wojtasik et al., 2025).

**Designs that helped:**
- A judge that fetched full-text sources agreed with human consensus 87.9% of the time, against 92.5% between two humans (Fan et al., 2026).
- Splitting the judgement into sub-checks raised accuracy by 7.6–10.0 points on rubrics that required checking evidence (Qi et al., 2026).
- Re-scoring extracted passages against the full claim recovered accuracy lost to naive claim decomposition (Dey & Collomosse, 2026). Plain decomposition gave inconsistent results (Hu et al., 2024).
- Locating the 5 most relevant sentences and then judging found 51% of erroneous citations, against 25% when the whole reference was pasted in (Sarol et al., 2025; conference abstract; human agreement on accuracy was only κ = 0.31).

**Challenge.** Asking the verifier to check support at the cited page raised recall but also false positives (Verma, 2026). Verification accuracy of open models generally fell as the input grew, and evidence placed in the middle of the input was verified less accurately, with exceptions such as Qwen3 (Bernardelle et al., 2026). No study tests a verifier that copies the supporting passage against injected near-miss errors.

**What this means for the skill:** the verifier opens the page itself, locates the passage, copies it, and judges from the copy, checking each number and qualifier. Topical overlap is not support. Partial support is not support. These rules combine the designs above; the combination is a design choice.

## 4. Who reviews after the verifier

A cheap judge used first, with escalation to a stronger judge only when its confidence is low, kept a guaranteed level of human agreement (Jung et al., 2024). Small judges' confidence was anti-calibrated, higher on errors (Qi et al., 2026), so a cheap verifier's confidence is a weak escalation signal. Clinicians who rely on decision-support systems make errors of omission: they fail to act because the system did not prompt them (Goddard et al., 2012). People who felt accountable for how they used an automated aid checked it more and made fewer automation errors (Mosier et al., 1996; abstract only).

No study measures how many errors are missed when only a verifier's flags are reviewed.

**What this means for the skill:** the coordinator reads every unverified claim's reason. For each verified claim the conclusion depends on, it compares the claim with the passage the verifier copied. This costs a short passage per claim, not a page. The coordinator opens the page only when the passage does not settle the question.

## 5. How often research agents' citations are wrong

- Deep-research systems' citation accuracy ranged from 40% to 80% (Venkit et al., 2025).
- In generative search engines, 74.5% of citations supported their sentence, and only 51.5% of sentences were fully supported (Liu et al., 2023).
- For GPT-4o with web search on medical questions, about 30% of statements were unsupported (Wu et al., 2025).
- In a biomedical corpus written by humans, 39.18% of 3,063 citations had accuracy errors, and few-shot GPT-4 found erroneous citations less well than accurate ones (Sarol et al., 2024).

No study reports how often a research agent's verbatim quote is absent from its page. Every claim needs checking, not a sample.

## 6. Cost

Multi-agent research uses about 15 times the tokens of a chat (Anthropic, 2025). A 770M checker matched GPT-4 accuracy at over 400 times lower cost (Tang et al., 2024). Cascades that escalate only uncertain items cut judge cost by up to 87.4% at a guaranteed agreement level (Jung et al., 2024). Restricting the verifier's input to retrieved passages cut verification token cost by over 80% with no loss of accuracy (Han et al., 2026). No study reports verification's share of tokens in a research pipeline.

## 7. A test of the design on this board

The design was run on this research's own 124 claims, with four Haiku verifiers and the brief now in `templates/verifier-brief.md`. This is one run on one board, with no human labels. It shows how the design behaves, not how accurate it is.

| Measure | Result |
|---|---|
| Claims checked | 124: 87 verified, 37 unverified |
| Verifier tokens | about 785,000 on Haiku, about 6,300 per claim |
| Quote matched page text exactly, but verifier rejected the claim | 23 of 90: the claim added an inference, widened the scope, or did not answer its question |
| Verifier verified the claim, but the quote did not match exactly | 20 of 87: hyphens, ligatures, line breaks, table layout |
| Coordinator comparison of ~35 verified key claims with their copied passages | no disagreement |
| Coordinator reading of 20 unverified reasons | most were real overreach; about 3 looked too strict |
| Problems in the run | one verifier wrote to a claim another verifier held; 75 claims were marked `hard`, because the definition was too broad |

String matching would have accepted the 23 claims that overstate their source, and rejected or sent for review the 20 correct claims that did not match exactly. This supports the user's decision against mechanical quote matching. The brief now tells verifiers to re-read the checker line before writing, and narrows `hard` to numbers the passage does not state.

## 8. What changes in `/research-better`

| Change | Section |
|---|---|
| New `templates/verifier-brief.md`: separate agent, opens the page, copies the passage, judges found, supports and answers from it, names partial support, checks source fields | 2, 3 |
| Board claims gain `checker`, `span`, `hard` and `reason` lines | 3, 4 |
| 7.1: the coordinator starts verifiers on the workers' cheaper model, as claims accumulate | 1, 2, 6 |
| 7.2 step 1: the coordinator does not open pages to verify. It reads unverified reasons, compares verified key claims with their passage, and checks numbers in `hard` claims | 4, 7 |
| 8: a missing source field goes to a verifier, not to the coordinator | 6 |

## 9. Open questions and gaps

- **Not found:** a verifier that copies the passage, tested against injected near-miss quotes; the share of errors missed when only flags are reviewed; how often string matching rejects correct quotes, outside this board; cheap verifiers from different model families compared on claim support.
- **Thin everywhere:** most sources are 2026 preprints. No study uses web pages read by an agent, the setting of this skill.

## References

Aarnes, P. R., & Setty, V. (2025). *NumPert: Numerical perturbations to probe language models for veracity prediction* (arXiv:2511.09971). arXiv. https://arxiv.org/pdf/2511.09971

Anthropic. (2025, June 13). *How we built our multi-agent research system*. Anthropic Engineering. https://www.anthropic.com/engineering/multi-agent-research-system

Bergeron, L., Buhnila, I., François, J., & State, R. (2025). *HalluGuard: Evidence-grounded small reasoning models to mitigate hallucinations in retrieval-augmented generation* (arXiv:2510.00880). arXiv. https://arxiv.org/pdf/2510.00880

Bernardelle, P., Civelli, S., Roitero, K., & Demartini, G. (2026). *Context shapes LLMs retrieval-augmented fact-checking effectiveness* (arXiv:2602.14044). arXiv. https://arxiv.org/pdf/2602.14044

Dey, A. U., & Collomosse, J. (2026). *The warrant gap: Claim-conditioned re-scoring for fact-checking*. arXiv. https://arxiv.org/html/2606.24627

Fan, D., Delsad, S., Flammarion, N., Andriushchenko, M., et al. (2026). *HalluHard: A hard multi-turn hallucination benchmark*. arXiv. https://arxiv.org/html/2602.01031

Goddard, K., Roudsari, A., & Wyatt, J. C. (2012). Automation bias: A systematic review of frequency, effect mediators, and mitigators. *Journal of the American Medical Informatics Association*. https://pmc.ncbi.nlm.nih.gov/articles/PMC3240751/

Han, J., Kim, H., Lee, C., Lee, D., Park, M. H., Song, H., Choi, S. J., Lee, M., & Lee, H. (2026). *DEER: A benchmark for evaluating deep research agents on expert report generation* (arXiv:2512.17776). arXiv. https://arxiv.org/pdf/2512.17776

Hu, Q., Long, Q., & Wang, W. (2024). *Decomposition dilemmas: Does claim decomposition boost or burden fact-checking performance?* arXiv. https://arxiv.org/html/2411.02400

Huang, J., Chen, X., Mishra, S., Zheng, H. S., Yu, A. W., Song, X., & Zhou, D. (2023). *Large language models cannot self-correct reasoning yet* (arXiv:2310.01798). arXiv. https://arxiv.org/html/2310.01798v1

Jung, J., Brahman, F., & Choi, Y. (2024). *Trust or escalate: LLM judges with provable guarantees for human agreement* (arXiv:2407.18370). arXiv. https://arxiv.org/pdf/2407.18370

Kim, E., Garg, A., Peng, K., & Garg, N. (2025). *Correlated errors in large language models* (arXiv:2506.07962). arXiv. https://arxiv.org/pdf/2506.07962

Kim, Y., Park, C., Kim, T., et al. (2026). *TeamBench: Evaluating agent coordination under enforced role separation* (arXiv:2605.07073). arXiv. https://arxiv.org/pdf/2605.07073

Kohli, G. (2026). *Nine judges, two effective votes: Correlated errors undermine LLM evaluation panels* (arXiv:2605.29800). arXiv. https://arxiv.org/pdf/2605.29800

Leung, E., Lumer, E., Feld, C., Huber, A., Subbiah, V. K., & Paul, K. (2026). *Do you need a frontier model as a citation verifier? Benchmarking rubric LLMs for deep-research source attribution* (arXiv:2607.08700). arXiv. https://arxiv.org/html/2607.08700

Liu, N. F., Zhang, T., & Liang, P. (2023). *Evaluating verifiability in generative search engines* (arXiv:2304.09848). arXiv. https://arxiv.org/pdf/2304.09848

Mosier, K. L., Skitka, L. J., Burdick, M. R., Heers, S. T., & Rosekind, M. R. (1996, November 2). *Decision making in a high-tech world: Automation bias and countermeasures*. NASA Technical Reports Server. https://ntrs.nasa.gov/api/citations/20020041010

Panickssery, A., Bowman, S. R., & Feng, S. (2024). *LLM evaluators recognize and favor their own generations* (arXiv:2404.13076). arXiv. https://arxiv.org/html/2404.13076v1

Qi, J., Dantsev, D., & Sun, M. (2026). *VERDI: Single-call confidence estimation for verification-based LLM judges via decomposed inference*. arXiv. https://arxiv.org/html/2605.11334

Rao, D., Han, F., & Callison-Burch, C. (2026). *ThinknCheck: Grounded claim verification with compact, reasoning-driven, and interpretable models* (arXiv:2604.01652). arXiv. https://arxiv.org/pdf/2604.01652

Sarol, M. J., Schneider, J., & Kilicoglu, H. (2025). *Leveraging large language models for detecting citation quotation errors in biomedical literature* [Conference abstract]. International Congress on Peer Review and Scientific Publication. https://peerreviewcongress.org/abstract/leveraging-large-language-models-for-detecting-citation-quotation-errors-in-biomedical-literature/

Sarol, M. J., Ming, S., Radhakrishna, S., Schneider, J., & Kilicoglu, H. (2024). Assessing citation integrity in biomedical publications: Corpus annotation and NLP models. *Bioinformatics*. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11231046/

Schneppen, N., Li, M. M., & Ritz, E. (2026). *Verification without privilege: Information, not architecture, corrects multi-agent errors* [Workshop abstract]. NeurIPS 2026 Workshop "Who Verifies the Agents?". https://neurips.cc/virtual/2026/172892

Selvam, S., & Ghosh, A. (2026). *Eval-Pair Matrix: Answer-paired meta-evaluation of LLM judges for grounded RAG* (arXiv:2607.10626). arXiv. https://arxiv.org/pdf/2607.10626

Seo, W., Han, S., Jung, J., et al. (2026). *Verifying the verifiers: Unveiling pitfalls and potentials in fact verifiers*. arXiv. https://arxiv.org/html/2506.13342

Spiliopoulou, E., Fogliato, R., Burnsky, H., Soliman, T., Ma, J., Horwood, G., & Ballesteros, M. (2025). *Play favorites: A statistical method to measure self-bias in LLM-as-a-judge* (arXiv:2508.06709). arXiv. https://arxiv.org/html/2508.06709v1

Tang, L., Laban, P., & Durrett, G. (2024). *MiniCheck: Efficient fact-checking of LLMs on grounding documents* (arXiv:2404.10774). arXiv. https://arxiv.org/pdf/2404.10774

Venkit, P. N., Laban, P., Zhou, Y., Huang, K.-H., et al. (2025). *DeepTRACE: Auditing deep research AI systems for tracking reliability across citations and evidence* (arXiv:2509.04499). arXiv. https://arxiv.org/pdf/2509.04499

Verma, A. (2026). *Is this citation on point?* (arXiv:2608.12571). arXiv. https://arxiv.org/pdf/2608.12571

Wataoka, K., Takahashi, T., & Ri, R. (2024). *Self-preference bias in LLM-as-a-judge* (arXiv:2410.21819). arXiv. https://arxiv.org/html/2410.21819v1

Wu, K., Wu, E., Wei, K., Zhang, A., Casasola, A., Nguyen, T., Riantawan, S., Shi, P., Ho, D., & Zou, J. (2025). An automated framework for assessing how well LLMs cite relevant medical references. *Nature Communications, 16*, 3615. https://pmc.ncbi.nlm.nih.gov/articles/PMC12003634/

Wojtasik, K., Dolega, T., & Piasecki, M. (2025). CiteVerifier: How good are citation verifiers and how to use them? *ICCS 2025*. https://www.iccs-meeting.org/archive/iccs2025/papers/159110235.pdf

Yue, X., Wang, B., Chen, Z., Zhang, K., Su, Y., & Sun, H. (2023). *Automatic evaluation of attribution by large language models* (arXiv:2305.06311). arXiv. https://arxiv.org/pdf/2305.06311
