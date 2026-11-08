# Tooling to evaluate the skills across agent harnesses

Research findings · Search date: 8 November 2026

No single tool covers the evaluation method in `evaluating-agent-skills.md` across harnesses. Four independent open-source tools run a skill inside real agent CLIs and compare runs with and without it: Caliper, agent-exam, agent-skill-eval and Skillgrade. Two large companies have since released similar tools: Alibaba's skill-up and NVIDIA's SkillEvaluator. **None of them drives a simulated user over several turns, and none packages a way to test a judge on deliberately damaged outputs.** Those two parts must come from general evaluation frameworks or be built. Gemini CLI is the weakest harness to cover: no tool found detects when it loads a skill.

**Scope.** Tools that run SKILL.md skills in more than one coding-agent harness and evaluate them: runs with and without the skill, repeated runs, automatic checks on files and transcripts, LLM judges that can be validated, simulated users, and tests of whether a skill loads from its description. The goal is to decide which tools to adopt, combine or build. This report does not design the evaluation.

**Status.** All high- and medium-priority questions are answered. One low-priority question is open (section 11). Every claim used below was checked against its page; one claim on the board stayed unverified and is not used. All tool descriptions come from each tool's own documentation or source code. No tool was installed or run.

## Findings at a glance

The table compares the four skill-evaluation tools found. "Not read" means the research did not find the answer, not that the tool lacks the feature.

| | Caliper | agent-exam | agent-skill-eval | Skillgrade |
|---|---|---|---|---|
| Harnesses | Claude Code, Codex, Pi, Hermes | Claude Code, Codex CLI, Copilot CLI, OpenCode | Claude Code, Codex, OpenCode | Gemini CLI, Claude Code, Codex CLI, OpenCode, ACP agents, any command |
| Skill installed natively | Yes, fresh home and empty working directory | Not read | Yes, fresh workspace per case | Not read; runs in Docker by default |
| Run without the skill | Yes | Not read | Yes | Not read |
| Automatic checks | Python assertions on the working directory | `file_exists`, `tool_called`, `skill_invoked` | State-diff checks | Deterministic scripts |
| Common transcript format | Yes | Yes | Not read | Not read |
| Detects skill loading | Yes, not Gemini CLI | Yes, not Gemini CLI | Trigger and negative cases; detection not read | Not read |
| LLM judge | Yes; judge model can differ from the agent | Not read | LLM rubric | LLM rubric, plus human graders |
| GitHub stars (8 Nov 2026) | 230 | 2 | 4 | 735 |

Three more tools were found late in the research and were not compared on these rows:

- **skill-ab-eval** runs Claude Code, Codex, Gemini and Antigravity, but it pastes the skill into the prompt instead of installing it (section 1).
- **skill-up** (Alibaba) runs Claude Code, Codex, Qoder CLI and Qwen Code (Alibaba, n.d.). It has 1,439 GitHub stars.
- **SkillEvaluator** (NVIDIA) runs Codex, Claude Code and OpenCode, and its docs mark that support as Experimental (NVIDIA, n.d.).

## 1. Running a skill with and without it

Four tools say they drive real agent CLIs with a skill (Donadei, n.d.-a; Gechev, n.d.; tardigrde, 2026; zytedata, n.d.-a). None of the pages read lists which harness versions are supported. agent-skill-eval records "agent CLI version, and harness version" for each run (tardigrde, 2026).

How the skill reaches the agent differs, and it matters:

- **Caliper** says: "Every attempt installs your skill where the agent looks for it, never pasted into the prompt, in a fresh home with an empty working directory" (Donadei, 2026).
- **agent-skill-eval** installs the skill into each harness's own skill directory, and "every case gets its own workspace so state does not leak between cases." It does not block the user's own configuration: "agents silently inherit their own local config (e.g. `~/.codex/config.toml`)" unless flags are set (tardigrde, 2026).
- **skill-ab-eval** pastes the skill's text into the prompt ("Follow these instructions exactly") instead of installing it (cskwork, 2026b). Its own example shows a leak: the skill "shows **0.00 lift** because the user's global `CLAUDE.md` already mandates the same conventions" (cskwork, 2026a).

