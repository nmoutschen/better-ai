# Blackboard techniques and delegation for the research-better skill

Research register · Search date: 7 November 2026

**Scope.** What blackboard architectures, multi-agent research systems, and multi-agent failure studies imply for a research skill that keeps an open-question register, delegates to cheaper sub-agents, and runs across several AI harnesses.

**Status.** Questions answered across sections 1.1–1.7; five left open (section 4). The evidence for LLM blackboard systems comes from benchmarks of maths, reasoning, and data discovery, not open-web research. Applying it to research-better is a design inference, and section 3 labels it as one.

## 1. Findings

### 1.1. LLM blackboard systems

**LbMAS** (Han & Zhang, 2025). A shared board replaces each agent's own memory. Agents communicate only through the board. An LLM control unit "iteratively selects agents based on query q, current messages B on the blackboard and agent abilities." Five fixed roles: planner, decider (stops when the board holds enough), critic ("points out errors in messages on the blackboard"), conflict-resolver (sends contradicting agents to discuss), and cleaner ("detects useless or redundant messages and removes them"). The loop is capped at 4 rounds.
- Ablation: removing the control unit raised MATH tokens from 4.7M to 13.9M at similar accuracy. Marking redundant messages instead of removing them lowered accuracy on all three datasets.
- Limits: maths and reasoning benchmarks, one run per setting, no variance reported. Some figures differ between the text and the tables.

**Blackboard for data discovery** (arXiv 2510.01285v2, 2025). A main agent posts requests without naming a recipient. Helper agents decide whether they can answer. Each answer goes to a separate per-request board "to prevent cross-influence of sub-agents." The authors report a 13–57% relative improvement in end-to-end success over the best baseline. Volunteering removes the need for a controller that knows each agent's abilities, but costs about 1.8× a master–slave design per question. I read the cost figure in a model summary of the page, not in the verbatim text.

### 1.2. Classic blackboard systems

Three components: "blackboard—a structured global memory", "knowledge sources—specialized modules", and a "control component—selects, configures and executes modules" (Wikipedia, Blackboard design pattern). BB1 used meta-level control to detect a stalled search and "switch from one strategy to another." ACCORD defined "obviation conditions to discard a KS action that is no longer relevant" (Wikipedia, Blackboard system). Wikipedia is a secondary source. The primary sources (Corkill 1991; the AI Magazine report) could not be opened.

### 1.3. Anthropic's multi-agent research system

(Anthropic, 2025.) A lead agent plans and dispatches parallel sub-agents, and a citation agent attributes claims at the end.
- **Plan storage.** The lead saves its plan to memory, "since if the context window exceeds 200,000 tokens it will be truncated."
- **Effort scaling.** "simple fact-finding requires just 1 agent with 3-10 tool calls, direct comparisons might need 2-4 subagents with 10-15 calls each." Complex research can need more than 10. Early versions spawned 50 sub-agents for simple queries.
- **Briefs.** Each sub-agent needs "an objective, an output format, guidance on the tools and sources to use, and clear task boundaries." Short briefs led to duplicate work and gaps.
- **Source choice.** Early agents "consistently chose SEO-optimized content farms over authoritative but less highly-ranked sources."
- **Cost and benefit.** An Opus 4 lead with Sonnet 4 sub-agents beat a single Opus 4 agent by 90.2% on an internal eval. Multi-agent runs used about 15× the tokens of a chat.
- **Poor fit.** Multi-agent designs do not suit tasks with many dependencies between agents.

### 1.4. Multi-agent failures (MAST)

Cemri et al. (2025) built a taxonomy of 14 failure modes from 1,642 annotated traces. The verbatim text gives the frequencies for the most common modes:
- Step repetition: 15.7%
- Unaware of termination conditions: 12.4%
- Disobeying the task specification: 11.8%

The summarized sections report three more:
- Incorrect verification: 9.1%
- Incomplete verification: 8.2%
- Failing to ask for clarification: 6.8%

According to the summary, verifiers often run superficial checks. Changing roles or topology improved ChatDev success by up to 15.6 points, but the results varied by model and task.

### 1.5. Cross-harness skill format

