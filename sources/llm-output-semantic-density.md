# Making LLM output more semantically dense

Research findings · Search date: 8 November 2026

**Scope.** How to make text, and especially LLM output, carry more information per word without losing meaning or accuracy. Covers how much padding LLM output contains and what form it takes, why models pad, methods that raise density (prompting, training, editing), what content must survive cutting, how readers respond to dense text, and how density is measured. These findings are input for writing rules for AI agents, such as the write-better skill. This report does not write those rules.

**Status.** Fifteen questions are closed: fourteen answered and one contested (section 7). No question is open. 53 of 54 claims were checked against their source pages; the one unchecked claim is left out of this report. Most evidence comes from 2023–2026 arXiv preprints, from short-answer or math tasks, and from model behaviour rather than human readers. Several findings rest on one study.

**Cutting padding is well supported. Cutting content is not.** Studies agree that LLM answers often contain removable parts: a restated question, a preamble, generic caveats, formatting wrappers, or a list of possible answers. But instructions to "be brief" can remove content readers need, and packing in more information helps readers only up to about the density of human writing. For writing rules, "cut these specific parts" has support, while "be concise" or "be dense" applied to everything does not.

## Findings at a glance

| Question | What the evidence shows | Evidence boundary |
| --- | --- | --- |
| Is LLM output padded? | All 14 models tested produced compressible answers on all 5 datasets. Excess length varies tenfold across 76 models. | Short-answer prompts with one correct answer. |
| Why? | Preference training rewards length; reward models pick up a length bias from preference data. | One main study; pretraining and fine-tuning data not studied. |
| Do brevity prompts keep accuracy? | Often yes for reasoning on math in large models given examples. No for final answers to false-premise questions. | No study tests these factors against each other. |
| Does training for brevity work? | Reasoning cut by 50–70% with accuracy kept. | One study reports lost explanatory context. Math reasoning only. |
| What must survive cutting? | Rebuttals of false premises, explanatory context, calibrated first-person hedges. | Each rests on one study. |
| Do readers benefit from denser text? | Preferred up to about human-written density, then readability drops. Denser text slows reading. | Few studies; none compares dense and padded LLM answers. |
| Do common editing tips help comprehension? | Avoiding nominalisations and passives: no comprehension difference in the one controlled test. | 27 students, 4 texts. |

## 1. How much padding LLM output contains

**Padding is common and varies a lot between models.**

- Zhang et al. (2024) tested 14 models on five question-answering datasets. They define *verbosity compensation* as "generating responses that can be compressed without information loss when prompted to respond concisely". All 14 models showed it on all five datasets. The abstract gives GPT-4 a rate of 50.40%; the paper's tables show this is GPT-4o on one dataset (NarrativeQA). GPT-4o's average across the five datasets is 29.39%.
- Borisov et al. (2026) built YapBench, a benchmark of prompts where a minimal answer is enough. Across 76 chat models, median excess length varied by an order of magnitude.
- Poddar et al. (2025) report that 12 models across 5 datasets often produce answers "substantially longer than necessary", with redundant or additional information beyond the minimal answer. Only the abstract could be read.

**Forms of padding the sources name:**

- restating the question (Zhang et al., 2024)
- listing several answers in a row to cover the right one (Zhang et al., 2024)
- vague answers that avoid answering precisely (Zhang et al., 2024)
- extra detail or format symbols (Zhang et al., 2024)
- headings, prose, or duplicated code blocks around a one-line command (Borisov et al., 2026)
- boilerplate preambles and generic caveats (Borisov et al., 2026)
- *vacuum-filling*: long unrequested help on low-information prompts, where one clarifying question would do (Borisov et al., 2026)

**Padding tracks lower accuracy.** Padded answers were less accurate than concise ones in most models and datasets. The largest gap was 27.61% (llama3-70b on Qasper), and the authors report that the gap does not shrink as models become more capable. Padded answers also showed higher model uncertainty on all five datasets (Zhang et al., 2024). This is a correlation; the study does not show that uncertainty causes padding.

**Limit.** YapBench defines removable text only for prompts with one stable short answer, and excluded other prompts (Borisov et al., 2026). No source measures how much of an open-ended answer is filler.

## 2. Why models pad

The best-supported cause is preference training (RLHF), the step where a reward model learns which answers people prefer.

- Singhal et al. (2023) found that reward gains during RLHF were "largely driven by increasing response length". A reward based on length alone reproduced most of the improvement over the fine-tuned model. They identify reward models as the main source of the bias, because reward models are "easily influenced by length biases in preference data".
- LLMs used as judges also favour longer answers (Hu et al., 2025), which affects evaluations that rely on them.

**Not found.** No source tested whether pretraining data or supervised fine-tuning data causes padding. The claim that human annotators are the origin of the preference bias was seen only in a search snippet and is not used.