**The practical consequence:** a tool that pastes the skill cannot test triggering, and it measures a different mechanism from the one users get. Runs also need the user's global configuration kept out. Otherwise the baseline already contains part of the skill.

## 2. Automatic checks and transcripts

Caliper and agent-exam each turn every harness's output into one transcript format through per-harness adapters, so the same assertions work in every harness (Donadei, n.d.-b; zytedata, n.d.-a). Caliper's `assert:` "runs locally as Python, in the attempt's workdir," and its `activates:` check "asserts which skills the agent chose to load. It needs no judge" (Donadei, 2026). agent-exam offers `file_exists`, `tool_called` and `skill_invoked` (zytedata, n.d.-b).

Claude Code, Gemini CLI and Codex each have a non-interactive mode with JSON event output that includes tool calls and token usage (Anthropic, n.d.-b; Google, n.d.-a; OpenAI, n.d.-b). Two isolation flags matter here:

- Claude Code's `--bare` mode also removes the list of skills, so it cannot be used for trigger tests (Anthropic, n.d.-b).
- Codex has flags to ignore user configuration and rules (OpenAI, n.d.-b). No equivalent was found for Gemini CLI.

## 3. Detecting that a skill loaded

The Agent Skills guide tests triggering with labelled requests run several times, and reads loading from the client's tool-call history. Its example covers Claude Code only (Agent Skills project, n.d.-b). Two tools detect loading in other harnesses, each with rules for each harness:

- **Caliper** counts a dedicated skill tool call (Claude Code, Hermes), or any tool call that reads a `<name>/SKILL.md` path (Codex, Pi) (Donadei, n.d.-c).
- **agent-exam** reads Codex's reads of SKILL.md, OpenCode's `skill` tool events and Copilot CLI's `skill` tool requests (zytedata, n.d.-c, n.d.-d, n.d.-e).

Neither detects loading in Gemini CLI. Gemini's docs name an `activate_skill` tool (Google, n.d.-b), but whether it shows in Gemini's JSON output was not checked.

## 4. Where harnesses look for skills

Most harnesses read a shared `.agents/skills/` directory. Gemini CLI, OpenCode, Copilot and Codex document it (Google, n.d.-b; OpenCode, n.d.; GitHub, n.d.; OpenAI, n.d.-a). Claude Code's docs list only `.claude/skills/` (Anthropic, n.d.-a), so an evaluation needs a copy or link there. One Google codelab says Antigravity CLI reads `.agents/skills/` in the project, but it gives two different global paths (Google, n.d.-c). Test this against the installed CLI.

## 5. LLM judges and their validation

Promptfoo and Inspect let the user choose the judge model, and Inspect can combine a panel of judges (Promptfoo, 2026; UK AI Security Institute, n.d.). Caliper lets the judge differ from the agent being tested, and warns when compared runs used different judges (Donadei, n.d.-a).

Validating a judge is mostly left to the user:

- **Agreement with human labels:** small tools compute it. kappa computes Cohen's kappa offline (yishaik, n.d.). Potato computes kappa and position-swap consistency (Potato project, n.d.). Ragas and MLflow measure plain agreement and can tune the judge's prompt (Ragas, n.d.; MLflow, n.d.).
- **Answer order:** Phoenix can "call the judge twice (once in each order) and only return a winner when both calls agree" (Arize Phoenix, n.d.).
- **The metric is contested:** the kappa tools report kappa. Husain's validate-evaluator procedure argues for true-positive and true-negative rates instead (Husain, n.d.).
- **Damaged outputs:** no packaged tool was found. This test must be built.

## 6. Simulated users

No skill-evaluation tool documents a simulated user. General frameworks do. Promptfoo has a simulated-user provider that stops at a maximum number of turns, and its Claude Agent SDK provider supports resuming a session (Promptfoo, n.d.-b, n.d.-c). DeepEval's ConversationSimulator and the early-stage inspect_multiturn also supply one (Confident AI, n.d.; aschriner, n.d.). In each case the user must connect the agent CLI to the simulator themselves.

