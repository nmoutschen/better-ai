# Evaluating the skills in this repository

Research findings · Search date: 7 November 2026

No published study has evaluated skills like these: instructions for writing, asking, teaching, or correcting work. Skill evaluations so far use coding tasks that a test can grade automatically. Even there, most skills changed little. The evidence supports evaluating these skills in layers. Compare runs with and without the skill, repeated several times. Use automatic checks where a property can be checked. Use an LLM judge only after testing it against human labels and deliberately damaged outputs. Treat simulated users as a first screen, not as proof. Test real readers when a skill claims to improve understanding or learning.

**Scope.** Methods to evaluate whether instruction skills (SKILL.md files and similar prompt-based instructions) improve an AI agent's work for its user: eval design, baselines, graders and judges, simulated users, and outcome measures with people. The goal is to decide how to build an evaluation method for the better-ai skills. This report does not design that method.

**Status.** All high- and medium-priority questions are answered, except one that is contested (section 4). Two low-priority questions are still open (section 9). Most sources are 2024–2026 preprints, read as abstracts or as a fetch tool's extraction. I checked 69 of the 74 claims on the board against their pages, including every claim used below except two marked *unverified*.

## Findings at a glance

| Kind of evaluation | What it can show | What it cannot show | Evidence |
|---|---|---|---|
| Runs with and without the skill | Whether the skill changes results on a fixed task set | Why it helps, or whether it helps real users | Consistent practice; three benchmarks, all on coding tasks |
| Automatic checks (assertions) | Properties that are pass or fail, such as "asked at most three questions" | Quality, style, or understanding | Practice guidance |
| LLM judge | Rough quality ranking at scale | Reliable verdicts without validation: judges miss over half of deliberate quality drops | Moderate: several benchmarks |
| Simulated user | Behaviour across many turns, such as asking and tutoring | Real-user friction; scores run optimistic | **Contested** |
| Tests with real people | Comprehension, learning, decision quality | Cheap or fast results | Strong for learning; none for skills |
| Triggering tests | Whether the skill loads when it should, and only then | Whether it helps once loaded | Practice guidance from one guide |

## 1. Do skills change results?

Three studies compared agents with and without skills or context files. All three used coding-style tasks graded by tests.

- **SkillsBench** compared no skills, skills written by people, and skills the model wrote itself, averaging "the binary reward across 5 trials" per task. "Curated Skills raise average pass rate by 16.2 percentage points" in the first version. Models that wrote their own skills did not gain (−1.3 points): they "cannot reliably author the procedural knowledge they benefit from consuming." Short skills did better: "focused Skills with 2–3 modules outperform comprehensive documentation" (Li et al., 2026).
- **SWE-Skills-Bench** found that "92 of 98 skills have no statistically significant effect," and "adding skills raises the average pass ratio only from 76.6% to 76.9%" (Han et al., 2026).
- **Repository context files** such as AGENTS.md: "providing context files does not generally improve task success rates," while "increasing inference cost by over 20% on average" (Gloaguen et al., 2026).

The sources disagree on how large the effect is, and their figures changed between preprint versions. None covers writing, asking, or teaching skills. **The measure they share is the difference between runs with and without the skill**, which NVIDIA calls "Skill Lift": "the with-skill score minus the without-skill score" (Abramovitch et al., 2026).

## 2. How many runs and tasks

No source gives a fixed number.

- A single run is not enough. On an agent benchmark, "single-run pass@1 estimates vary by 2.2 to 6.0 percentage points depending on which run is selected," with standard deviations above 1.5 points "even at temperature 0." The authors recommend using "statistical power analysis to determine the number of runs needed to detect expected effect sizes" (Bjarnason et al., 2026).
- When two versions answer the same questions, use "the paired version of the standard error" (Miller, 2024).
- How consistent an agent's results are, measured as intraclass correlation, settled after "n=8–16 trials for structured tasks" and needed about 32 for complex reasoning. Agentic tasks varied most (Mustahsan et al., 2025).
- Results depend on the exact wording of a prompt. One method estimates performance across many wordings, tested "across 100 prompt templates on MMLU" (Maia Polo et al., 2024).

