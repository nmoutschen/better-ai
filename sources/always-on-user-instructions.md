# Always-on user instructions: what they do to an LLM, and how to write them

Research findings for the better-ai skills  
Prepared for Nicolas · Search date: 12 November 2026

**No study measured the effect of user-written always-on instructions, such as Claude profile preferences or ChatGPT custom instructions, on output quality or sycophancy. The nearest evidence points one way: user context in the prompt raised agreement sycophancy, model-written memory profiles raised it most, and compliance fell as the number of simultaneous instructions grew.** Memory profiles raised agreement sycophancy by 33% to 45% for three of five models (Jain et al., 2026). In one qualitative case, explicit custom instructions and the memory feature led ChatGPT to infer and align with a user's political views "in similar ways" (Karadal & Kekulluoglu, 2025). Compliance fell as instruction counts rose, mostly through omission (Jaroslawicz et al., 2025; Harada et al., 2025).

Vendors describe these instructions as account-wide context loaded into every conversation, not as enforced configuration. Only coding harnesses give a size limit. Precedence between instruction layers differs between harnesses, and models resolve conflicts between layers unreliably (Z. Zhang et al., 2025; McCauley et al., 2026).

Users who share custom instructions ask for more than style: sourcing, calibrated uncertainty, clarifying questions and resistance to sycophancy (Clark et al., 2025). Users also mispredicted which conditions made them want AI help, and a system built from their stated preferences performed worse than one built from their behaviour (Lai et al., 2026).

**Scope.** This report covers instructions a user writes once and a harness adds to every conversation or session: Claude profile preferences, ChatGPT custom instructions, Gemini saved info, user-level `CLAUDE.md` and `AGENTS.md`, and user rules in Cursor and GitHub Copilot. It covers their effect on output, the effect of instruction count and content, vendor documentation, adherence, what users put in them, and how to draw them out of a user. How to interview a user about their reading and reviewing is in `sources/interviewing-users-about-themselves.md`. Stored personalisation and inferred traits are also in `sources/inclusivity.md`. Agreement bias is in `sources/sycophancy-in-ai-agents.md`.

**Status.** The research stopped at the `medium` level: no high- or medium-priority question is open. 51 claims from 34 sources are on the board. I checked 27 claims against their pages, including every claim this report relies on, except where marked *unchecked*. All checked claims held. The research board is in `.research/always-on-user-instructions/`.

**Reading level of the evidence.** Read in full or as extracted full text: Jain et al. (2026), Jaroslawicz et al. (2025), Harada et al. (2025), Clark, Bai and Mitra (2025), Lai et al. (2026), Clark et al. (2025), and the vendor documentation. Read as abstracts only: Wang et al. (2026), Hu et al. (2026), Karadal and Kekulluoglu (2025), X. Zhang et al. (2026), Z. Zhang et al. (2025), McCauley et al. (2026) and the persona, negation and distraction studies. OpenAI's help pages on custom instructions returned HTTP 403 and are not used. **No study tested a user-written, always-on profile against no profile on any outcome.** Every rule this report suggests is inferred from neighbouring settings: memory profiles, synthetic constraint benchmarks, project-level rule files, and vendor guidance.

## 1. Findings at a glance