Two general frameworks can run agents as the system under test. Promptfoo has providers for the Claude Agent SDK and the Codex SDK; with Codex, skill use is only inferred (Promptfoo, n.d.-c, n.d.-d). Inspect SWE runs Claude Code, Codex CLI, Gemini CLI and others in a sandbox (Meridian Labs, n.d.).

## 7. What can skew a comparison across harnesses

- **Model and harness change together.** LH-Bench compares harness-and-model pairs, and notes that Claude models are trained with awareness of the Agent Skills format (Chandwani & Gupta, 2026).
- **The skill reaches the model differently.** In LH-Bench, Codex received the skill inside the system prompt, while Claude Code and Gemini CLI found it in a directory. The gain from the skill differed by harness (Codex +0.87, Claude Code +0.15, Gemini CLI +0.05), but with only 2–3 runs per harness, which the authors call directional (Chandwani & Gupta, 2026).
- **Usage is counted differently.** Harnesses report tokens differently, so cost comparisons need one counting method (Bob, 2026).
- **The harness itself must be reported.** One preprint argues harness differences can outweigh model differences (Zhang et al., 2026).

## 8. Cost and terms

All three vendors meter subscription sign-in separately from API keys:

- **Anthropic** says plan limits assume ordinary individual use. It says developers "building products or services ... including those using the Agent SDK, should use API key authentication" (Anthropic, n.d.-c). Whether one person's own eval batch on their own subscription is acceptable is not stated explicitly.
- **OpenAI** describes the Codex API key as "great for automation in shared environments like CI" (OpenAI, n.d.-c).
- **Gemini CLI** documents daily request quotas that differ by sign-in method (Gemini CLI, n.d.).

No source gives a ceiling that a many-run evaluation would hit.

## 9. Adoption

Tools built to evaluate skills are young and little used, but general evaluation frameworks are not. GitHub stars on 8 November 2026 (GitHub, 2026):

| Repository | What it is | Created | Stars |
|---|---|---|---|
| anthropics/skills | The skills themselves | Sep 2025 | 189,084 |
| promptfoo | General LLM evaluation | Apr 2023 | 26,950 |
| deepeval | General LLM evaluation | Aug 2023 | 19,363 |
| inspect_ai | General LLM evaluation | Nov 2023 | 3,204 |
| skill-up (Alibaba) | Skill evaluation | May 2026 | 1,439 |
| Skillgrade | Skill evaluation | Feb 2026 | 735 |
| Caliper | Skill evaluation | May 2026 | 230 |
| inspect_swe | Inspect add-on that runs agent CLIs | Aug 2025 | 41 |
| agent-skill-eval, agent-exam, skill-ab-eval | Skill evaluation | 2026 | 0–4 |

Stars measure attention, not use or maintenance.

## 10. Why these tools are new

The tools are new because the format is new. Anthropic announced Agent Skills in October 2025. Most other harnesses added support by January 2026, and every skill-evaluation tool found appeared between February and August 2026. Researchers also say that until 2026 there was no benchmark for whether skills help. Practitioners say almost nobody tests their skills, but no one has counted.

### 10.1. Timeline

| Date | Event |
|---|---|
| 2025-10-16 | Anthropic announces Agent Skills (Anthropic, 2025). The anthropics/skills repository was created on 2025-09-22 (GitHub, 2026). |
| 2025-12-02 | Codex prototype, "an **experimental** feature for internal testing" (openai/codex contributors, 2025) |
| 2025-12-16 | First commit of the open specification repository (agentskills/agentskills contributors, 2025) |
| 2025-12-18 | GitHub Copilot supports Agent Skills (GitHub, 2025) |
| 2025-12-22 | OpenCode v1.0.186: "Added Agent Skills support" (OpenCode team, 2025) |
| 2026-01-07 | Gemini CLI v0.24.0-preview.0 adds skill infrastructure (Google Gemini CLI team, 2026) |
| 2026-02 | SkillsBench preprint (Li et al., 2026); Skillgrade repository created (GitHub, 2026) |
| 2026-03-03 | Anthropic adds evals and a benchmark mode to skill-creator, for Claude products only (Anthropic, 2026) |
| 2026-05 | Caliper, agent-skill-eval, skill-ab-eval and skill-up repositories created (GitHub, 2026) |
| 2026-07-30 | agent-exam repository created (GitHub, 2026) |
| 2026-08-19 | NVIDIA announces SkillEvaluator (Abramovitch et al., 2026) |