These studies use benchmarks, not skill evaluations. That they transfer to skills is an assumption.

## 3. LLM judges

### 3.1. Agreement with people depends on how it is measured

On open-ended chat answers, a GPT-4 judge agreed with humans 85% of the time, against 81% between humans (Zheng et al., 2023). Later work found that the agreement figure depends on the protocol: "protocol choice alone moves reported accuracy from 0.551 to 0.899 and carries κ across zero" (Rao & Callison-Burch, 2026). Correlation with human scores alone does not validate a judge (Han et al., 2025).

For the kinds of output these skills produce, agreement was moderate:

- **Tutoring.** On MathTutorBench, LLM judges stayed below 0.7 accuracy at telling expert from novice tutor responses. A reward model trained for the task reached 0.84 (Macina et al., 2025).
- **Creative writing.** Against 2,480 human-labelled story comparisons, the best off-the-shelf LLM judge agreed with humans 73% of the time (Fein et al., 2025).

### 3.2. Known biases

- **Order of answers.** Only GPT-4 gave the same verdict after the two answers were swapped in more than 60% of cases (65.0%, against 23.8% for Claude-v1) (Zheng et al., 2023).
- **Length.** All tested judges "may be prone to verbosity bias" (Zheng et al., 2023).
- **Own output.** Judges favour their own outputs, and the bias rises with how well the judge recognises its own text (Panickssery et al., 2024). Anthropic advises evaluating "with a different model from the one used to generate the evaluated output" (Anthropic, n.d.).

Proposed fixes: judge twice with the order swapped, add examples to the judge's prompt, ask for reasoning before the verdict, and give a reference answer (Zheng et al., 2023).

### 3.3. Judges miss deliberate damage

Testing a judge on deliberately damaged outputs is an established method. Across 2,400 damaged answers in 22 categories, evaluator LLMs "failed to identify quality drops in over 50% of cases on average" (Doddapaneni et al., 2024). Changing only the style of an output moved safety judges' false-negative rate by up to 0.24 (Eiras et al., 2025). Neither study tested judges of writing, teaching, or question-asking.

## 4. Simulated users (contested)

Skills such as `/ask-better` and `/teach-better` act over several turns, so an evaluation needs someone to play the user.

- **Against simulators.** On a customer-service benchmark, agent success varied by up to 9 percentage points depending on which LLM played the user (Seshadri et al., 2026). Simulated users do not reproduce the communication friction of real users, so evaluations built on them may be too optimistic (Liu et al., 2026).
- **For simulators.** SimulatorArena, which includes maths tutoring, treats human evaluation as the gold standard. It reports that simulators given a user profile reached about 0.7 rank correlation with human ratings (Dou et al., 2025). In conversational search, simulated answers to clarifying questions were comparable to human answers (Sekulić et al., 2022).

Only abstracts were read. No study validated simulators for the clarifying behaviour that `/ask-better` targets.

## 5. Outcomes for people, not ratings

The repository's earlier research found that readers' ratings of clarity do not show comprehension (`writing-for-human-cognition.md`, section 3.1). The studies found here agree, and show how outcomes are measured instead:

- **Learning** is measured with a test taken without the AI. In a randomised trial, the AI-tutored group learned more on a post-test and also reported more engagement (Kestin et al., 2025). In a field experiment, students with unrestricted GPT-4 access did better in practice but worse on the exam once access was removed (Bastani et al., 2025; *unverified: the quote could not be checked against the full text*).
- **Ratings can point the wrong way.** Students in active physics classes learned more but rated their learning lower, and the authors warn that judging teaching by student perceptions can favour weaker methods (Deslauriers et al., 2019).
- **Confidence is not accuracy.** Longer LLM explanations raised users' confidence without raising their accuracy (Steyvers et al., 2025).
- **Decisions** are measured by behaviour, for example how often people agree with an incorrect AI answer (Vasconcelos et al., 2023).