| Finding | Evidence | Strength |
|---|---|---|
| **User context raises agreement sycophancy**; model-written memory profiles raised it most | Jain et al. (2026), 38 users, 5 models | One study, full text; effect differs by model |
| **Profiles and retrieved memories worsen irrelevant personalisation, preference narrowing and sycophancy** | Wang et al. (2026), 13 models; Hu et al. (2026) | Two preprints, abstracts |
| **Explicit custom instructions and memory both led ChatGPT to infer and align with a user's politics** | Karadal & Kekulluoglu (2025) | 3 personas, qualitative, abstract |
| **Compliance falls as simultaneous instructions grow**, mainly by omission | Jaroslawicz et al. (2025), up to 500; Harada et al. (2025), up to 10 | Two benchmarks, synthetic constraints |
| **Real custom instructions are often not followed**; parameterised mode switches fail most | Clark, Bai & Mitra (2025), 65 instructions, 1 model | Pilot, full text |
| **Negative constraints: sources disagree** | X. Zhang et al. (2026) vs Anthropic (n.d.-c); Rana (2026) | Contested |
| **Persona descriptions do not improve factual accuracy** | Zheng et al. (2024) | Peer-reviewed, abstract |
| **Users ask for epistemic behaviour, not only style** | Clark et al. (2025), 128 Reddit instructions | One preprint, self-selected sample |
| **Users mispredict what makes them want AI help** | Lai et al. (2026), 50 users | One study, writing assistance |
| **Vendors give no size limit for chat profiles**; coding harnesses give 200 or 500 lines | Anthropic (n.d.-a, n.d.-b); Cursor (n.d.) | Documentation |
| **Precedence between layers differs by harness**, and models resolve conflicts unreliably | Anthropic (n.d.-b); GitHub (n.d.); Cursor (n.d.); Z. Zhang et al. (2025); McCauley et al. (2026) | Documentation plus two benchmarks, abstracts |

## 2. What always-on user context does to output

In a two-week study, 38 users chatted with five models. Responses were then generated with and without parts of their interaction context. "User memory profiles are associated with the largest increases in agreement sycophancy (e.g. +45% for Gemini 2.5 Pro)." For Claude Sonnet 4, GPT 4.1 Mini and Gemini 2.5 Pro, "responses generated with user memory profiles are associated with 33%, 16%, and 45% increases" (Jain et al., 2026). GPT 5.1 and Llama 4 Scout showed no significant change from profiles. "Perspective sycophancy increases only when models can accurately infer user viewpoints from interaction context." The profiles in this study were written by a model from the user's chats, not by the user. The authors write that "these results suggest that system prompt instructions to personalize may influence agreement sycophancy."

Two benchmarks report the same direction across many models. Wang et al. (2026), across 13 LLMs: "the presence of user profiles and retrieved memories consistently exacerbates biases, resulting in an average drop of 45.9% in irrelevant personalization, 41.7% in preference narrowing and 61.7% in sycophantic bias." The paper defines irrelevant personalisation as "models reference personal information in unnecessary contexts." OP-Bench names three types of over-personalisation: "Irrelevance, Repetition, and Sycophancy" (Hu et al., 2026). Both were read as abstracts.

The only source that names user-written instructions found the same mechanism: "We also find the inference happening with explicit custom instructions and the implicit memory feature in similar ways" (Karadal & Kekulluoglu, 2025, abstract). That study used three personas and a qualitative analysis.

**What this means:** user context that lets a model infer the user's views can make it agree more. No source separates the effect of user-written rules about form, such as "use short paragraphs", from the effect of descriptions of the user. That split is a gap. The finding in `sources/interviewing-users-about-themselves.md` §9.2 holds here too: approved examples of output carried most of the benefit of a profile (Wu et al., 2024, as cited there).

## 3. How many instructions a model follows

IFScale gave models up to 500 keyword-inclusion instructions at once: "even the best frontier models only achieve 68% accuracy at the max density of 500 instructions" (Jaroslawicz et al., 2025). The shape of the decline differed by model: "threshold decay" for reasoning models such as o3, "linear decay (gpt-4.1, claude-sonnet-4), and (3) exponential decay (gpt-4o, llama-4-scout)." "Models overwhelmingly err toward omission errors as instruction density increases." Models favoured earlier instructions at moderate densities, so "packing more important instructions towards the beginning of a prompt may help, it becomes a less effective strategy once extreme densities are reached."

ManyIFEval tested up to ten instructions across ten LLMs: "performance consistently degrades as the number of instructions increases" (Harada et al., 2025).

Both benchmarks use synthetic constraints that a program can check. Benchmarks built from realistic prompts point the same way without giving a count-response curve. On agentic instructions with about 12 constraints each, "current models generally perform poorly, especially in handling complex constraint structures" (Qi et al., 2025, abstract). On persistent rules in coding agents, experiments "reveal a systematic gap between task-solving and scaffold-aware compliance" (Ding et al., 2026, abstract). **No source compared short natural-language profile rules with synthetic constraints**, so how many profile rules a model follows is not measured.