Claude Code's changelog says "Added support for Claude Skills" in version 2.0.20, but the entry has no date (Anthropic, n.d.-d). The dates for other harnesses are the earliest release notes found, not proven firsts.

### 10.2. What the builders say was missing

The research papers name a measurement gap:

- SkillsBench: "no benchmark systematically evaluates how and when Skills improve agent performance" (Li et al., 2026).
- SkillTester: "systematic benchmark-based evaluation remains limited," and "selection often depends on indirect signals such as popularity, ranking, developer reputation, or surface-level documentation" (Wang et al., 2026).
- SkillAudit: adoption relies "on README claims, star counts, and download figures ... rather than on direct empirical evaluation evidence." Fixed task suites "can conflate a skill's marginal contribution with backbone strength" (Yu et al., 2026).

The vendor tools do not name a gap in earlier tools. NVIDIA says it built SkillEvaluator to measure whether skills improve agent results (Abramovitch et al., 2026). Anthropic's skill-creator evals work only in Claude products (Anthropic, 2026). OpenAI published a guide for evaluating skills with Codex, not a packaged tool (OpenAI, n.d.-d).

### 10.3. How often skills are tested

No survey or count was found. Practitioners say testing is rare. One wrote, "Almost nobody is testing them and most of them are AI-generated" (Schmid, 2026a). Expo describes its own earlier practice: "try a prompt ourselves, watch the agent do something sensible, and feel good about the result" (Shukla et al., 2026). A talk says its authors "indexed more than 50,000 skills from GitHub, with almost none carrying evaluations," but gives no method (Schmid, 2026b), so it is not used as evidence here.

### 10.4. Older methods, and what skills add

Before skills, instruction files such as AGENTS.md were tested the same way: the same tasks run with and without the file. Those studies found little gain. Providing context files "does not generally improve task success rates" (Gloaguen et al., 2026). One paired study found "comparable task completion behavior" (Lulla et al., 2026). In an observational study, "27.7% of the projects increased their merge rate by at least 20%, while 26.35% decreased it" (Arabat & Sayagh, 2026).

Skills add a problem that always-loaded files do not have: the skill must load. In Vercel's evaluation, "in 56% of eval cases, the skill was never invoked" (Gao, 2026). No source tested instruction files and skills under one protocol. That the with-and-without method carries over to skills is an inference.

### 10.5. Why skills are hard to evaluate

One preprint backs several difficulties with data. It found that static scores of a skill do not predict its effect in live runs, across 62 skills. It also notes that "a positive aggregate does not mean every skill helps every agent" (Kevin et al., 2026). A practitioner guide adds that "the same skill can behave differently depending on the agent framework running it" (Schmid, 2026a). This rests mostly on one preprint, of which only part was read.

### 10.6. What this means for choosing a tool

This is an inference from the findings above, not a finding. Every skill-evaluation tool is less than nine months old, and none has a long maintenance record. Expect breaking changes. Keep test cases in a format independent of any one tool, so the runner can be replaced.

## 11. What the research could not find

| Gap | Effect on the decision |
|---|---|
| No tool detects skill loading in Gemini CLI | Trigger tests in Gemini CLI need a detector built and checked by hand |
| No packaged test of judges on damaged outputs | Build it, as the eval method requires |
| No skill-evaluation tool with a simulated user | Connect a general framework's simulator to the agent CLI |
| Skillgrade's install method, isolation and loading detection not read | Read its code or run it before choosing it, despite it having the widest harness list |
| Coder Eval, harness-cli, skill-cert and skill-forge-eval appeared only in search summaries | They may change the comparison |
| Low priority, open: which tools report variance or paired comparisons | Repeated-run statistics may need to be computed outside the tool |
| Most tools are under a year old and have few users | Expect breaking changes; record the tool version with results |
| skill-up and SkillEvaluator were not compared on install method, isolation, checks or loading detection | Read or try them before choosing |
| No count of skill authors who evaluate their skills | How rare testing is rests on practitioner statements |
| No dated release note for Claude Code's or Antigravity CLI's skill support | The timeline's start for those two harnesses is approximate |