The Agent Skills specification lists six frontmatter fields: `name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools`. `argument-hint` is not one of them. The specification does not say how clients treat unknown fields. It recommends a SKILL.md under 500 lines, with reference files kept one level deep. Its best-practices page says to name the trigger for each reference file and to keep gotchas in SKILL.md.

Tool names from the official docs:

| Capability | Gemini CLI | OpenCode | Codex |
| --- | --- | --- | --- |
| Web search | `google_web_search` | `websearch` | `web_search` |
| Page fetch | `web_fetch` | `webfetch` | not found |
| Ask the user | `ask_user` | `question` | not found |
| Task list | `write_todos` | none | not found |
| Sub-agent | one tool per defined sub-agent | `subagent` | not named in docs |
| Sub-agent model | set in the agent definition | set in the agent definition | set per spawn or per definition (summary only) |

### 1.6. Swarms, worker pools, and coordination topology

**Scaling agent systems** (Kim et al., 2025; Google Research and MIT, 180 configurations). Verbatim: "independent agents amplify errors 17.2× through unchecked propagation, while centralized coordination contains this to 4.4×." Decentralized coordination "excels on dynamic web navigation (+9.2% vs. +0.2%)". Coordination shows diminishing or negative returns "once single-agent baselines exceed an empirical threshold of ∼45%", and "tool-heavy tasks suffer disproportionately from multi-agent overhead." On mixed models, verbatim: "Anthropic models uniquely benefit from heterogeneous mixing in centralized architecture, where low-capability orchestrator with high-capability subagents (0.42) outperforms homogeneous high-capability" (0.32). OpenAI and Gemini models degraded under the same mix. Most experiments used 3 agents.

**SearchSwarm** (2026). One fresh sub-agent per delegation call, with a brief stating what is established, uncertain, and ruled out. No shared memory. Without such briefs, sub-agents "re-investigate facts the main agent has already confirmed." If reports are "trusted without scrutiny, errors propagate and accumulate." Correct answers peaked at 3–5 sub-agent calls on BrowseComp.

**Kimi Agent Swarm** (Moonshot AI). Up to 100 sub-agents (300 in a later version, per the help centre), with an orchestrator trained by reinforcement learning. The 4.5× speed-up is a vendor claim about speed, not research quality.

**Stigmergy / pressure fields** (arXiv 2601.08129, 2026). Agents coordinate only through a shared artifact, guided by measurable quality signals. It beat conversation-based and hierarchical control on meeting scheduling. The author scopes it to "artifact refinement tasks where quality decomposes into measurable regional signals", which open-ended research is not.

**Claude Code agent teams** (official docs). Long-lived teammates share a task list. After finishing a task, a teammate "picks up the next unassigned, unblocked task on its own." Claiming "uses file locking to prevent race conditions." Teammates can message each other and run different models.

**Conclusion.** A swarm of many independent agents with no checking is the worst-performing topology in the only controlled study. Long-lived workers that take questions from a shared board, with a coordinator acting as the checkpoint, combine self-claiming (agent teams, 1.1 volunteering) with centralized validation (Kim et al.). This is a design inference: no study tests it on open-web research.

### 1.7. What search and fetch tools return

Claude Code docs: WebFetch "runs the prompt against the content in a separate model call, and Claude receives the result of that call rather than the raw page." The docs call this "lossy by design" and point to `curl` for the unprocessed page. It reads up to 100,000 characters per call and caches pages for 15 minutes. WebSearch "returns result titles and URLs" and does not fetch pages. In this session, though, WebSearch results arrived with a model-written narrative summary, so the docs and the observed output differ. The Claude API `web_fetch` tool returns the full text. The API `web_search` tool limits cited text to 150 characters. Codex's search config has "cached" and "indexed" modes (summary only, unverified). In this session, three sub-agent fetches returned verbatim text only for the first ~40,000 characters and a model summary for the rest.

### 1.8. Pages that refuse automated access

Testing `scripts/fetch_text.py` on this session's failed pages showed three distinct failures: an HTTP 403 (ScienceDirect), a login page served with HTTP 200 (AAAI's journal site), and a page built by JavaScript with about 800 characters of menu text (agentskills.io client list). Before the fix, the script returned the last two as page text, so a quote check would have reported "not found".

