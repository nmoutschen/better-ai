# Agents that improve their own instructions, memory and tools

Research findings · Search date: 11 November 2026

Skills an agent writes for itself, adopted without a check, did not help: in the largest test they lowered pass rates below having no skills at all. The systems that report gains all put a gate in front of each change: the change is adopted only if it does better on tasks held back from the ones it was built on, without breaking cases that passed before. Even gated changes often fail to carry over to new kinds of task. Over time, self-written libraries degrade unless skills are retired on measured results and their number is capped. An agent that judges its own changes, without an outside signal, is not reliable. People approve most of the prompts they see and stop reading them, and a written rationale can raise acceptance of wrong advice.

**Scope.** Changes an AI agent makes to its own scaffold (instructions, memory, skill library, tools and workflows), found without waiting for a failure, and possibly without the user invoking it. A human approves each change. Changes to model weights are out of scope. The goal is to decide the rules of a new skill, `/improve-better`. This report does not design the skill. How to compare runs with and without a skill, how many runs to use, and how reliable LLM judges are is covered in `evaluating-agent-skills.md` and is not repeated here.

**Status.** All high- and medium-priority questions are answered, most with thin evidence. Almost all sources are 2025–2026 arXiv preprints, each tested on its own benchmark, and most were read as abstracts. I checked every claim used below against its page, except the claims marked *unverified*.

## Findings at a glance

| Question | Finding | Evidence |
|---|---|---|
| Where do candidate changes come from without a failure? | New tasks proposed to explore, routines distilled from successful runs, and offline review of past session logs | Thin: abstracts, one vendor post |
| Do self-written changes help? | Not without a gate; with a gate, gains are reported | Moderate for "not without a gate"; thin for gated gains |
| How to check a change before adopting it | Replay held-out cases that passed and failed before, under a limit on regressions; test changes together, not only one by one | Thin: preprints with ablations |
| Do gains carry over? | Often not to new kinds of task | Thin |
| What goes wrong over time | Library drift, safety degrading as memory grows, self-copied malicious skills, judge errors that block retirement | Thin: abstracts, mostly one research group for drift |
| Can the agent judge its own changes? | No: models favour their own text and self-correction can make results worse | Moderate, but on 2023–2024 models |
| Can the agent game its checks? | Systems keep evaluation outside what the agent can edit; a poisoned benchmark produced persistent insecure changes | Thin |
| How to present a change for approval | Approval fatigue is real; rationales can raise acceptance of wrong advice; what is shown first is checked most | Thin and indirect: no study of agent self-changes |
| When to run the loop | No tested cadence; practitioner guidance only | Weak |

## 1. Finding candidate changes without a failure

Sources describe three signals that do not need a failure:

- **Proposing new tasks to explore.** Voyager uses "an automatic curriculum that maximizes exploration" and stores what it learns in "an ever-growing skill library of executable code" (Wang et al., 2023).
- **Distilling routines from successful runs.** SKILL-DISCO "distills reusable PFSM subgraphs from successful traces" (Guo et al., 2026). Agent Workflow Memory extracts reusable workflows either "from training examples beforehand or from test queries on the fly" (Wang et al., 2024).
- **Reviewing past sessions offline.** Anthropic describes "dreaming": "reflecting on logs to fix mistakes or produce new notes and representations." It can "search across many sessions to find common patterns or correct common mistakes," and lets the agent "test its notes against the original transcripts." In one test, "As we scaled dreaming from two sessions to 128, performance on the 25 questions grew from 13% to 48% of graded criteria" (Martin, 2026). Sleep-time compute works offline on a context by "anticipating what queries users might ask" (Lin et al., 2025, *unverified*), but it pre-computes answers rather than editing the scaffold.

Failures still help select changes. AutoRefine "contrasts failed against successful trajectories" (Qiu et al., 2026). In a study of feedback over several rounds, "All 11 selections come from feedback conditions that include failed trajectories" (Liu et al., 2026): none of the skills selected on validation came from successful runs alone.

The research did not read any source that uses cost or latency as the signal for a change.

## 2. Do self-written changes help?

