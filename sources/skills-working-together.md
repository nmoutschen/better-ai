# Designing skills that work together

Research findings · Search date: 11 November 2026

No skill format or harness gives one skill a portable way to declare or call another skill, so a skill that needs another can only name it in its text. Naming a skill does not make the agent load it, a skill that relies on another skill's internals breaks when that skill changes, and in Claude Code the calling skill can stop once the called skill returns. **No study tests the pattern these skills use, one skill naming another in prose with a fallback;** the findings below come from nearby evidence: skill triggering, bug reports, documentation and preprints.

**Scope.** How a skill calls, references, chains with or hands off to another skill, shares terms with it, and behaves when it is missing. Portability across harnesses is out of scope. The goal is to decide how better-ai skills should work together, starting with PRINCIPLES.md section 6.4.

**Status.** All high- and medium-priority questions are closed. The question on terms is contested (section 6). One low-priority question is open (section 8). Every claim used below was checked against its page. Most academic sources are 2026 arXiv preprints read at abstract level.

## 1. What skill formats and harnesses provide

None of the five documents read defines a way for one skill to declare a dependency on another skill, or to call it. The Agent Skills specification lists the fields `name`, `description`, `license`, `compatibility`, `metadata` and an experimental `allowed-tools`, and its only cross-file mechanism is file references inside one skill, kept "one level deep from `SKILL.md`" (Agent Skills, n.d.).

Each harness has its own controls, none of them portable:

| Harness | What it provides |
|---|---|
| Claude Code | `Skill(name)` permission rules; `context: fork` with an `agent` field runs a skill in a subagent; `disable-model-invocation` (Anthropic, n.d.-a); plugin-level `dependencies` in `plugin.json` (Anthropic, n.d.-b) |
| Hermes | Skills shown only when named toolsets are present (`requires_toolsets`) or missing (`fallback_for_toolsets`); bundles of skills (Nous Research, n.d.) |
| Codex | Tool dependencies in `openai.yaml`; `allow_implicit_invocation` (OpenAI, n.d.) |
| Cursor | `disable-model-invocation` (Cursor, n.d.) |

These controls concern tools and invocation, not one skill depending on another.

## 2. Whether a named skill gets loaded

No study measures whether an agent loads a skill named inside another skill. Nearby evidence points the same way:

- In Vercel's evals, the agent never invoked an available skill in 56% of cases by default; an explicit instruction raised the trigger rate to 95%+. The model and number of cases are not stated (Gao, 2026).
- A user reported that the agent skipped a skill its own instructions required and ran the workflow from memory, missing a phase (coreyDavisFF, 2026).
- Destefanis (2026) says the agent's decision to apply a skill "is probabilistic. There is no compiler or type system confirming that the right skill fired."
- Two Claude Code bug reports say the calling skill stops after the called skill finishes, so its later steps never run, even with "MANDATORY CONTINUATION" text in the skill (jaried, 2026; virhdr, 2026). On 11 November 2026, one was closed as a duplicate and the other for inactivity after a commenter reproduced it on version 2.1.86; neither was closed as fixed.

## 3. What goes wrong when skills are combined

- Overlapping skill scopes raised reported ownership conflicts from 0/16 to 14/16 audited cases, and bland trigger descriptions raised routing conflicts from 3/32 to 30/32 and loaded 3.7 times more skill tokens (Kang Ruiyuan, 2026).
- Skill-use precision fell from 29.6% to 3.3% as the pool of available skills grew from 5 to 100 (Jiang et al., 2026).
- Of 211,575 pairs of skills that each passed inspection, 22.25% were flagged as structural risk candidates, and about one in five flagged hits held up as real risks (Wang et al., 2026).

All three are preprints read at abstract level, with the authors' own unreplicated numbers.

## 4. Coupling and handoff practice

- Destefanis (2026): "a skill that relies on the internal behaviour or output format of another skill, or on a shared resource, is coupled to it, so that a change to one can break the other. Such dependencies are kept few and made explicit." The paper also recommends one responsibility per skill.
- Anthropic's authoring guide asks for one term per concept, output templates, and a plan file validated before execution, but says nothing about one skill referencing another (Anthropic, n.d.-c).
- Blogs and tutorials describe an orchestrating skill that tells the model to invoke sub-skills by name, with each sub-skill still usable alone, and recommend that chained skills declare inputs and predictable output formats. These are low-trust sources with no measurements.

## 5. When a referenced skill is missing