The research board is at `.research/eval-tooling-across-harnesses/`.

## References

Abramovitch, M., Kevin, C., Raghavan, N., Puget, J.-F., & Swaminathan, N. (2026, August 19). *Evaluating AI agent skill performance with NVIDIA SkillEvaluator*. NVIDIA Technical Blog. https://developer.nvidia.com/blog/evaluating-ai-agent-skill-performance-with-nvidia-skillevaluator/

Agent Skills project. (n.d.-a). *How to add skills support to your agent*. agentskills.io. https://agentskills.io/client-implementation/adding-skills-support

Agent Skills project. (n.d.-b). *Optimizing skill descriptions*. agentskills.io. https://agentskills.io/skill-creation/optimizing-descriptions

agentskills/agentskills contributors. (2025, December 16). *init* [First commit]. GitHub. https://github.com/agentskills/agentskills

Alibaba. (n.d.). *skill-up README*. GitHub. https://raw.githubusercontent.com/alibaba/skill-up/main/README.md

Anthropic. (n.d.-a). *Extend Claude with skills*. Claude Code Docs. https://code.claude.com/docs/en/skills

Anthropic. (n.d.-b). *Run Claude Code programmatically*. Claude Code Docs. https://code.claude.com/docs/en/headless

Anthropic. (n.d.-c). *Legal and compliance*. Claude Code Docs. https://code.claude.com/docs/en/legal-and-compliance

Anthropic. (n.d.-d). *claude-code CHANGELOG.md*. GitHub. https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md

Anthropic. (2025, October 16). *Introducing Agent Skills*. Claude blog. https://claude.com/blog/skills

Anthropic. (2026, March 3). *Improving skill-creator: Test, measure, and refine Agent Skills*. Claude blog. https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills

Arabat, A., & Sayagh, M. (2026, June 11). *Toward instructions-as-code: Understanding the impact of instruction files on agentic pull requests*. arXiv. https://arxiv.org/abs/2606.13449

Arize Phoenix. (n.d.). *Pairwise evaluator*. Arize Phoenix docs. https://www.arize.com/docs/phoenix/evaluation/server-evals/code-evaluators/pairwise

aschriner. (n.d.). *inspect_multiturn*. GitHub. https://github.com/aschriner/inspect_multiturn

Bob. (2026, March 20). *Cross-harness evals: The missing piece of agent comparison*. timetobuildbob.com. http://timetobuildbob.com/blog/cross-harness-evals-the-missing-piece-of-agent-comparison

Chandwani, A., & Gupta, I. (2026, May 29). *LH-Bench: Skill-grounded evaluation of long-horizon agents on subjective enterprise tasks* (arXiv:2603.22744v2). arXiv. https://arxiv.org/html/2603.22744

Confident AI. (n.d.). *Conversation simulator*. DeepEval documentation. https://deepeval.com/docs/conversation-simulator

cskwork. (2026a). *skill-ab-eval README*. GitHub. https://github.com/cskwork/skill-ab-eval

cskwork. (2026b). *skill-ab-eval scripts/run_eval.py* [Source code]. GitHub. https://github.com/cskwork/skill-ab-eval/blob/main/skills/skill-ab-eval/scripts/run_eval.py

Donadei, E. (n.d.-a). *Caliper backends documentation (docs/backends.md)*. GitHub. https://raw.githubusercontent.com/edonadei/caliper/main/docs/backends.md

Donadei, E. (n.d.-b). *Caliper results documentation (docs/results.md)*. GitHub. https://raw.githubusercontent.com/edonadei/caliper/main/docs/results.md

Donadei, E. (n.d.-c). *caliper/activation.py* [Source code]. GitHub. https://github.com/edonadei/caliper/blob/main/caliper/activation.py

Donadei, E. (2026, November 5). *caliper-eval 0.22.0: A lightweight evaluation harness for agent skills*. PyPI. https://pypi.org/project/caliper-eval/