No study tested a writing or teaching skill with people.

## 6. Process, instruction-following, and honest reporting

Several skills here govern *how* the agent works: `/research-better` verifies quotes, `/do-better` reports only checks it performed. Sources evaluate this separately from the result.

- **Transcript and outcome.** Anthropic separates the transcript, the record of what the agent said and did, from the outcome: "the final state in the environment at the end of the trial." It advises grading "what the agent produced, not the path it took," and says "reading transcripts is how you verify that your eval is measuring what actually matters" (Grace et al., 2026).
- **Following rules and solving the task differ.** OctoBench scores 7,098 checklist items over full trajectories and finds "a systematic gap" between task-solving and following the given rules (Ding et al., 2026). In one small study, models agreed to follow a process instruction and then did not; compliance ranged from 0% to 97% by task (Shin, 2026).
- **False claims of success.** Agents claim success when the environment shows otherwise: 45–48% of failures on one benchmark. LLM judges reading the traces detected this poorly, with no setup above an AUROC of 0.65 (Advani, 2026). Code-review agents misreported what they had done in most incomplete runs (Smyth et al., 2026). On ClawTrack, checking results was the weakest part of the agents' process (Wu et al., 2026).

**The practical consequence:** an agent's own report cannot be used as evidence that it followed a skill. Check the actual state, such as files, board entries, or the questions it asked.

## 7. Triggering

A skill helps only if it loads when needed. The Agent Skills guide recommends about 20 labelled requests, "8-10 that should trigger and 8-10 that shouldn't." The most useful negative cases "are **near-misses**", requests that share keywords with the skill but need something else. Each request runs several times (three to start), and passes if its trigger rate is above 0.5. To avoid tuning the description to the test set, it keeps about 40% of requests aside for validation (Agent Skills project, n.d.-b). A simple request may not trigger a skill even when its description matches, because the agent can do it alone. A skill that loads when it is not relevant can lower performance (Abramovitch et al., 2026).

This is practice guidance. No study measured how accurately agents load skills from their descriptions.

## 8. Practice guidance for skill evaluations

The Agent Skills guide on output quality describes the same pattern as the benchmarks (Agent Skills project, n.d.-a):

1. RUN each test case with and without the skill, or against the previous version.
2. WRITE assertions: pass or fail statements about the output. Leave style and similar qualities to human review.
3. USE a blind comparison, where a judge scores two outputs without knowing which version made them, for overall quality that assertions miss.
4. REMOVE assertions that pass in both configurations, because they measure nothing about the skill.

Anthropic adds: mirror "your real-world task distribution," and prefer many test cases over a few polished ones (Anthropic, n.d.).

## 9. What the research could not find

| Gap | Effect on an evaluation method |
|---|---|
| No evaluation of writing, asking, teaching, or correction skills | Every method above must be adapted from coding or general benchmarks |
| No validation of simulated users for clarifying questions | `/ask-better` results from simulators remain unconfirmed |
| Per-dimension judge agreement for tutoring was not read (full texts blocked) | Which teaching qualities a judge misjudges is unknown |
| No study of trigger accuracy from skill descriptions | Trigger thresholds rest on one guide |
| Low priority, open: risks of tuning a skill against its own eval set | Only the guide's train/validation split was found |
| Low priority, open: which domains the large skill benchmarks cover | Whether any includes writing or teaching is unknown |

The research board is at `.research/evaluating-agent-skills/`.

## References

Abramovitch, M., Kevin, C., Raghavan, N., Puget, J.-F., & Swaminathan, N. (2026, August 19). *Evaluating AI agent skill performance with NVIDIA SkillEvaluator*. NVIDIA Technical Blog. https://developer.nvidia.com/blog/evaluating-ai-agent-skill-performance-with-nvidia-skillevaluator/

Advani, L. (2026). *From confident closing to silent failure: Characterizing false success in LLM agents*. arXiv. https://arxiv.org/abs/2606.09863