Harness-level dependencies behave differently: a Claude Code plugin whose dependency is missing fails to load (Anthropic, n.d.-b), while a Hermes bundle skips its missing skills (Nous Research, n.d.). In a study of 1.43 million skills, 8.92% had direct dependencies on other skills, fields that could declare dependencies appeared in only 1.40% of skills, and 30.41% of root skills with dependencies contained a skill in a cycle (Jia et al., 2026). The authors recommend typed dependency manifests. No evidence was found on how well instruction-level fallbacks ("if available, otherwise do X") work.

## 6. Terms

Sources use terms loosely and do not agree. "Layering" means several skills active in one context in one guide, and a higher-level skill orchestrating lower-level ones in another. Stacking, chaining, delegation and orchestration have no shared definitions. This question is contested.

## 7. Structured composition

Running skills in a planned order (a DAG) "substantially outperforms native flat invocation even when given the identical skill set" (Li et al., 2026). This concerns task pipelines built by a framework, not skills naming each other in prose.

## 8. What the research could not find

- A study of one skill naming another skill in its text.
- Evidence on instruction-level fallbacks.
- A source that says where comparisons with software modularity (Unix pipes, header files) stop working.
- Open, low priority: what agent-to-agent handoff protocols could teach about skill handoffs.

## References

- Agent Skills. (n.d.). *Specification*. agentskills.io. https://agentskills.io/specification
- Anthropic. (n.d.-a). *Extend Claude with skills*. Claude Code documentation. https://code.claude.com/docs/en/skills
- Anthropic. (n.d.-b). *Plugin dependencies*. Claude Code documentation. https://code.claude.com/docs/en/plugin-dependencies.md
- Anthropic. (n.d.-c). *Skill authoring best practices*. Claude API Docs. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- coreyDavisFF. (2026, April 27). *Agent ignored skill invocation requirement and skipped workflow phases* (Issue #54049). GitHub, anthropics/claude-code. https://github.com/anthropics/claude-code/issues/54049
- Cursor. (n.d.). *Agent Skills*. Cursor documentation. https://cursor.com/docs/context/skills
- Destefanis, G. (2026, July 27). *Authoring agent skills: A software-engineering approach* (arXiv:2607.25032). arXiv. https://arxiv.org/html/2607.25032
- Gao, J. (2026, January 27). *AGENTS.md outperforms skills in our agent evals*. Vercel. https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
- jaried. (2026, March 2). *[BUG] Parent skill halts entirely after nested skill completes — remaining steps never execute* (Issue #30028). GitHub, anthropics/claude-code. https://github.com/anthropics/claude-code/issues/30028
- Jia, C., Zhao, T., He, R., & Zhou, M. (2026, July 1). *Skills are not islands: Measuring dependency and risk in agent skill supply chains* (arXiv:2607.01136). arXiv. https://arxiv.org/html/2607.01136
- Jiang, Z., Huang, F., Xing, H., Wu, X., Gao, Y., Cao, R., Wang, M., Liu, S., & Li, Y. (2026, August 14). *Demystifying agent skills: Why they work—until they don't* (arXiv:2608.14036). arXiv. https://arxiv.org/abs/2608.14036
- Kang Ruiyuan. (2026, September 10). *SkillSeam: Six principles for auditing agent skill collections* (arXiv:2609.13321). arXiv. https://arxiv.org/abs/2609.13321
- Li, H., Mu, C., Chen, J., Ren, S., Cui, Z., Zhang, Y., Bai, L., & Hu, S. (2026). *Organizing, orchestrating, and benchmarking agent skills at ecosystem scale* (arXiv:2603.02176). arXiv. https://arxiv.org/abs/2603.02176
- Nous Research. (n.d.). *Skills system*. Hermes Agent documentation. https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- OpenAI. (n.d.). *Build skills*. OpenAI Developers. https://learn.chatgpt.com/docs/build-skills
- virhdr. (2026, January 29). *[BUG] Skill workflow stops after sub-skill invocation despite MANDATORY CONTINUATION directives* (Issue #21672). GitHub, anthropics/claude-code. https://github.com/anthropics/claude-code/issues/21672
- Wang, S., Qian, P., Chen, Y., You, J., Wang, X., Jiang, X., Liu, L., Yu, H., & Xu, J. (2026, May 30). *When safe skills collide: Measuring compositional risk in agent skill ecosystems* (arXiv:2606.00448). arXiv. https://arxiv.org/abs/2606.00448