Estimates of how many sites block AI crawlers vary with the sample: roughly 10–25% of major sites in robots.txt studies, plus server-level blocking. These come from secondary sources and vendor analyses, not verified here.

Two lookups need no account and worked in testing: the Internet Archive's availability API (`archive.org/wayback/available?url=`) found a 2012 copy of Corkill's unreachable paper, and OpenAlex's `open_access.oa_url` returned the arXiv PDF for a DOI. Unpaywall requires an email address with each request, so the skill does not use it.

### 1.9. Dashboard design (Tufte; n14n.dev)

Tufte, sparkline page (edwardtufte.com): "Sparklines are datawords: data-intense, design-simple, word-sized graphics." "Background colors, frames and boxes don't add much. Avoid all data frames." On colour flags: "the color coding should be modest, just strong enough to send the editorial or interpretative signal", and "We don't want to turn sparklines into vulgar stoplight charts." On monitoring displays, sparklines are "adjacent in space rather than stacked in time." Small multiples (Envisioning Information, as quoted on Wikipedia): "At the heart of quantitative reasoning is a single question: Compared to what?" Tufte's definitions of "layering and separation" and "smallest effective difference" are in his books, which were not read.

The n14n.dev palette fails the dataviz colour-blindness check for status colours (moss vs terracotta, protan ΔE 4.1), so every status also has a glyph and a label.

### 1.10. Second run: tutoring research board

29 questions: 14 from the coordinator, 15 from workers. 12 of the workers' questions came from a source, not from the agent's expectations. About half opened new lines of inquiry (replication beyond high school, mitigations, learners missing tutor errors that match their misconceptions); two were raised to high priority. The other half asked to check details of a source already found ("Does the full text of X report Y"); most stayed low priority or were closed. 11 workers ran, each taking one to three questions, because the brief capped each worker at a small number of questions. The coordinator re-read pages to verify 72 of 88 claims. 56 of 62 sources were read through the fetch tool's extraction.

## 2. Changes made to research-better