## 3. Methods that raise density

### 3.1. Prompting

| Method | Reported result | Cost or limit |
| --- | --- | --- |
| Constrained-CoT: limit reasoning to a word count | LLaMA2-70b on GSM8K: accuracy 36.01% → 41.07% with a 100-word limit, 28 fewer words on average (Nayab et al., 2024) | Reasoning only, not the final answer |
| Chain of Draft: minimal notes instead of full reasoning steps | Matched or beat step-by-step reasoning with as little as 7.6% of the tokens (Xu et al., 2025) | Without examples, Claude 3.5 Sonnet scored 65.5% vs 90.4% on GSM8K. Llama 3.2 3B scored 52.5% vs 70.7%. |
| Concise chain of thought | Length −48.70% for GPT-3.5 and GPT-4, negligible effect overall (Renze & Guven, 2024) | GPT-3.5 lost 27.69% on math problems |
| Chain of Density: iteratively add missing entities to a fixed-length summary | Readers preferred denser summaries, up to about the density of human-written summaries (Adams et al., 2023) | The authors report "a tradeoff between informativeness and readability" |

Lee et al. (2025) found a general trade-off between reasoning length and accuracy. Each problem has a minimum number of tokens needed to solve it ("token complexity"), and prompt-based compression stays far from that minimum.

### 3.2. Training

- DLER, a reinforcement-learning method with a simple length penalty, cut reasoning length by over 70% while beating previous baselines on accuracy (Liu et al., 2025).
- AALC, a length reward that adapts to accuracy, cut response length by over 50% on math benchmarks while keeping or improving accuracy (Li et al., 2025). The authors note that "models trained with AALC omit some narrative framing and explanatory context."

Both results cover reasoning chains on math, not final answers for readers. No source studied decoding-time methods, which change how the model picks each next word.

### 3.3. Editing after generation

- Zhang et al. (2024) replaced padded answers with answers generated by another model. This cut Mistral's padding rate on Qasper from 63.81% to 16.16%.
- Automatic editing of LLM text "show[s] promise in improving alignment between LLM-generated and human-written text", although experts preferred edits by other experts (Chakrabarty et al., 2024). This was tested on creative writing, not on density.

## 4. What content must survive cutting

| Usually safe to cut on simple requests | Carries information readers use |
| --- | --- |
| Restated question, boilerplate preamble, formatting wrappers, unrequested explanation, vacuum-filling help (Borisov et al., 2026) | **Rebuttal of a false premise.** Asked to "answer the question briefly", 11 of 17 models got worse at rejecting misinformation, by up to 20% (Le Jeune et al., 2025). |
| | **Explanatory context.** The length-trained models in Li et al. (2025) lost it. |
| | **Calibrated first-person hedges.** In a pre-registered study (N=404, medical questions), "I'm not sure, but…" lowered agreement with the system and raised participants' accuracy (Kim et al., 2024). |

Le Jeune et al. (2025) explain the false-premise result as a lack of room: rejecting false content needs "nuance or justification". They checked whether LLM judges' preference for longer answers explained the drop and found the same judge error rate (3 of 50) with and without brevity instructions. A news report on the same study says the size of the drop varied by model (Bastian, 2025).

**Generic caveats: the evidence is split.** In one preprint, 69% of 300 users said they preferred a confident falsehood over an LLM admitting it did not know (Bar-Or Nirman et al., 2024). That measures stated preference, and the preprint is low-trust. No source tested boilerplate caveats separately from calibrated hedges.

## 5. How readers respond to dense text

The evidence on human readers is thin.

- Older adults spent more time reading sentences that pack in more ideas, and they allocated that time effectively (Stine & Hindman, 1994).
- Students scored higher after a lecture with lower idea density than after a denser one (n=75, median 7 vs 6, p=0.04). Second-language English speakers gained more (Lunn et al., 2021).
- Readers preferred summaries up to about human-written density, with readability falling beyond that point (Adams et al., 2023).
- Uneven spread of information across a sentence predicted lower acceptability ratings (Meister et al., 2021).
- One preprint reports that users "overwhelmingly prefer concise, source-attributed responses over elaborate explanations" in AI search (Esposito, 2025). Concision is confounded with source attribution, and the study is low-trust.

**Common editing advice has little support.** A medical-writing editorial recommends cutting nominalisations (verbs turned into nouns) and passive voice, saying this shortens text by up to 30% and improves clarity (Lang, 2017). The only controlled test found had 27 students read 4 texts under eye-tracking. It found "no difference between recommended and problem constructions" in comprehension (Balling, 2018). Balling hypothesises that what matters is "how the linguistic manipulations support cohesion and coherence in the text."

**Not found.** No controlled study compares how readers understand or trust dense versus padded LLM answers. No controlled study tests deleting redundancy or hedges from human-written text.