Vendors of coding harnesses state a length limit for this reason. Claude Code: "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence," and "The more specific and concise your instructions, the more consistently Claude follows them" (Anthropic, n.d.-b). Cursor: "Keep rules under 500 lines" (Cursor, n.d.). GitHub advises short, self-contained statements (GitHub, n.d.).

## 4. What content helps

### 4.1. Vendor guidance

Anthropic's prompting guide is guidance, not a measured result (Anthropic, n.d.-c):
- Reasons: "Providing context or motivation behind your instructions, such as explaining to Claude why such behavior is important, can … help it deliver more targeted responses."
- Examples: "Examples are one of the most reliable ways to steer Claude's output format, tone, and structure." It recommends 3–5 relevant, diverse examples, kept apart from the instructions.
- Phrasing: "Tell Claude what to do instead of what not to do."
- Emphasis: newer models respond more to the system prompt, so "these models might now overtrigger. The fix is to soften any aggressive language."

### 4.2. Studies

- **Persona descriptions.** "Adding personas in system prompts does not improve model performance across a range of questions" (Zheng et al., 2024, abstract). This concerns factual accuracy, not tone or form.
- **Irrelevant context.** Accuracy on arithmetic reasoning "is dramatically decreased when irrelevant information is included" (Shi et al., 2023, abstract). An always-on instruction is irrelevant to most tasks it is loaded into. That this degrades them is an inference that no study tested.
- **Negative constraints: contested.** In a study of rules for Claude Code, "every individually beneficial rule is a negative constraint ('do not refactor unrelated code'), while every individually harmful one is a positive directive ('follow code style')." Random rules helped as much as curated ones (X. Zhang et al., 2026, abstract). A preprint finds that "the very act of naming a forbidden word primes the model to produce it" (Rana, 2026, abstract), and Anthropic advises positive phrasing (section 4.1). The two studies measure different things, one a forbidden word, the other a scope limit in coding. Neither tested user profiles.

**No source tested scoped or conditional rules, such as "for code reviews, …", in user-level instructions.**

## 5. Do models follow custom instructions?

Offscript audited 65 custom instructions shared on Reddit, on GPT-5 Chat. The auditor "detected potential deviations from instructed behavior in 86.4% of conversations, 22.2% of which were confirmed as material violations through human review" (Clark, Bai & Mitra, 2025). Two failure patterns:
- "Reddit users who implemented complex parameterized instructions designed to switch between task modes or adjust verbosity frequently experienced violations."
- When a later message contradicted a standing instruction, "GPT-5 Chat consistently prioritized the most recent message over established preferences."

This is a pilot on one model. A 13-model evaluation of enterprise personas found that "instruction following varies dramatically across models" (Tripathi et al., 2025).

## 6. What users put in custom instructions

A thematic analysis of 128 custom instructions shared on Reddit found requests about how knowledge is delivered, not only about style (Clark et al., 2025). Users asked for sourcing, calibrated uncertainty, multiple viewpoints, clarifying questions and resistance to sycophancy. One shared instruction reads: "If a question is unclear or ambiguous, ask for more details to confirm your understanding before answering." The authors reviewed OpenAI's and Anthropic's documents, not model outputs, and conclude that the platforms "offer no verification tools to confirm whether preferences were followed." The sample is self-selected.

Indirect evidence:
- A survey of 169 users of social AI found motivations for customisation that include "(3) trust and reliability, (4) pushback" (Skjuve et al., 2026, abstract).
- Project-level Cursor rules in 401 repositories fall into five themes, one of which is "LLM Directives" (Jiang & Nam, 2025, abstract). These are project files, not personal ones.

## 7. Drawing out preferences about AI behaviour

- In a study of 50 users, people ranked urgency first as a reason to want AI writing help, although it was "the weakest behavioral driver." "Systems designed from users' stated preferences achieve only 57.7% accuracy, underperforming even naive baselines," against 61.3% for systems built from behaviour (Lai et al., 2026).
- "Users care about only a sparse subset and rarely articulate them upfront." An adaptive questioning method that infers related preferences from a few answers reached 80.8% alignment on simulated users (Bose et al., 2026).
- "Users often lack the domain knowledge to have completely specified preferences," so the authors argue an agent should help the user build a preference instead of only asking for it (Saracay et al., 2026). This is a position paper.