**Without a gate, no.** In the current version of SkillsBench, "Self-generated Skills land below the no-Skills baseline on all three configurations": −8.1, −11.3 and −11.5 percentage points, "while curated Skills add +18.2 to +24.8 pp on the same configurations." The authors note that this deficit "mixes content quality with skill-discovery and creator/solver interference effects" (Li et al., 2026). The first version of the paper reported a smaller effect (−1.3 points on average, cited in `evaluating-agent-skills.md`); the current version tests newer models and no longer reports it. GRASP's authors write that skill writing "without validation is no better than using no skills" (Moll et al., 2026).

**With a gate, gains are reported.**

- GRASP attributes its gain "to comparative proposal generation, the acceptance gate, and the hard regression budget" (Moll et al., 2026).
- SkillOpt keeps a candidate skill "only if it improves held-out selection performance." It reports gains on every target model it tested, with no clear pattern by model size, and "A stronger optimizer model gives the largest gains" (Yang et al., 2026).
- Mistake Notebook Learning updates its memory "only when batch performance improves to ensure stability" (Su et al., 2025).
- EvoSkill reports that "skills evolved from SealQA transfers zero-shot to BrowseComp, improving accuracy by 5.3%" (Alzubi et al., 2026).

The contrast between gated and ungated changes is indirect: the studies use different benchmarks and models.

## 3. Checking a change before adopting it

Reported gates:

- **Held-out replay under a regression budget.** GRASP admits a candidate "only if it produces a net improvement on a balanced held-out probe under a hard regression budget" (Moll et al., 2026). AutoRefine admits a change "only when it improves the correction cases linked to its source failures without regression on preservation cases" (Qiu et al., 2026).
- **Runs with and without the change.** SelfEvoSkill compares "executions with and without the skill, while holding these factors fixed" (Gao et al., 2026).
- **Benchmark runs.** The Darwin Gödel Machine "empirically validates each change using coding benchmarks" (Zhang et al., 2025).

One ablation compared four checks (Shang et al., 2026):

- Removing held-out replay cost the most: pass@1 fell from 72% to 62%. The authors note it "is the only check that empirically tests behavior rather than surface form."
- Removing the check on the combined effect of skills grew the library from 37 to 58 skills and cost 8 points: "skills which each clear the individual checks can still conflict once injected together."
- Removing bad skills afterwards "recovers only a small part of the drop."

**A gate does not guarantee transfer.** "Granting the same acceptance gate to all five baselines lifts each of them in-domain and none of them out of distribution" (Moll et al., 2026). In another study, "Validation and downstream evaluations on test, robustness, and transfer sometimes favor different feedback views" (Liu et al., 2026).

## 4. What goes wrong over time

- **Library drift.** "Unbounded skill accumulation without outcome-driven lifecycle management causes retrieval degradation, false-positive injections, and performance stagnation" (Zhang et al., 2026a). A library left alone keeps "growing until injecting a skill scores worse than injecting nothing" (Zhang et al., 2026b).
- **Judge errors block clean-up.** When a judge scores failures as passes, "failures scored as passes displace the eviction statistic, and no correction inside the rule recovers it" (Zhang et al., 2026b).
- **Safety degrades.** Observed risks include "the degradation of safety alignment after memory accumulation" and "the unintended introduction of vulnerabilities in tool creation and reuse" (Shao et al., 2025).
- **Self-poisoning.** Agents copy malicious skills into new ones, at rates from 20.3% to 41.8% across six models. The copies form "a self-propagating worm that persists after the planted skills are removed." A prompt that discourages this copying cut the rate to at most 6.7% without a significant loss in task completion (Wu et al., 2026).
- **Wrong lessons stored as guidance.** "Reflection can endorse execution errors and store them as future guidance." Having a separate agent distil the lessons and other agents verify them cut this rate from 11.0% to 5.0% (Zhu et al., 2026).

Reported counter-measures: Ratchet "evicts each skill on its measured contribution, caps the library at width C, and constrains synthesis" (Zhang et al., 2026b). With this kind of management, held-out pass@1 rose from 0.258 to a late-window mean of 0.584 on one benchmark (Zhang et al., 2026a). A survey lists "feedback reliability, benchmark overfitting, reversibility" among the open problems (Zhou et al., 2026).