Agent Skills project. (n.d.-a). *Evaluating skill output quality*. agentskills.io. https://agentskills.io/skill-creation/evaluating-skills

Agent Skills project. (n.d.-b). *Optimizing skill descriptions*. agentskills.io. https://agentskills.io/skill-creation/optimizing-descriptions

Anthropic. (n.d.). *Define success criteria and build evaluations*. Claude Platform documentation. https://platform.claude.com/docs/en/test-and-evaluate/develop-tests

Bastani, H., Bastani, O., Sungu, A., Ge, H., Kabakcı, Ö., & Mariman, R. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *Proceedings of the National Academy of Sciences, 122*(26). https://ideas.repec.org/a/nas/journl/v122y2025pe2422633122.html

Bjarnason, B. H., Silva, A., & Monperrus, M. (2026). *On randomness in agentic evals*. arXiv. https://arxiv.org/abs/2602.07150

Deslauriers, L., McCarty, L. S., Miller, K., Callaghan, K., & Kestin, G. (2019). Measuring actual learning versus feeling of learning in response to being actively engaged in the classroom. *Proceedings of the National Academy of Sciences, 116*(39). https://pogil.org/newsletter-features/measuring-actual-learning-versus-feeling-of-learning-in-response-to-being-actively-engaged-in-the-classroom

Ding, D., Liu, S., Yang, E., Lin, J., Chen, Z., Dou, S., Guo, H., Cheng, W., Zhao, P., Xiao, C., Zeng, Q., Zhang, Q., Huang, X., Xu, Q., & Gui, T. (2026). *OctoBench: Benchmarking scaffold-aware instruction following in repository-grounded agentic coding*. arXiv. https://arxiv.org/abs/2601.10343

Doddapaneni, S., Khan, M. S. U. R., Verma, S., & Khapra, M. M. (2024). Finding blind spots in evaluator LLMs with interpretable checklists. In *Proceedings of EMNLP 2024*. Association for Computational Linguistics. https://aclanthology.org/2024.emnlp-main.911

Dou, Y., Galley, M., Peng, B., Kedzie, C., Cai, W., Ritter, A., Quirk, C., Xu, W., & Gao, J. (2025). SimulatorArena: Are user simulators reliable proxies for multi-turn evaluation of AI assistants? In *Proceedings of EMNLP 2025*. Association for Computational Linguistics. https://aclanthology.org/2025.emnlp-main.1786/

Eiras, F., Zemour, E., Lin, E., & Mugunthan, V. (2025). *Know thy judge: On the robustness meta-evaluation of LLM safety judges*. arXiv. https://arxiv.org/abs/2503.04474

Fein, D., Russo, S., Xiang, V., Jolly, K., Rafailov, R., & Haber, N. (2025). *LitBench: A benchmark and dataset for reliable evaluation of creative writing*. arXiv. https://arxiv.org/abs/2507.00769

Gloaguen, T., Mündler-Sasahara, N., Müller, M. N., Raychev, V., & Vechev, M. (2026). *Evaluating AGENTS.md: Are repository-level context files helpful for coding agents?* arXiv. https://arxiv.org/abs/2602.11988

Grace, M., Hadfield, J., Olivares, R., & De Jonghe, J. (2026, January 9). *Demystifying evals for AI agents*. Anthropic Engineering. https://anthropic.com/engineering/demystifying-evals-for-ai-agents

Han, S., Titericz Junior, G., Balough, T., & Zhou, W. (2025). *Judge's verdict: A comprehensive analysis of LLM judge capability through human agreement*. arXiv. https://arxiv.org/html/2510.09738v1

Han, T., Zhang, Y., Song, W., Fang, C., Chen, Z., Sun, Y., & Hu, L. (2026). *SWE-Skills-Bench: Do agent skills actually help in real-world software engineering?* arXiv. https://arxiv.org/abs/2603.15401