Gao, J. (2026, January 27). *AGENTS.md outperforms skills in our agent evals*. Vercel. https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals

Gechev, M. (n.d.). *Skillgrade*. GitHub. https://github.com/mgechev/skillgrade

Gemini CLI. (n.d.). *Gemini CLI: Quotas and pricing*. geminicli.com. https://geminicli.com/docs/resources/quota-and-pricing/

GitHub. (n.d.). *Agent skills*. GitHub Docs. https://docs.github.com/en/copilot/concepts/agents/about-agent-skills

GitHub. (2025, December 18). *GitHub Copilot now supports Agent Skills*. GitHub Changelog. https://github.blog/changelog/2025-12-18-github-copilot-now-supports-agent-skills/

GitHub. (2026, November 8). *Repository metadata* [GitHub REST API, retrieved with gh]. https://api.github.com/repos/

Gloaguen, T., Mündler-Sasahara, N., Müller, M. N., Raychev, V., & Vechev, M. (2026, February 12). *Evaluating AGENTS.md: Are repository-level context files helpful for coding agents?* arXiv. https://arxiv.org/abs/2602.11988

Google Gemini CLI team. (2026, January 7). *Gemini CLI v0.24.0-preview.0 release notes*. GitHub. https://github.com/google-gemini/gemini-cli/releases/tag/v0.24.0-preview.0

Google. (n.d.-a). *Headless mode reference*. GitHub (google-gemini/gemini-cli). https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/headless.md

Google. (n.d.-b). *Agent skills*. GitHub (google-gemini/gemini-cli). https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/cli/skills.md

Google. (n.d.-c). *Authoring Google Antigravity skills*. Google Codelabs. https://codelabs.developers.google.com/getting-started-with-antigravity-skills

Husain, H. (n.d.). *validate-evaluator (skills/validate-evaluator/SKILL.md)*. GitHub. https://github.com/hamelsmu/evals-skills/blob/main/skills/validate-evaluator/SKILL.md

Kevin, C., Raghavan, N., Puget, J.-F., Malani, R., Puvvadi, M., Abramovitch, M., Gupta, M., Akkiraju, R., Prabhu, S., Dangi, Y., Luo, W., & Lee, S. H. (2026, August 20). *Evaluating skills, not just agents: Agentic continuous evaluation of skills* (arXiv:2608.20614v1). arXiv. https://arxiv.org/html/2608.20614

Li, X., Chen, W., Liu, Y., et al. (2026). *SkillsBench: Benchmarking how well agent skills work across diverse tasks*. arXiv. https://arxiv.org/html/2602.12670v1

Lulla, J. L., Mohsenimofidi, S., Galster, M., Zhang, J. M., Baltes, S., & Treude, C. (2026, January 28). *On the impact of AGENTS.md files on the efficiency of AI coding agents*. arXiv. https://arxiv.org/abs/2601.20404

Meridian Labs. (n.d.). *Inspect SWE: Software engineering agents for Inspect AI*. https://meridianlabs-ai.github.io/inspect_swe/

MLflow. (n.d.). *Judge alignment: Teaching AI to match human preferences*. MLflow documentation. https://www.mlflow.org/docs/latest/genai/eval-monitor/scorers/llm-judge/alignment/

NVIDIA. (n.d.). *SkillEvaluator: Tier 3 live evaluation*. NVIDIA docs. https://docs.nvidia.com/skills/skillevaluator/tier3-live-evaluation.md

OpenAI. (n.d.-a). *Build skills*. OpenAI Codex docs. https://learn.chatgpt.com/docs/build-skills

OpenAI. (n.d.-b). *Non-interactive mode*. OpenAI Codex docs. https://learn.chatgpt.com/docs/non-interactive-mode

OpenAI. (n.d.-c). *Pricing*. OpenAI Codex docs. https://learn.chatgpt.com/docs/pricing.md

OpenAI. (n.d.-d). *Testing agent skills systematically with evals*. OpenAI Developers. https://developers.openai.com/blog/eval-skills.md

