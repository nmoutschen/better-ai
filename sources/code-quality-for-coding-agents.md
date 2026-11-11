# Code quality for AI coding agents

Research findings · Search date: 11 November 2026

Code written by AI coding agents passes tests more often than it meets maintainers' standards. Agents edit more than the task needs, add complexity, ignore repository rules unless reminded, and write tests that check little. The evidence supports a few runtime rules: keep the change minimal and say so in the instruction, check against the specific tests the change affects, run static analysis or security feedback and fix what it reports, and keep each change to one purpose. Few interventions have been tested on repository-level work, and almost all sources are 2025–2026 preprints read as abstracts.

**Scope.** What an AI coding agent can do at runtime so that the code it writes for a user is correct, minimal, in scope, tested, fits the existing codebase, and stays maintainable. Training methods are out of scope. Asking versus proceeding, gaming tests, and honest self-reporting are covered in `agent-alignment-with-user-intent.md` and not repeated here. These findings are input for a `code-better` skill. This report does not design it.

**Status.** All 10 high- and medium-priority questions are answered, except one that is contested (section 7). One low-priority question on terminology is still open. 31 sources, 52 claims. I checked every claim's quote against its source page; all 52 are on the page. 19 sources were read as abstracts only, so their numbers come from the abstract and not from the full method.

## Findings at a glance

| Finding | Evidence | Evidence boundary |
|---|---|---|
| Agent code adds warnings, complexity and smells | Causal study of Cursor adoption; controlled Java benchmark | Static metrics, not defects |
| Later agents fail more often on top of agent code | One controlled experiment: up to 13.1% fewer follow-up tasks solved | Single study; field data mixed |
| About half of test-passing patches would not be merged | Maintainer review of SWE-bench patches | One benchmark |
| Agents edit more than needed | Measured over-editing; a one-line instruction reduced it | Single-function repair; abstracts |
| Large, mixed PRs are rejected more | Five mining studies of agent PRs | Correlational |
| Agents ignore repository rules unless reminded | One study of contribution rules | Abstract |
| Agent-written tests check little | More print statements than assertions; writing tests did not change resolution | One scaffold, one benchmark |
| Targeted test selection cut regressions; generic TDD raised them | One intervention study | 100 tasks, small model, no significance test |
| Static-analysis and security feedback fix many issues | Two studies | Snippet-level, not agent runs |
| Instruction files (AGENTS.md) help | **Contested** | Effects differ by outcome and project |

## 1. How agent code differs from human code

Static measures point one way. Adopting Cursor in open-source projects gave "a short-lived velocity gain but a persistent rise in static analysis warnings and code complexity", and the added warnings and complexity are linked to later slowdown (He et al., 2025). In a controlled Java benchmark, LLM-generated code had about 63% more code smells than reference solutions, more for complex tasks (Paul et al., 2025). A vendor analysis reports fewer moved (refactored) lines and more copy-pasted lines from 2021 to 2024 (GitClear, n.d.); treat it as low trust.

One controlled experiment tested maintainability directly. Agents solved follow-up tasks less often when building on agent-written code than on human-written code, by up to 13.1% (Patel et al., 2026). "Many traditional software engineering maintainability metrics do not explain this difference. Instead, the clearest signals are subtler behavioral differences in agent code, such as changes to input validation and error handling" (Patel et al., 2026).

Field data is mixed. Post-merge revert rates differ by agent: Codex PRs were reverted about half as often as human PRs, Devin PRs more often, and pooled agent code was less likely to contain a security smell (Kraishan, 2026). AI-generated files are maintained less often than human files, mostly by humans (Sawada et al., 2026). Among merged agent bug-fix PRs, differences between agents in SonarQube issues disappear once normalized by churn: larger PRs produce more issues (Cynthia et al., 2026). Agent PRs differ from human PRs most in commit count, and moderately in files touched and lines deleted (Ogenrwot & Businge, 2026).

**Passing tests is not merging.** Roughly half of test-passing SWE-bench patches would not be merged by maintainers, and the automated grader overstates the merge rate by about 24 points (Whitfill et al., 2026). Maintainers rejected them for code quality (style, repository standards), for breaking other code, or for failing the core task. Merge success also does not indicate post-merge quality of agent PRs (Cynthia et al., 2026).

## 2. Why agent pull requests are rejected

Claude Code PRs were accepted less often than human PRs (83.8% vs 91.0%). Of the merged ones, 45.1% needed further changes, mostly bug fixes, documentation, refactoring and code style (Watanabe et al., 2025).