| Change | Source |
| --- | --- |
| Capabilities named without tool names, because tool names change across harnesses and versions | 1.5 |
| No default budget numbers: Anthropic's figures are for its own system and untested here | 1.3 |
| Each result triggers four checks on the entries it touched: errors, conflicts, duplicates (delete, don't mark), and obsolete questions | 1.1 LbMAS roles and ablation; 1.2 obviation conditions |
| Event-driven loop and a sub-agent worker pool instead of rounds; batches only when the harness cannot run sub-agents in the background | 1.2 knowledge sources act when the board changes; 1.3 synchronous sub-agents were a bottleneck |
| When results stop adding anything new, change strategy once before stopping | 1.2 BB1 meta-level control; 1.4 termination failures |
| No STANDARD/DEEP modes: delegation is decided per question | 1.3 delegation fits independent questions, not whole topics |
| Delegation steps live in SKILL.md; copyable templates live in `templates/`, with placeholders only | Design inference: in a research skill, `references/` reads as a bibliography or optional background, and `references/register.md` reads as the register itself. Example entries in a template prime the agent's content. 1.5 keeps gotchas in SKILL.md |
| Workers write to the board as they go, one file per entry, with IDs that include the agent's name, so no two writes collide | User feedback; 1.1; 1.6 agent teams |
| Long-lived workers take the next open question themselves, instead of one sub-agent per question; the coordinator verifies, merges, and stops | 1.6 Kim et al. centralized validation; agent teams self-claiming |
| The coordinator does not research; it verifies, merges, and reprioritizes | User feedback; 1.6 |
| Workers use a cheaper model than the coordinator when the harness allows it | User feedback. Note: Kim et al. found Anthropic models did better with a cheaper orchestrator and stronger workers, so this choice is untested |
| No budget question: the GOAL and stop rules set the size | User feedback |
| Search tool text is a lead; fetch output is an extraction unless documented otherwise | 1.7 |
| `scripts/board.py watch` shows the board live; questions nest under the question or source that raised them | User request |
| No retrieval scripts: the skill treats fetch output as an extraction and records how each source was read | 1.7. `fetch_text.py` and `check_quote.py` were tried and removed: they need a shell and Python, add their own failure modes, and were never shown to improve a run |
| One-page dashboard: question tree with status glyphs, evidence squares per claim, progress to the stop level, current answer, source read-and-trust table, agent lanes on a shared time axis; n14n.dev styling | User request; 1.9 |
| `summary.md` holds the current answer in prose, kept by the coordinator | User request |
| Stop level (`high`, `medium`, `low`) chosen from the GOAL | User feedback; 1.10 |
| Workers keep taking questions until none is left at the stop level or their context grows long; no per-worker cap | 1.10 |
| No new question to check details of a known source | 1.10 |
| Final reports cite in APA 7th edition; sources record author, date, title, publisher, and URL | User request |
| Brief adds a stop condition, preferred source types, and an "unclear" status | 1.3 briefs; 1.4 termination and clarification failures |
| Verification also checks that the claim answers the question | 1.4 superficial verification |
| Prefer primary sources over pages that summarize them | 1.3 content farms |
| Do not create harness config to choose a sub-agent model without permission | 1.5 model set in agent definitions |

## 3. Design inferences not tested

- The four register checks transfer LbMAS roles from multi-agent debate to a single controller. No source tests that transfer.
- The board and worker design has not been run end to end. The research-better evals give the agent only web search and fetch, so they cover the single-agent path only.
- Self-claiming uses write-then-re-read, not a lock. Two workers can still take the same question in rare races; the cost is duplicate work.

## 4. Open questions

- [Q8] What do the primary classic sources (Corkill 1991; Hayes-Roth 1985) say about focus-of-attention control? An archived copy of Corkill (1991) now exists at http://web.archive.org/web/20120416034609/http://www.bbtech.com/papers/ai-expert.pdf but has not been read. Hayes-Roth (1985) is closed access.
- [Q10] Does a cheaper coordinator with stronger workers beat the reverse for open-web research? Kim et al. found it for Anthropic models on their benchmarks only.
- [Q11] What do Gemini CLI's `web_fetch` and Codex's search return to the model: page text or a summary?
- [Q9] Do clients that follow the Agent Skills specification ignore or reject `argument-hint`?

## 5. Sources

- Anthropic. (2025, June 13). *How we built our multi-agent research system*. https://www.anthropic.com/engineering/multi-agent-research-system
- Agent Skills. *Specification*. https://agentskills.io/specification
- Cemri, M., et al. (2025). *Why do multi-agent LLM systems fail?* NeurIPS 2025. https://arxiv.org/html/2503.13657v3
- Gemini CLI. *Tools reference* and *Subagents*. https://geminicli.com/docs/reference/tools/ · https://geminicli.com/docs/core/subagents
- Claude Code docs. *Tools reference* and *Agent teams*. https://code.claude.com/docs/en/tools-reference · https://code.claude.com/docs/en/agent-teams
- *Emergent coordination in multi-agent systems via pressure fields and temporal decay* (2026). https://arxiv.org/html/2601.08129
- Han, B., & Zhang, S. (2025). *Exploring advanced LLM multi-agent systems based on blackboard architecture*. https://arxiv.org/html/2507.01701v1
- *LLM-based multi-agent blackboard system for information discovery in data science* (2025). https://arxiv.org/html/2510.01285v2
- Kim, Y., et al. (2025). *Towards a science of scaling agent systems: When and why agent systems work*. https://arxiv.org/html/2512.08296v2
- Moonshot AI. *Kimi Agent Swarm*. https://www.kimi.ai/blog/agent-swarm
- OpenAI Codex docs. *Web search* and *Subagents*. https://learn.chatgpt.com/codex/web-search · https://learn.chatgpt.com/codex/agent-configuration/subagents
- OpenCode. *Tools* and *Agents*. https://opencode.ai/docs/tools/ · https://opencode.ai/docs/agents/
- *SearchSwarm: Towards delegation intelligence in agentic LLMs for long-horizon deep research* (2026). https://arxiv.org/html/2606.09730v1
- Wikipedia. *Blackboard (design pattern)* and *Blackboard system*. https://en.wikipedia.org/wiki/Blackboard_(design_pattern) · https://en.wikipedia.org/wiki/Blackboard_system