**No study compared a user's stated preferences about AI behaviour, such as when to ask, how much to verify, or how much autonomy to take, with what they later accept or correct.** The stated-versus-revealed gap in `sources/interviewing-users-about-themselves.md` §2–3 applies by inference.

## 8. Vendor documentation and instruction layers

| Surface | Purpose stated | Size guidance | Precedence stated |
|---|---|---|---|
| Claude profile preferences | "applied to all of your conversations with Claude" (Anthropic, n.d.-a) | None found | None; features work alone or combined |
| Claude Code `~/.claude/CLAUDE.md` | Personal preferences for all projects; "context, not enforced configuration" (Anthropic, n.d.-b) | Under 200 lines per file | "Neither set overrides the other: if a user rule and a project rule conflict, Claude may follow either one" |
| ChatGPT custom instructions | "shape how ChatGPT responds to you"; user, project or chat level; memory is separate (OpenAI, 2025) | Not confirmed: help page blocked | Not confirmed |
| Gemini saved info | "save info about your life, work, or preferences, to get more helpful responses" (Google, n.d.) | None found | None found |
| Cursor User Rules | User-level rules (Cursor, n.d.) | Under 500 lines | Team, then Project, then User; "earlier sources take precedence" |
| GitHub Copilot personal instructions | Personal instructions (GitHub, n.d.) | Short, self-contained statements | On GitHub.com, personal above repository above organisation; most other clients define no order |
| `AGENTS.md` | Project context for coding agents (AGENTS.md, n.d.) | None found | Nearest file wins; "explicit user chat prompts override everything" |

OpenAI's Model Spec ranks instructions root, system, developer, user, guideline. An instruction is "superseded if an instruction in a later message at the same authority level either contradicts it," and "Prior preferences are defaults" (OpenAI, 2026). Benchmarks show that models do not apply a hierarchy reliably. "All evaluated models experience a sharp performance decline when facing conflicting instructions" (Z. Zhang et al., 2025, abstract). "Across 37 evaluated models, hierarchy compliance ranges from 98.2% to 20.5%" (McCauley et al., 2026, abstract). In multi-turn conversation, "all frontier models have less than 50% accuracy on MultiChallenge," which includes keeping earlier instructions (Sirdeshmukh et al., 2025, abstract).

**No source tested an always-on profile against a skill or task instruction loaded later.** Claude Code's advice for this case is "keep the two consistent" (Anthropic, n.d.-b). GitHub's is: "Whenever possible, try to avoid providing conflicting sets of instructions" (GitHub, n.d.).

## 9. Where sources disagree

- **Negative versus positive rules.** X. Zhang et al. (2026) found only negative constraints helped a coding agent. Anthropic (n.d.-c) advises positive phrasing, and Rana (2026) found that naming a forbidden word primes it. The studies measure different kinds of rule.
- **Which layer wins.** Cursor ranks user rules lowest. GitHub.com ranks personal instructions highest. Claude Code defines no order between user and project rules. The OpenAI Model Spec and `AGENTS.md` let the latest explicit user message win.
- **Whether profiles raise sycophancy in every model.** Jain et al. (2026) found no significant effect for GPT 5.1 and Llama 4 Scout. Wang et al. (2026) report the effect as consistent across 13 models, but the abstract gives no per-model results.

## 10. Inferences for a profile-instructions step in `/interview-me`

These are my inferences from the findings above. No study tested them in this setting.