openai/codex contributors. (2025, December 2). *feat: experimental support for skills.md (#7412)* [Commit]. GitHub. https://github.com/openai/codex/commit/a8d5ad37b8115068ff777b66ab9299cdab85cdd7

OpenCode team. (2025, December 22). *OpenCode v1.0.186 release notes*. GitHub. https://github.com/sst/opencode/releases/tag/v1.0.186

OpenCode. (n.d.). *Skill discovery and loading in OpenCode*. OpenCode documentation. https://opencode.ai/docs/skills/

Potato project. (n.d.). *LLM-judge <-> human alignment*. Potato documentation. https://potatoannotator.readthedocs.io/en/latest/agent-evaluation/judge_alignment/

Promptfoo. (n.d.-a). *Test agent skills*. Promptfoo documentation. https://www.promptfoo.dev/docs/guides/test-agent-skills/

Promptfoo. (n.d.-b). *Simulated user*. Promptfoo documentation. https://www.promptfoo.dev/docs/providers/simulated-user/

Promptfoo. (n.d.-c). *Claude Agent SDK*. Promptfoo documentation. https://www.promptfoo.dev/docs/providers/claude-agent-sdk/

Promptfoo. (n.d.-d). *OpenAI Codex SDK*. Promptfoo documentation. https://www.promptfoo.dev/docs/providers/openai-codex-sdk/

Promptfoo. (2026, November 7). *Model-graded metrics*. Promptfoo documentation. https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded

Ragas. (n.d.). *How to align an LLM as a judge*. Ragas documentation. https://docs.ragas.io/en/latest/howtos/applications/align-llm-as-judge/

Schmid, P. (2026a, March 4). *Practical guide to evaluating and testing agent skills*. philschmid.de. https://www.philschmid.de/testing-skills

Schmid, P. (2026b). *Don't ship skills without evals* [Conference talk]. AI Engineer World's Fair 2026. https://www.ai.engineer/talks/0vphxNt4wyk-dont-ship-skills-without-evals

Shukla, A., Gupta, K., Tingle, D., Chien, K., Vatne, B., & Mokos, D. (2026, October 8). *Your skills need an evaluation mechanism*. Expo. https://expo.dev/blog/your-skills-need-an-evaluation-mechanism.md

tardigrde. (2026). *agent-skill-eval README*. GitHub. https://github.com/tardigrde/agent-skill-eval

UK AI Security Institute. (n.d.). *Model grading*. Inspect documentation. https://inspect.aisi.org.uk/model-graded.html

Wang, L., Wang, Z., & Xu, A. (2026, March 28). *SkillTester: Benchmarking utility and security of agent skills*. arXiv. https://arxiv.org/html/2603.28815v1

yishaik. (n.d.). *kappa: A tiny, zero-dependency evaluation kit for LLM-as-a-Judge*. GitHub. https://github.com/yishaik/kappa

Yu, D., Li, Y., Guan, Z., et al. (2026, June 21). *SkillAudit: From fixed-suite benchmarking to skill-centered assessment*. arXiv. https://arxiv.org/html/2606.22613

Zhang, Y., Wang, J., Ge, Y., Xu, W., Hamm, J., & Reddy, C. K. (2026, May 7). *Stop comparing LLM agents without disclosing the harness*. arXiv. https://arxiv.org/abs/2605.23950

zytedata. (n.d.-a). *agent-exam README*. GitHub. https://github.com/zytedata/agent-exam

zytedata. (n.d.-b). *agent-exam quick start*. Read the Docs. https://agent-exam.readthedocs.io/en/stable/quick-start.html

zytedata. (n.d.-c). *agent_exam/providers/codex_cli/stream_parser.py* [Source code]. GitHub. https://github.com/zytedata/agent-exam/blob/main/agent_exam/providers/codex_cli/stream_parser.py

zytedata. (n.d.-d). *agent_exam/providers/opencode/stream_parser.py* [Source code]. GitHub. https://github.com/zytedata/agent-exam/blob/main/agent_exam/providers/opencode/stream_parser.py

zytedata. (n.d.-e). *agent_exam/providers/copilot_cli/stream_parser.py* [Source code]. GitHub. https://github.com/zytedata/agent-exam/blob/main/agent_exam/providers/copilot_cli/stream_parser.py