## 6. How density is measured

**Text density.** Ji et al. (2023) use four criteria:

- **surprisal**: how unexpected each word is in context
- **entropy**: how uncertain the next word is
- **uniform information density**: how evenly surprisal is spread across the text
- **lexical density**: the share of content words, such as nouns, verbs and adjectives

For summaries, Adams et al. (2023) use entities per token as a proxy for density. Compression ratio appears in the sources only as a measure of redundancy in training data (Yin et al., 2024), not of generated output.

**Answer concision.**

- **Length-controlled win rates** remove the length bias from LLM-judge comparisons. This raised the Spearman correlation with Chatbot Arena from 0.94 to 0.98 (Dubois et al., 2025).
- **YapScore** counts characters beyond a curated minimal answer, so it does not depend on a tokenizer (Borisov et al., 2026).
- **ConCISE** scores conciseness without a reference answer. It averages three compression ratios: against an abstractive summary, against an extractive summary, and after removing words (Ghafari et al., 2026).

I did not check how well YapScore or ConCISE agrees with human judgement. ConCISE was read from its abstract only.

## 7. Where sources disagree

Whether shorter output is better is **contested**. The answer depends on what gets shortened.

- **Shortened reasoning** on math held or improved accuracy in large models given examples (Nayab et al., 2024; Xu et al., 2025).
- **Shortened final answers** on false-premise questions lost accuracy (Le Jeune et al., 2025).
- **Small models and prompts without examples** lost accuracy (Xu et al., 2025), as did GPT-3.5 on math (Renze & Guven, 2024).
- A single-author preprint reports the reverse for one case: a brevity limit raised large models' accuracy by about 26 points on problems where they underperformed small models (Hakim, 2026).

This split (reasoning versus final answer, task type, model size, examples given) fits the evidence. No study tested these factors against each other, so it remains a hypothesis.

Preference evidence also points two ways. Reward models and LLM judges favour longer answers (Singhal et al., 2023; Hu et al., 2025), while human readers preferred density up to human-written levels (Adams et al., 2023).

## 8. Limits and open questions

- No study of which parts of open-ended answers readers can lose.
- No evidence on density in translation or code output.
- No study of decoding-time methods.
- No controlled test of cutting redundancy or hedges.
- Most prompting and training results are on math reasoning and come from preprints.
- **Blocked sources that could change the reader findings:**
  - Harrag et al. (2025), *Too dense to comprehend—or perfectly packed? The divergent effects of propositional density on levels of text memory*, Discourse Processes. Publisher block.
  - Bo et al. (2024), a study of reliability disclaimers in an LLM tutor, HCOMP. Bot check; no open copy found, so its claim is unverified and not used.

The research board is at `.research/semantic-density-llm-output/` and can be resumed.

## Sources