1. **Write rules about the output and the agent's behaviour, not descriptions of the user.** Descriptions let a model infer the user's views, and inferred views raised sycophancy (sections 2, 4.2).
2. **Keep the text short, and put the rules that matter most first.** Compliance falls with count, mainly by omission, and earlier rules held better at moderate counts (section 3). No source gives a safe number for profile rules.
3. **Point to on-demand guides instead of copying them.** The `write-for` and `review-for` skills load only when relevant, so only their pointers need to be always-on. Irrelevant context degraded reasoning (section 4.2), and profiles caused irrelevant personalisation (section 2).
4. **Give each rule its scope, and avoid mode switches.** Parameterised mode-switching instructions failed most often (section 5). No source tested scoped rules.
5. **Ask about epistemic behaviour, such as sourcing, uncertainty, clarifying questions and disagreement.** Users put these in shared instructions (section 6).
6. **Prefer evidence from what the user did over what they say they want.** Stated preferences about AI help mispredicted behaviour (section 7). Corrections the user made to past AI output are the nearest record.
7. **Write the text without harness-specific syntax, and state that the latest explicit request wins.** Precedence differs between harnesses (section 8), and the user wants to reuse the text across them.
8. **Use plain wording, not emphatic wording.** Emphatic wording can cause overtriggering (section 4.1). This rests on vendor guidance only.

## 11. Open gaps

- No study of user-written profile rules about form against no profile, on quality or sycophancy.
- No count-response curve for short natural-language profile rules.
- No study of scoped or conditional rules in user-level instructions.
- No study of stated preferences about AI behaviour against later corrections.
- ChatGPT custom-instruction limits and precedence: OpenAI's help pages were blocked (HTTP 403). Secondary blogs disagree (1,500 vs 5,000 characters) and are not used.

## References

AGENTS.md. (n.d.). *AGENTS.md*. https://agents.md

Anthropic. (n.d.-a). *Understanding Claude's personalization features*. Claude Help Center. https://support.claude.com/en/articles/10185728-understanding-claude-s-personalization-features

Anthropic. (n.d.-b). *How Claude remembers your project*. Claude Code Docs. https://code.claude.com/docs/en/memory

Anthropic. (n.d.-c). *Prompting best practices*. Claude Docs. https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

Bose, A., Li, S. S., Brahman, F., Koh, P. W., Du, S. S., Tsvetkov, Y., Fazel, M., Xiao, L., & Celikyilmaz, A. (2026). *Cold-start personalization via Bayesian adaptive questioning*. arXiv. https://arxiv.org/abs/2602.15012

Clark, N., Bai, R., & Mitra, T. (2025). *Offscript: Automated auditing of instruction adherence in LLMs*. arXiv. https://arxiv.org/abs/2512.10172

Clark, N., Shen, H., Howe, B., & Mitra, T. (2025). *Epistemic alignment: A mediating framework for user-LLM knowledge delivery*. arXiv. https://arxiv.org/abs/2504.01205

Cursor. (n.d.). *Rules*. Cursor Docs. https://cursor.com/docs/context/rules

Ding, D., Liu, S., Yang, E., et al. (2026). *OctoBench: Benchmarking scaffold-aware instruction following in repository-grounded agentic coding*. arXiv. https://arxiv.org/abs/2601.10343

GitHub. (n.d.). *Custom instructions for GitHub Copilot*. GitHub Docs. https://docs.github.com/en/copilot/concepts/prompting/response-customization

Google. (n.d.). *Save info and reference past chats in Gemini Apps*. Gemini Apps Help. https://support.google.com/gemini/answer/16413516

Harada, K., Yamazaki, Y., Taniguchi, M., Marrese-Taylor, E., Kojima, T., Iwasawa, Y., & Matsuo, Y. (2025). *When instructions multiply: Measuring and estimating LLM capabilities of multiple instructions following*. arXiv. https://arxiv.org/abs/2509.21051

Hu, Y., Long, Z., Guo, J., Sui, X., Fu, X., Zhao, W., Zhao, Y., & Qin, B. (2026). *OP-Bench: Benchmarking over-personalization for memory-augmented personalized conversational agents*. arXiv. https://arxiv.org/abs/2601.13722

Jain, S., Park, C., Viana, M., Wilson, A., & Calacci, D. (2026). *Interaction context often increases sycophancy in LLMs*. arXiv. https://arxiv.org/abs/2509.12517

Jaroslawicz, D., Whiting, B., Shah, P., & Maamari, K. (2025). *How many instructions can LLMs follow at once?* arXiv. https://arxiv.org/abs/2507.11538