The research found nothing specific on rules that contradict each other, beyond the conflicting skills in section 3, or on overfitting to the most recent tasks.

## 5. The agent judging its own changes

- Models favour their own output: "a linear correlation between self-recognition capability and the strength of self-preference bias" (Panickssery et al., 2024).
- Without outside feedback, models struggle to correct their own reasoning, and "at times, their performance even degrades after self-correction" (Huang et al., 2024).
- The wrong-lessons finding in section 4 is the same failure in agent memory (Zhu et al., 2026).

No study tested an agent grading changes to its own scaffold. Both general studies use 2023–2024 models.

## 6. Gaming the checks

The research found no direct report of an agent tampering with the check on its changes. It found the risk, and the design choices meant to prevent it:

- Hyperagents keeps "parent selection, evaluation protocols" fixed: agents "cannot alter the outer process that determines which agents are selected or how they are evaluated." The authors write that "Keeping these components fixed improves experimental stability and safety, but limits full self-modifiability," and that safeguards such as sandboxing "may become increasingly strained or infeasible as self-improving systems grow more capable" (Zhang et al., 2026c).
- The Darwin Gödel Machine warns that "Modifications optimized solely for benchmark performance might inadvertently introduce vulnerabilities." Its archive provides "a traceable lineage of modifications for review" (Zhang et al., 2025).
- A poisoned benchmark fed into a self-improvement loop made the agent evolve instructions that disabled certificate checks, and "contamination often persists even when a poisoned agent is subsequently evolved against clean benchmarks." Adding security cues to tasks did not help: "We did not find these security cues to be a reliable defense." The authors suggest to "augment any untrusted benchmark with one internal to the self-modifying system" (Roesner & Kohno, 2026).

The Darwin Gödel Machine's case study on hallucination (its Appendix H) could not be read.

## 7. Presenting a change for approval

No study tested how an agent should present a change to its own configuration. The evidence is about approval in general:

- **People stop reading prompts.** For Claude Code's permission prompts, "in practice users accept 93% of them anyway," and "Over time that leads to approval fatigue, where people stop paying close attention to what they're approving" (Hughes, 2026).
- **AI help raises confidence more than quality.** Participants with an AI assistant "wrote significantly less secure code" and "were more likely to believe they wrote secure code" (Perry et al., 2023).
- **A rationale can backfire.** In one study, "explanations increased the chance that humans will accept the AI's recommendation, regardless of its correctness" (Bansal et al., 2021). Another found "there are scenarios where AI explanations reduce overreliance" (Vasconcelos et al., 2023).
- **What comes first gets checked most.** In code review, "files shown earlier in a PR … receive more comments than files shown later." For one of two defect types, reviewers had "64% lower odds to identify it when its file is last as opposed to first" (Fregnan et al., 2022).

The research found no study on the effect of change size, attached test results, or a stated expected effect.

## 8. When to run the loop

No source tested a cadence. The guidance found:

- Anthropic suggests to "focus dreaming on information that's likely to change or to carefully tune the cadence of dreaming (e.g., based on how often memories are accessed)," and notes that dreaming "requires compute" (Martin, 2026).
- AWS advises to "trigger the full reflection pass only when the score falls below a configurable threshold," to disable the trigger for task categories "that never benefit from reflection," and to "Review cost-quality baselines monthly (or quarterly for stable workloads)" (Amazon Web Services, n.d.). This guidance is about reflection within a task, not about changing the scaffold.
- One open-source pattern updates memory every N tasks, five by default (AgentFlow, n.d., *unverified*).

## 9. Which changes are safe to make

A survey classifies self-improvement by what it changes: "framework, memory, skills and tools, components, workflow and topology, or environment and context" (Zhou et al., 2026). The Darwin Gödel Machine, which edits its own code, ran "with safety precautions (e.g., sandboxing, human oversight)" (Zhang et al., 2025). Self-made tools can introduce vulnerabilities (Shao et al., 2025).

No source ranks these targets by risk. Treating prompts and memory as safer to change than code or tools is an inference, not a finding.

## 10. What the research could not find