Rejected agent PRs "tend to have larger code changes, touch more files, and often fail CI/CD" (Ehsani et al., 2026). In 600 manually coded rejections, the most frequent patterns were reviewer abandonment (228), duplicate PRs (142) and CI or test failure (99). Unwanted features (24) and misalignment with reviewer instructions (9) were rarer. Maintainers asked for PRs that are small, focused on one coherent change, and do not mix substantive changes with unrelated edits (Ehsani et al., 2026). Some rejection reasons occur only for agent PRs, such as "too large" and "no confidence in AI-generated code" (Nakashima et al., 2026).

Merge outcome is a weak label. Only about a third of rejections reflect a clear agent failure; a third are workflow constraints and a third have no visible reason (Peralta et al., 2026). 67.9% of rejected PRs had no explicit reviewer feedback (Nakashima et al., 2026). All of these studies are correlational: none tests PR size or scope as a cause.

## 3. Doing more than the task asks

Over-editing is measured. "High Pass@1 can coexist with unnecessarily large edits and added cognitive complexity", even for strong models (Zhu et al., 2026). **A one-line preservation instruction reduced it**: "lowering average excess Levenshtein distance from 0.195 to 0.131, reducing added cognitive complexity by 26.6%, and increasing Pass@1 by 2.3 points" (Zhu et al., 2026). Larger models or reasoning budgets did not account for the gain. This was tested on single-function repair, not on repository tasks.

Agents also carry speculative edits and abandoned hypotheses from their search into the final patch ("CodeSlop"). Removing them after the fact cut 17.9%–32.9% of such edits with negligible performance loss (Mathai et al., 2026). Patch size relative to the reference depends on the benchmark, so one benchmark recommends assessing scope alongside test results (Shayanfar et al., 2026).

**Gap.** No controlled study measured unrequested features or unnecessary defensive code. Practitioner blogs describe both; they were not recorded as evidence.

## 4. Following conventions and non-functional instructions

Strong models "struggle to follow multiple verifiable non-functional code instructions" and lose functional correctness when they do (Zhong et al., 2025). A combined score of correctness and instruction following matched human preference best. As structural requirements (architecture, ORM, database) accumulate, agent pass rates drop by about 27 points on average, more in convention-heavy frameworks such as Django and FastAPI (Dente et al., 2026).

Agents "almost never proactively retrieve the contribution rules" of a repository, but follow them with "reminder prompts, rule quotes, and verifier feedback" (Yang et al., 2026).

**Gap.** No benchmark scores how well code matches a specific codebase's own style and patterns.

## 5. Tests

In 5,000 SWE-bench Verified runs, agent-written test files used many more print statements than assertions. Prompting agents to write or skip tests changed resolved tasks by 0–13 of 500 per model, not significant, but changed cost substantially for three models (Chen et al., 2026). One model rarely wrote tests yet resolved nearly as many tasks as the top model.

Coverage is a weak signal: some test suites reached 100% coverage with a 4% mutation score. Feeding mutation results back into the prompt improved the fault detection of LLM unit tests (Wang et al., 2025). This was unit-test generation, not agent patches.

## 6. Runtime practices tested

Few interventions were tested on repository-level work.

- **Targeted tests beat generic test-driven instructions.** Telling the agent which tests the change affects cut regressions from 6.08% to 1.82%. "Adding TDD procedural instructions without targeted test context increased regressions to 9.94%—worse than no intervention at all" (Alonso et al., 2026). The sample is 100 tasks on one small open model, with no significance test. TREAT this as a guide.
- **Context first, then validate.** Across 19 agents, those that gather context before editing and spend more of their run on validation resolve more tasks. This is correlational, and run length is a confound. "Framework prompts do influence agent tactics, but this influence diminishes with stronger LLMs" (Mehtiyev & Assunção, 2026).
- **Execution feedback.** Feeding execution errors back for repair raises pass rates on function-level benchmarks; logic errors are hardest to repair (Arimbur, 2026).
- **Security feedback.** Agents and a standalone LLM all introduced vulnerabilities on SWE-bench issues; insecure patches went with broader modifications and with issues missing specific information (Sajadi et al., 2025). Feeding static-analysis warnings back fixed up to 55.5% of Copilot snippets' weaknesses (Fu et al., 2023). Three reflexion rounds raised the secure rate from 70.74% to 79.43%, "with the largest gains in the first round followed by diminishing returns" (Datta et al., 2025). Both were tested on snippets, not agent runs.