Jiang, S., & Nam, D. (2025). *Beyond the prompt: An empirical study of Cursor rules*. arXiv. https://arxiv.org/abs/2512.18925

Karadal, P., & Kekulluoglu, D. (2025). *Prioritize economy or climate action? Investigating ChatGPT response differences based on inferred political orientation*. arXiv. https://arxiv.org/abs/2511.04706

Lai, V., Buçinca, Z., Akpinar, N.-J., Houtti, M., Kang, H. B., Chian, K., Suh, N., & Williams, A. C. (2026). *Users mispredict their own preferences for AI writing assistance*. arXiv. https://arxiv.org/abs/2601.04461

McCauley, C., Kan, Z., & Martin, J. (2026). *IH-Benchmark: A conflict-centered benchmark for instruction-hierarchy robustness in LLM applications*. arXiv. https://arxiv.org/abs/2607.25987

OpenAI. (2025). *Customizing ChatGPT*. OpenAI Academy. https://academy.openai.com/public/clubs/work-users-ynjqu/resources/customizing-chatgpt

OpenAI. (2026, October 29). *OpenAI model spec*. https://model-spec.openai.com/2026-10-29.html

Qi, Y., Peng, H., Wang, X., Xin, A., Liu, Y., Xu, B., Hou, L., & Li, J. (2025). *AGENTIF: Benchmarking instruction following of large language models in agentic scenarios*. arXiv. https://arxiv.org/abs/2505.16944

Rana, S. (2026). *Semantic gravity wells: Why negative constraints backfire*. arXiv. https://arxiv.org/abs/2601.08070

Saracay, I., Schmidt, L., & Guestrin, C. (2026). *Beyond expert users: Agents should help users construct preferences, not just elicit them*. arXiv. https://arxiv.org/abs/2606.30863

Shi, F., Chen, X., Misra, K., Scales, N., Dohan, D., Chi, E., Schärli, N., & Zhou, D. (2023). *Large language models can be easily distracted by irrelevant context*. arXiv. https://arxiv.org/abs/2302.00093

Sirdeshmukh, V., Deshpande, K., Mols, J., Jin, L., Cardona, E.-Y., & Lee, D. (2025). *MultiChallenge: A realistic multi-turn conversation evaluation benchmark challenging to frontier LLMs*. arXiv. https://arxiv.org/abs/2501.17399

Skjuve, M., Larsen, A. G., Følstad, A., van As, N., & Brandtzaeg, P. B. (2026). *I wanted it to feel more personal: Customization of social AI as AI individualism in practice*. arXiv. https://arxiv.org/abs/2607.17826

Tripathi, V., Allu, U., & Ahmed, B. (2025). *The instruction gap: LLMs get lost in following instruction*. arXiv. https://arxiv.org/abs/2601.03269

Wang, Y., Wu, Y., Qian, C., Fan, Z., Ha, H., Wu, S., Liu, J., Ji, H., & Wang, G. (2026). *Evaluating the hidden costs of personalization in large language models*. arXiv. https://arxiv.org/abs/2608.28833

Zhang, X., Wang, G., Cui, Y., Qiu, W., Li, Z., Zhu, B., & He, P. (2026). *Guardrails beat guidance: A large-scale study of rules, skills, and persistent configuration for coding agents*. arXiv. https://arxiv.org/abs/2604.11088

Zhang, Z., Li, S., Zhang, Z., Liu, X., Jiang, H., Tang, X., Gao, Y., Li, Z., Wang, H., Tan, Z., Li, Y., Yin, Q., Yin, B., & Jiang, M. (2025). *IHEval: Evaluating language models on following the instruction hierarchy*. arXiv. https://arxiv.org/abs/2502.08745

Zheng, M., Pei, J., Logeswaran, L., Lee, M., & Jurgens, D. (2024). When "a helpful assistant" is not really helpful: Personas in system prompts do not improve performances of large language models. In *Findings of the Association for Computational Linguistics: EMNLP 2024*. https://aclanthology.org/2024.findings-emnlp.888/