- Adams, G., Fabbri, A., Ladhak, F., Lehman, E., & Elhadad, N. (2023). *From sparse to dense: GPT-4 summarization with chain of density prompting*. arXiv. https://arxiv.org/abs/2309.04269
- Balling, L. W. (2018). No effect of writing advice on reading comprehension. *Journal of Technical Writing and Communication, 48*(1), 104–122. https://research.cbs.dk/en/publications/26e94662-46ab-4c41-85d1-14ee869cc1dd
- Bar-Or Nirman, D., Weizman, A., & Azaria, A. (2024). *Fool me, fool me: User attitudes toward LLM falsehoods*. arXiv. https://arxiv.org/abs/2412.11625
- Bastian, M. (2025, May 11). *Confident user prompts make LLMs more likely to hallucinate*. The Decoder. https://the-decoder.com/confident-user-prompts-make-llms-more-likely-to-hallucinate/
- Borisov, V., Gröger, M., Mikhael, M., & Schreiber, R. H. (2026). *Do chatbot LLMs talk too much? The YapBench benchmark*. arXiv. https://arxiv.org/abs/2601.00624
- Chakrabarty, T., Laban, P., & Wu, C.-S. (2024). *Can AI writing be salvaged? Mitigating idiosyncrasies and improving human-AI alignment in the writing process through edits*. arXiv. https://arxiv.org/abs/2409.14509
- Dubois, Y., Galambosi, B., Liang, P., & Hashimoto, T. B. (2025). *Length-controlled AlpacaEval: A simple way to debias automatic evaluators*. arXiv. https://arxiv.org/abs/2404.04475
- Esposito, C. (2025). *AI should be more human, not more complex*. arXiv. https://arxiv.org/abs/2508.04713
- Ghafari, S. M., Kol, R., Quiroz, J. C., Luan, N., Patial, M., Rupasinghe, C., Wandabwa, H., & Pizzato, L. (2026). *ConCISE: A reference-free conciseness evaluation metric for LLM-generated answers*. arXiv. https://arxiv.org/abs/2511.16846
- Hakim, M. A. (2026). *Brevity constraints reverse performance hierarchies in language models*. arXiv. https://arxiv.org/abs/2604.00025
- Hu, Z., Song, L., Zhang, J., Xiao, Z., Wang, T., Chen, Z., Yuan, N. J., Lian, J., Ding, K., & Xiong, H. (2025). *Explaining length bias in LLM-based preference evaluations*. arXiv. https://arxiv.org/abs/2407.01085
- Ji, S., Sun, W., & Marttinen, P. (2023). *Content reduction, surprisal and information density estimation for long documents*. arXiv. https://arxiv.org/abs/2309.06009
- Kim, S. S. Y., Liao, Q. V., Vorvoreanu, M., Ballard, S., & Vaughan, J. W. (2024). *"I'm not sure, but...": Examining the impact of large language models' uncertainty expression on user reliance and trust*. arXiv. https://arxiv.org/abs/2405.00623
- Lang, T. (2017). How to shorten a text by up to 30% and improve clarity without losing information. *Medical Writing, 26*(1), 21–25. https://emwa.org/journal/writing-better/how-to-shorten-a-text-by-up-to-30-and-improve-clarity-without-losing-information
- Le Jeune, P., Malézieux, B., Xiao, W., & Dora, M. (2025). *Phare: A safety probe for large language models*. arXiv. https://arxiv.org/abs/2505.11365
- Lee, A., Che, E., & Peng, T. (2025). *How well do LLMs compress their own chain-of-thought? A token complexity approach*. arXiv. https://arxiv.org/abs/2503.01141
- Li, R., Luo, Z., Zhang, Q., Li, R., Zhou, B., Payani, A., & Du, X. (2025). *AALC: Large language model efficient reasoning via adaptive accuracy-length control*. arXiv. https://arxiv.org/abs/2506.20160
- Liu, S.-Y., Dong, X., Lu, X., Diao, S., Liu, M., Chen, M.-H., Yin, H., Wang, Y.-C. F., Cheng, K.-T., Choi, Y., Kautz, J., & Molchanov, P. (2025). *DLER: Doing length pEnalty right – Incentivizing more intelligence per token via reinforcement learning*. arXiv. https://arxiv.org/abs/2510.15110
- Lunn, A., Bürkle, D. M., Ward, R. J., McCloskey, A. P., Rathbone, A., Courtenay, A., Mullen, R., & Manfrin, A. (2021). Spoken propositional idea density, a measure to help second language English speaking students: A multicentre cohort study. *Medical Teacher*. https://clok.uclan.ac.uk/39317/
- Meister, C., Pimentel, T., Haller, P., Jäger, L., Cotterell, R., & Levy, R. (2021). *Revisiting the uniform information density hypothesis*. arXiv. https://arxiv.org/abs/2109.11635
- Nayab, S., Rossolini, G., Simoni, M., Saracino, A., Buttazzo, G., Manes, N., & Giacomelli, F. (2024). *Concise thoughts: Impact of output length on LLM reasoning and cost*. arXiv. https://arxiv.org/abs/2407.19825
- Poddar, S., Koley, P., Misra, J., Podder, S., Balani, N., Ganguly, N., & Ghosh, S. (2025). *Brevity is the soul of sustainability: Characterizing LLM response lengths*. arXiv. https://arxiv.org/abs/2506.08686
- Renze, M., & Guven, E. (2024). *The benefits of a concise chain of thought on problem-solving in large language models*. arXiv. https://arxiv.org/abs/2401.05618
- Singhal, P., Goyal, T., Xu, J., & Durrett, G. (2023). *A long way to go: Investigating length correlations in RLHF*. arXiv. https://arxiv.org/abs/2310.03716
- Stine, E. A. L., & Hindman, J. (1994). Age differences in reading time allocation for propositionally dense sentences. *Aging, Neuropsychology, and Cognition, 1*(1), 2–16. https://experts.illinois.edu/en/publications/age-differences-in-reading-time-allocation-for-propositionally-de/
- Xu, S., Xie, W., Zhao, L., & He, P. (2025). *Chain of draft: Thinking faster by writing less*. arXiv. https://arxiv.org/abs/2502.18600
- Yin, M., Wu, C., Wang, Y., Wang, H., Guo, W., Wang, Y., Liu, Y., Tang, R., Lian, D., & Chen, E. (2024). *Entropy law: The story behind data compression and LLM performance*. arXiv. https://arxiv.org/abs/2407.06645
- Zhang, Y., Das, S. S. S., & Zhang, R. (2024). *Verbosity ≠ veracity: Demystify verbosity compensation behavior of large language models*. arXiv. https://arxiv.org/abs/2411.07858