**Gap.** No controlled test of small diffs, plan-first, or LLM self-review without execution feedback on maintainability.

## 7. Repository instruction files (contested)

The studies disagree, and the disagreement tracks what they measure.

- In controlled benchmark tasks, "providing context files does not generally improve task success rates, while increasing inference cost by over 20% on average" (Gloaguen et al., 2026). Instructions were followed and led to more testing; repository overviews did not help. The authors recommend files contain only specific instructions not already evident in the codebase.
- In 10 repositories and 124 PRs, agents with AGENTS.md ran faster and used fewer output tokens at comparable completion (Lulla et al., 2026).
- Before and after a project added an instruction file, merge rate rose by at least 20% in 27.7% of projects and fell in 26.35% (Arabat & Sayagh, 2026). Projects that gained had longer, more structured files; this is exploratory.
- Developers' context files rarely state security or performance requirements (Chatlatanagulchai et al., 2025).

No study tests which content causes a gain, or the effect on maintainability or style. The comparison of the three designs above is mine; no paper compares them.

## 8. What the research could not find

- A controlled study of agent versus human correctness on the same tasks, beyond the follow-up-task experiment.
- Any test of unrequested features or defensive code as a behaviour, or of instructions against them.
- A benchmark for consistency with an existing codebase's conventions.
- Controlled tests of plan-first, small-diff, or self-review rules on repository work.
- Longitudinal studies over many months.
- Most numbers come from abstracts of preprints from the AIDev and SWE-bench ecosystems. Few have a second study behind them.

Open question (low priority): which terms sources use for agent code quality problems (CodeSlop, over-editing, comprehension debt, churn).

The research board is in `.research/code-better-quality/`.

## References

Alonso, P., Yovine, S., & Braberman, V. A. (2026). *TDAD: Test-driven agentic development – Reducing code regressions in AI coding agents via graph-based impact analysis*. arXiv. https://arxiv.org/abs/2603.17973

Arabat, A., & Sayagh, M. (2026). *Toward instructions-as-code: Understanding the impact of instruction files on agentic pull requests*. arXiv. https://arxiv.org/abs/2606.13449

Arimbur, J. J. (2026). *How many tries does it take? Iterative self-repair in LLM code generation across model scales and benchmarks*. arXiv. https://arxiv.org/abs/2604.10508

Chatlatanagulchai, W., Li, H., Kashiwa, Y., Reid, B., Thonglek, K., Leelaprute, P., Rungsawang, A., Manaskasemsak, B., Adams, B., Hassan, A. E., & Iida, H. (2025). *Agent READMEs: An empirical study of context files for agentic coding*. arXiv. https://arxiv.org/abs/2511.12884

Chen, Z., Sun, Z., Shi, Y., Peng, C., Gu, X., Lo, D., & Jiang, L. (2026). *Rethinking the value of agent-generated tests for LLM-based software engineering agents*. arXiv. https://arxiv.org/abs/2602.07900

Cynthia, S. T., Muttakin, A., & Roy, B. (2026). *Beyond bug fixes: An empirical investigation of post-merge code quality issues in agent-generated pull requests*. arXiv. https://arxiv.org/abs/2601.20109

Datta, A., Aljohani, A., & Do, H. (2025). *Secure code generation at scale with reflexion*. arXiv. https://arxiv.org/abs/2511.03898

Dente, F., Satriani, D., & Papotti, P. (2026). *Constraint decay: The fragility of LLM agents in backend code generation*. arXiv. https://arxiv.org/abs/2605.06445

Ehsani, R., Pathak, S., Rawal, S., Al Mujahid, A., Imran, M. M., & Chatterjee, P. (2026). *Where do AI coding agents fail? An empirical study of failed agentic pull requests in GitHub*. arXiv. https://arxiv.org/abs/2601.15195

Fu, Y., Liang, P., Tahir, A., Li, Z., Shahin, M., Yu, J., & Chen, J. (2023). *Security weaknesses of Copilot-generated code in GitHub projects: An empirical study*. arXiv. https://arxiv.org/abs/2310.02059

GitClear. (n.d.). *AI copilot code quality: 2025 look back at 12 months of data*. GitClear. https://www.gitclear.com/ai_assistant_code_quality_2025_research

Gloaguen, T., Mündler-Sasahara, N., Müller, M. N., Raychev, V., & Vechev, M. (2026). *Evaluating AGENTS.md: Are repository-level context files helpful for coding agents?* arXiv. https://arxiv.org/abs/2602.11988