- A study of an agent improving its scaffold for one user over time, outside a benchmark.
- Cost or latency used as the signal for a change.
- Effects of change size, attached evidence, or a stated expected effect on how well people judge a change.
- A tested cadence for a self-improvement loop.
- Contradicting rules and overfitting to recent tasks as failure modes.
- Direct tampering with the check by the agent itself. The Darwin Gödel Machine's Appendix H was not readable.
- Leads not read: process-level evaluation of self-evolving agents (arXiv 2609.24663), a survey of skill library lifecycles (arXiv 2607.10113), RewardHackingAgents (arXiv 2603.11337), the "Blind Curator" paper, trajectory mining for skills (arXiv 2606.20363), and a workshop abstract on reward hacking in self-improving code agents (Zhao et al., 2026, abstract only).

The research board is in `.research/agent-self-improvement/` in the worktree where it was made, and is not committed.

## References

AgentFlow. (n.d.). *Self-improving pattern*. AgentFlow documentation. https://iuyup.github.io/AgentFlow/patterns/self_improving/

Alzubi, S., Provenzano, N., Bingham, J., Chen, W., & Vu, T. (2026). *EvoSkill: Automated skill discovery for multi-agent systems*. arXiv. https://arxiv.org/abs/2603.02766

Amazon Web Services. (n.d.). *AGENTCOST01-BP01 Use the reflection pattern to design efficient agent reasoning loops*. AWS Well-Architected Framework, Agentic AI Lens. https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentcost01-bp01.html

Bansal, G., Wu, T., Zhou, J., Fok, R., Nushi, B., Kamar, E., Ribeiro, M. T., & Weld, D. S. (2021). Does the whole exceed its parts? The effect of AI explanations on complementary team performance. In *CHI 2021*. https://arxiv.org/abs/2006.14779

Fregnan, E., Braz, L., D'Ambros, M., Çalikli, G., & Bacchelli, A. (2022). First come first served: The impact of file position on code review. In *ESEC/FSE 2022*. https://arxiv.org/abs/2208.04259

Gao, H., Chen, H., Wang, C., Guo, S., Pang, L., Liu, Z., Shen, H., & Cheng, X. (2026). *SelfEvoSkill: Paired execution audits for skill revision without external outcome supervision*. arXiv. https://arxiv.org/abs/2606.14239

Guo, Z., Qi, D., Gu, H., Cheng, P., & Xiong, Y. (2026). *SKILL-DISCO: Distilling and compiling agent traces into reusable procedural skills*. arXiv. https://arxiv.org/abs/2606.26669

Huang, J., Chen, X., Mishra, S., Zheng, H. S., Yu, A. W., Song, X., & Zhou, D. (2024). Large language models cannot self-correct reasoning yet. In *ICLR 2024*. https://arxiv.org/abs/2310.01798

Hughes, J. (2026, March 25). *How we built Claude Code auto mode: A safer way to skip permissions*. Anthropic Engineering. https://www.anthropic.com/engineering/claude-code-auto-mode

Li, X., et al. (2026). *SkillsBench: Benchmarking how well agent skills work across diverse tasks* (Version 4). arXiv. https://arxiv.org/abs/2602.12670

Lin, K., Snell, C., Wang, Y., Packer, C., Wooders, S., Stoica, I., & Gonzalez, J. E. (2025). *Sleep-time compute: Beyond inference scaling at test-time*. arXiv. https://arxiv.org/abs/2504.13171

Liu, Y., Su, Z., Zhang, Y., Guo, J., Xie, Z., Jing, H., Xie, L., Zong, Q., Yim, Y., Zhang, Z., Li, H., & Song, Y. (2026). *Rethinking self-evolving agent skills: Feedback dynamics over multiple rounds*. arXiv. https://arxiv.org/abs/2608.02636

Martin, L. (2026, November 6). *The components of agent memory*. Anthropic. https://anthropic.com/research/components-of-agent-memory

Moll, J., Corbeil, J.-P., Pan, J., Hadamitzky, M., Rueckert, D., Adams, L., & Bressem, K. (2026). *GRASP: Gated regression-aware skill proposer for self-improving LLM agents*. arXiv. https://arxiv.org/abs/2605.29668

Panickssery, A., Bowman, S. R., & Feng, S. (2024). *LLM evaluators recognize and favor their own generations*. arXiv. https://arxiv.org/abs/2404.13076