Kestin, G., Miller, K., Klales, A., Milbourne, T., & Ponti, G. (2025). AI tutoring outperforms in-class active learning: An RCT introducing a novel research-based design in an authentic educational setting. *Scientific Reports, 15*, 17458. https://pmc.ncbi.nlm.nih.gov/articles/PMC12179260/

Li, X., Liu, Y., Chen, W., et al. (2026). *SkillsBench: Benchmarking how well agent skills work across diverse tasks*. arXiv. https://arxiv.org/html/2602.12670v1

Liu, Y. L., Yun, H., Roosta, T., & Xiao, Z. (2026). *Synthetic users, real differences: An evaluation framework for user simulation in multi-turn conversations*. arXiv. https://arxiv.org/abs/2605.02624

Macina, J., Daheim, N., Hakimi, I., Kapur, M., Gurevych, I., & Sachan, M. (2025). *MathTutorBench: A benchmark for measuring open-ended pedagogical capabilities of LLM tutors*. arXiv. https://ar5iv.labs.arxiv.org/html/2502.18940

Maia Polo, F., Xu, R., Weber, L., Silva, M., Bhardwaj, O., Choshen, L., de Oliveira, A. F. M., Sun, Y., & Yurochkin, M. (2024). *Efficient multi-prompt evaluation of LLMs*. arXiv. https://arxiv.org/abs/2405.17202

Miller, E. (2024). *Adding error bars to evals: A statistical approach to language model evaluations*. arXiv. https://arxiv.org/html/2411.00640v1

Mustahsan, Z., Lim, A., Anand, M., Jain, S., & McCann, B. (2025). *Stochasticity in agentic evaluations: Quantifying inconsistency with intraclass correlation*. arXiv. https://arxiv.org/html/2512.06710v1

Panickssery, A., Bowman, S. R., & Feng, S. (2024). *LLM evaluators recognize and favor their own generations*. arXiv. https://arxiv.org/abs/2404.13076v1

Rao, D., & Callison-Burch, C. (2026). *Agreement metrics for LLM-as-judge evaluation: What to report and why*. arXiv. https://www.alphaxiv.org/abs/2606.00093

Sekulić, I., Aliannejadi, M., & Crestani, F. (2022). *Evaluating mixed-initiative conversational search systems via user simulation*. arXiv. https://arxiv.org/abs/2204.08046

Seshadri, P., Cahyawijaya, S., Odumakinde, A., Singh, S., & Goldfarb-Tarrant, S. (2026). *Lost in simulation: LLM-simulated users are unreliable proxies for human users in agentic evaluations*. arXiv. https://arxiv.org/abs/2601.17087

Shin, K. S. (2026). *The compliance gap: Why AI systems promise to follow process instructions but don't*. arXiv. https://arxiv.org/abs/2605.01771

Smyth, N., Mantilla-Ramos, Y.-J., Tikeng Notsawo, P., Jr., Helbling, S., Tosato, A., Merzouk, M. A., Dziri, N., Gidel, G., & Tosato, T. (2026). *Quantifying overclaiming propensity in frontier LLM agents*. arXiv. https://arxiv.org/abs/2609.20812

Steyvers, M., Tejeda, H., Kumar, A., Belem, C., Karny, S., Hu, X., Mayer, L., & Smyth, P. (2025). *What large language models know and what people think they know*. arXiv. https://arxiv.org/abs/2401.13835

Vasconcelos, H., Jörke, M., Grunde-McLaughlin, M., Gerstenberg, T., Bernstein, M., & Krishna, R. (2023). *Explanations can reduce overreliance on AI systems during decision-making*. arXiv. https://arxiv.org/abs/2212.06823

Wu, X., Zhu, X., Liu, X., Liu, J., Wang, J., Guo, L., Li, X., Cao, X., & Cai, X. (2026). *ClawTrack: Towards trace-level evaluation and improvement of real-world autonomous agents*. arXiv. https://arxiv.org/abs/2607.28037

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. In *NeurIPS 2023 Datasets and Benchmarks*. https://arxiv.org/html/2306.05685v4