He, H., Miller, C., Agarwal, S., Kästner, C., & Vasilescu, B. (2025). *Speed at the cost of quality: How Cursor AI increases short-term velocity and long-term complexity in open-source projects*. arXiv. https://arxiv.org/abs/2511.04427

Kraishan, O. (2026). *Not all agents are equal: Code quality and post-merge maintenance across five autonomous coding agents in the wild*. arXiv. https://arxiv.org/abs/2609.17598

Lulla, J. L., Mohsenimofidi, S., Galster, M., Zhang, J. M., Baltes, S., & Treude, C. (2026). *On the impact of AGENTS.md files on the efficiency of AI coding agents*. arXiv. https://arxiv.org/abs/2601.20404

Mathai, A., Iyer, S., Nogikh, A., Maniatis, P., Ivancic, F., Yang, J., & Ray, B. (2026). *TRIM: Reducing AI-generated CodeSlop via agent trajectory minimization*. arXiv. https://arxiv.org/abs/2607.18161

Mehtiyev, T., & Assunção, W. (2026). *Beyond resolution rates: Behavioral drivers of coding agent success and failure*. arXiv. https://arxiv.org/abs/2604.02547

Nakashima, S., Ishimoto, Y., Kondo, M., McIntosh, S., & Kamei, Y. (2026). *Why agentic-PRs get rejected: A comparative study of coding agents*. arXiv. https://arxiv.org/abs/2602.04226

Ogenrwot, D., & Businge, J. (2026). *How AI coding agents modify code: A large-scale study of GitHub pull requests*. arXiv. https://arxiv.org/abs/2601.17581

Patel, S., Hou, B. L., Purohit, A., Xu, K., Pan, J., He, H., & Chen, V. (2026). *Is agent code less maintainable than human code?* arXiv. https://arxiv.org/abs/2606.21804

Paul, D. G., Zhu, H., & Bayley, I. (2025). *Investigating the smells of LLM generated code*. arXiv. https://arxiv.org/abs/2510.03029

Peralta, S. R. O., Hoshi, F., Washizaki, H., Ubayashi, N., Kondo, I., Higo, Y., Mukai, H., Yoshida, N., Kusama, K., Tanaka, H., & Fan, Y. (2026). *Why are agentic pull requests merged or rejected? An empirical study*. arXiv. https://arxiv.org/abs/2605.22534

Sajadi, A., Damevski, K., & Chatterjee, P. (2025). *How safe are AI-generated patches? A large-scale study on security risks in LLM and agentic automated program repair on SWE-bench*. arXiv. https://arxiv.org/abs/2507.02976

Sawada, S., Shirai, T., Kashiwa, Y., Yamaguchi, K., Iwata, H., & Iida, H. (2026). *To what extent does agent-generated code require maintenance? An empirical study*. arXiv. https://arxiv.org/abs/2605.06464

Shayanfar, R., Gallaba, K., & Hassan, A. E. (2026). *Choosing coding-agent benchmarks for practice: Lessons from task demands and agent behaviour*. arXiv. https://arxiv.org/abs/2609.01271

Wang, G., Xu, Q., Briand, L., & Liu, K. (2025). *Mutation-guided unit test generation with a large language model*. arXiv. https://arxiv.org/abs/2506.02954

Watanabe, M., Li, H., Kashiwa, Y., Reid, B., Iida, H., & Hassan, A. E. (2025). *On the use of agentic coding: An empirical study of pull requests on GitHub*. arXiv. https://arxiv.org/abs/2509.14745

Whitfill, P., Wu, C., Becker, J., & Rush, N. (2026, March 10). *Many SWE-bench-passing PRs would not be merged into main*. METR. https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/

Yang, W., He, R., & Zhou, M. (2026). *A first look at coding agents' compliance with AI contribution rules in open-source communities*. arXiv. https://arxiv.org/abs/2607.26819

Zhong, M., Zhou, X., Chang, T.-Y., Wang, Q., Xu, N., Si, X., Garrette, D., Upadhyay, S., Liu, J., Han, J., Schillings, B., & Sun, J. (2025). *SWE-IF: Aligning code evaluation with human preference*. arXiv. https://arxiv.org/abs/2510.07315

Zhu, T., Lim, W. H., & Kan, M.-Y. (2026). *When models edit too much: On the fidelity of minimal code edits*. arXiv. https://arxiv.org/abs/2609.04061