Perry, N., Srivastava, M., Kumar, D., & Boneh, D. (2023). Do users write more insecure code with AI assistants? In *CCS '23*. https://arxiv.org/abs/2211.03622

Qiu, L., et al. (2026). *AutoRefine: Compiling trajectories into validated typed agent artifacts*. arXiv. https://arxiv.org/abs/2601.22758

Roesner, F., & Kohno, T. (2026). *Reflections on trusting trust, revisited: Contaminating self-modifying AI coding agents with poisoned benchmarks*. arXiv. https://arxiv.org/html/2609.17817

Shang, L., Xu, M., Sun, Y., Xia, T., Hu, L., Xu, L., & Zheng, N. (2026). *When self-evolution backfires: Pre-commit gating against skill contamination in LLM agents*. arXiv. https://arxiv.org/html/2608.05810

Shao, S., Ren, Q., Qian, C., Wei, B., Guo, D., Yang, J., Song, X., Zhang, L., Zhang, W., Liu, D., & Shao, J. (2025). *Your agent may misevolve: Emergent risks in self-evolving LLM agents*. arXiv. https://arxiv.org/abs/2509.26354

Su, X., et al. (2025). *Mistake notebook learning: Batch-clustered failures for training-free agent adaptation*. arXiv. https://arxiv.org/abs/2512.11485

Vasconcelos, H., Jörke, M., Grunde-McLaughlin, M., Gerstenberg, T., Bernstein, M., & Krishna, R. (2023). Explanations can reduce overreliance on AI systems during decision-making. In *CSCW 2023*. https://arxiv.org/abs/2212.06823

Wang, G., Xie, Y., Jiang, Y., Mandlekar, A., Xiao, C., Zhu, Y., Fan, L., & Anandkumar, A. (2023). *Voyager: An open-ended embodied agent with large language models*. arXiv. https://arxiv.org/abs/2305.16291

Wang, Z. Z., Mao, J., Fried, D., & Neubig, G. (2024). *Agent workflow memory*. arXiv. https://arxiv.org/abs/2409.07429

Wu, X., Shi, Y., Li, Q., Zhao, Z., Li, X., Adams, B., Hassan, A. E., & Ni, J. (2026). *EVOMAL: Self-poisoning in self-evolving coding agents*. arXiv. https://arxiv.org/abs/2608.25776

Yang, Y., et al. (2026). *SkillOpt: Executive strategy for self-evolving agent skills*. Project page. https://microsoft.github.io/SkillOpt/

Zhang, J., Hu, S., Lu, C., Lange, R., & Clune, J. (2025). *Darwin Gödel Machine: Open-ended evolution of self-improving agents*. arXiv. https://arxiv.org/abs/2505.22954

Zhang, J., Zhao, B., Yang, W., Foerster, J., Clune, J., Jiang, M., Devlin, S., & Shavrina, T. (2026c). *Hyperagents*. arXiv. https://arxiv.org/html/2603.19461v1

Zhang, X., Cui, Y., Wang, G., Li, Z., Qiu, W., Zhu, B., & He, P. (2026a). *Library drift: Diagnosing and fixing a silent failure mode in self-evolving LLM skill libraries*. arXiv. https://arxiv.org/abs/2605.19576

Zhang, X., Cui, Y., Wang, G., Li, Z., Qiu, W., Zhu, B., & He, P. (2026b). *Ratchet: How reliable must an LLM judge be to retire a skill?* arXiv. https://arxiv.org/abs/2605.22148

Zhao, B., Srikanth, D., Wu, Y., & Jiang, Z. (2026). *Reward hacking in self-improving code agents* [Poster]. ICLR 2026 Workshop on AI with Recursive Self-Improvement. https://iclr.cc/virtual/2026/10018648

Zhou, H., Hu, H., Luo, T., Shang, Y., Fang, C., Chen, Z., Xiao, L., & Zhang, Q. (2026). *Self-evolving coding agents*. arXiv. https://arxiv.org/abs/2608.03392

Zhu, S., et al. (2026). *Beyond self-reflection: An Execute-Distill-Verify framework for agentic experience learning*. arXiv. https://arxiv.org/abs/2606.24428
