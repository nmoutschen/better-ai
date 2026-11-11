# Building the right thing with AI coding agents

Research findings · Search date: 11 November 2026

AI coding agents often build something other than what the user meant, even when the stated tests pass. The main cause is not missing skill. The agent fills a gap in the request with a plausible assumption and does not say so. Checks that catch this work with concrete artifacts. Generated tests or examples that the user confirms, acceptance tests derived from the requirements, and clarifying questions about real ambiguity each improved results in controlled studies. Writing a specification first shows mixed results, and no study measures whether it gives the user what they wanted. LLM judges of whether code meets its requirements are unreliable.

On spec and design, canonical software-engineering sources distinguish three layers. **Requirements** describe the effect the user needs in their world. A **specification** describes the behaviour at the boundary of the software, precise enough to build from. A **design** describes the internal structure that produces that behaviour. The same sources agree the lines blur. Requirements often contain design constraints, users discover requirements by seeing designs or prototypes, and work on one layer changes the others. They recommend keeping the layers as separate artifacts but developing them together, not as one-way gates.

**Scope.** How an AI coding agent makes sure what it builds is what the user needs, not only that it passes checks: specifications before coding, checking the agent's understanding, showing artifacts early, design decisions, and checking the finished result against the user's goal. Also how canonical sources distinguish a specification from a design. Training methods are out of scope. Clarifying questions in general are covered in `agent-alignment-with-user-intent.md`. These findings are input for a `code-better` skill. This report does not design it.

**Status.** All 9 high- and medium-priority questions are answered. One low-priority question on terminology is still open. 45 sources, 85 claims. I checked every claim's quote against its source page; all 85 are on the page. The body text of ISO/IEC/IEEE 29148 is paywalled: only its table of contents and scope were read. Most AI studies are 2025–2026 preprints, and ten were read as abstracts only.

## Findings at a glance

| Finding | Evidence | Evidence boundary |
|---|---|---|
| Requirements, specification and design are distinct layers whose lines blur | Standards, foundational papers, SWEBOK, textbook | Standard's body text not read |
| Agents pass stated tests but miss implicit intent | Pilot benchmark; SWE-bench re-analysis; 20,574 real sessions | Pilot is small; no real-world rate per task |
| The cause is a silent plausible assumption | Real sessions; two benchmark studies | — |
| A spec written first: mixed | One null field study, one positive benchmark, two mixed | No user-intent outcome |
| Tests or examples confirmed by the user improve correctness | Two controlled user studies | Function-level, small samples |
| Acceptance tests from requirements improve agent results | One controlled study, one industrial report | Web apps |
| Agents follow a flawed proposed solution | Two benchmarks | Mutated benchmarks |
| Design flaws hide behind passing tests | Three studies | Abstracts; preprints |
| Plan review alone does not ensure a usable result | One user study, one industrial deployment | Thin |
| LLM judges of requirement conformance are unreliable | Four studies | — |

## 1. Specification versus design

### 1.1. The layers

- **Requirements and specification.** Zave and Jackson (1997) define a requirement as an optative property "whose satisfaction will fully satisfy the customer", and a specification as an optative property that is implementable. Domain knowledge bridges the two: the specification plus facts about the world must guarantee the requirements. They reject the old epigram as a foundation: "There was a time when the epigram 'requirements say what the system will do and not how it will do it' summarized all of requirements engineering. That time is long past." Requirements engineering should describe the environment, not the machine to be built.
- **The reference model.** Gunter et al. (2000) separate "requirements that indicate what the customer needs from the system, described in terms of its effect on the environment" from "specifications that provide enough information for a programmer to build a system that satisfies the requirements". The specification "occupies the middle ground between the system and its environment". They note that the European Space Agency standard mandates both a user-requirements and a software-requirements document, while some industrial groups find the second not worth maintaining.
- **The standard.** ISO/IEC/IEEE 29148:2018 has three specification documents at different levels: stakeholder (StRS), system (SyRS) and software (SRS). Its SRS contents include a section "Design constraints" (ISO/IEC/IEEE, 2018; table of contents only).
- **Design.** SWEBOK defines design as "the process of defining the architecture, components, interfaces, and other characteristics of a system or component" and the result of that process (Bourque & Fairley, 2014).

### 1.2. Where the lines blur

- The difference between a requirement and a specification "depends on precise location of the interface between the machine and environment" (Zave & Jackson, 1997). Moving that boundary moves the line.
- "Architectural design is the point at which the requirements process overlaps with software or systems design and illustrates how impossible it is to cleanly decouple the two tasks." SWEBOK places "invention design", conceptualising software to satisfy needs, inside the requirements process (Bourque & Fairley, 2014).
- "The boundary between requirements and design is not a sharp line but a gray, fuzzy area". Requirements should stay free of implementation bias except for intended design constraints. Analysing a proposed architecture or a prototype helps find wrong or missing requirements. "If you leap directly from requirements into code, you're essentially designing the software mentally and on the fly" (Wiegers & Beatty, 2016).
- The Twin Peaks model keeps problem structuring (requirements) and solution structuring (architecture) as distinct content but develops them concurrently. "Requirements often emerge only after significant analysis of models or prototypes of a system has taken place, and users have been given an opportunity to view and provide feedback" (Nuseibeh, 2001).
- "In most cases the people who commission the building of a software system do not know exactly what they want and are unable to tell us what they do know." Implementation details "invalidate our design and we must backtrack." Parnas and Clements (1986) still recommend writing the requirements document as if the process had been rational: "we can fake it."

**What this means for the question.** The sources support a distinction. A spec states what the software must do at its boundary and why, in terms the user can check against their world. A design states how the software's internals produce that behaviour, in terms only a developer checks. They do not support treating these as strict sequential steps. A user's request can contain a design constraint, and showing a design or prototype is one of the main ways to find out the requirements.

## 2. How often agents build the wrong thing

- In a 49-problem pilot, two models "pass over 92% of stated tests yet violate intent in over half of problems (54.5% and 63.5%)" (Haing et al., 2026). The sample is small, and the authors call the results suggestive.
- On SWE-bench Verified, 29.6% of plausible patches behave differently from the developer's patch. 28.6% of these were certainly incorrect, inflating resolution rates by 6.2 points (Wang et al., 2026).
- In 20,574 real coding-agent sessions, misread intent was 26.95% of misalignment episodes. It "reflects not wholesale misunderstanding, but a plausible concretization of an underspecified request." In 44.10% of these, the developer left a consequential gap in the prompt. 91.49% of visible resolutions needed explicit correction by the user (Tang et al., 2026).
- "When a prompt leaves input formats, error handling, or design decisions unstated, the model fills the gaps with implicit assumptions" (Wu, 2026). Extracting those assumptions is itself hard: the best method reached F1 0.66.
- In LLM-labelled failures of agent runs on a benchmark, requirement misinterpretation was 30–34% of failures. That category also includes failing to locate the problem (Xu et al., 2025).
- LLMs infer unspecified requirements correctly 41.1% of the time by default. Underspecified prompts are twice as likely to regress when the model or prompt changes. "Simply specifying all requirements does not consistently help, as models have limited instruction-following ability and requirements can conflict" (Yang et al., 2026).

## 3. Writing a specification first

- **Null result.** In 88,052 open-source pull requests, after matching on risk, PRs with and without specification artifacts were "indistinguishable in defect introduction". Specification quality predicted neither defects nor rework, and "specifications do not constrain the scope of AI-tagged changes" (Hill, 2026). The artifacts were mostly references to issues and tickets, not output of spec-driven development tools.
- **Positive, at a cost.** A separate phase in which an agent writes a behavioural specification before coding raised test pass rates by 6.9%–21.3% across four models, all significant. Total cost rose 48%–130% (Chen et al., 2026).
- **Mixed.** Structured specifications (Gherkin, domain models) improved output over natural language alone in a pilot, but Gherkin specs alone did worse than natural-language specs (Feng et al., 2026). Removing detail from prompts hurt on one benchmark and had near-zero effect on another, because descriptions, constraints and examples repeat each other (Akli et al., 2026).
- **Late requirements cause rework.** In real agent sessions, a requirement that arrived after implementation began was followed by about twice as much deletion of earlier agent code. Advance warning without the requirement's content had no effect (Jiang et al., 2026). This is an association, not a tested cause.

No study compares specification-first with prompting alone on whether the user got what they wanted.

## 4. Checking the agent understood

| Technique | What it does | Effect | Source |
|---|---|---|---|
| Tests confirmed by the user | Shows generated tests; the user marks each pass or fail | Users more likely to evaluate code correctly, lower cognitive load (15 programmers); large pass@1 gains only with a simulated user | Fakhoury et al. (2024) |
| Clarifying questions after detecting ambiguity | Detects ambiguity by checking whether candidate solutions agree, then asks | GPT-4 Pass@1 70.96% → 80.80% on MBPP-sanitized | Mu et al. (2023) |
| Requirement alignment | The model answers a question list about the requirement, then checks the code by recovering masked parts of the requirement | +7.93 to +30.25 points across five benchmarks | Li et al. (2026) |
| Users classify concrete examples | Shows distinguishing examples instead of the generated artifact | Users judged correctness better for regexes and access policies; novices matched domain-trained users on LTL | Prasad et al. (2026) |

All are function-level or small-language tasks. Strong coding models are not good at spotting ambiguity: "Strong code generation performance does not inherently translate to effective requirement clarification", and extra reasoning helps correctness more than ambiguity detection (Fang et al., 2026).

## 5. Concrete artifacts help people validate requirements

Acceptance-test tables of inputs and expected outputs "significantly improve requirement understanding, but tend to involve additional effort" (Ricca et al., 2007). Paper prototyping elicited the most requirements of three interview methods in a family of student experiments (Rueda et al., n.d.). With AI-generated artifacts, having users classify examples beat showing them the artifact (Prasad et al., 2026). No study compares examples with prose specifications or plans for validating a coding agent's work.

## 6. Requests that state a solution

When a query embeds a flawed proposed solution, "even the strongest LLMs predominantly answer the literal request (0.75–0.92) and far less often the intended one (0.33–0.71)". Giving the model the user's explicit intent helps, but a large gap remains (Yerukola et al., 2026). Coding agents' performance dropped by up to 46.7% when a task included a plausible but misleading solution. A system instruction warning about such problems "only offers partial mitigation" (Wu et al., 2026). These are mutated benchmarks, not real users.

## 7. Design decisions made by agents

- When agents choose the internal structure of evolving code, "structural erosion rising in 77% of trajectories" while they pass checkpoints. Prompts asking for quality did not change the rate of decline (Orlanski et al., 2026).
- "Neither functional correctness nor detailed prompting mitigates" architectural decay in AI-generated systems (Zhu et al., 2026).
- Given an explicit architecture constraint, a small open model violated it in 80% of a pilot's cases; a frontier model did not (Slater, 2025; low trust).
- Developers describe co-planning as a form of oversight, report difficulty reviewing agent code, and use test results as a proxy for correctness (Dhanorkar et al., 2026), which cannot reveal design flaws.

**Plan review.** In a spreadsheet study (N = 24), a plan mode gave similar outcomes with less refinement and a better perceived collaboration (Kumar et al., 2026). In an industrial deployment, practitioners approved 82% of agent-generated plans, but only 25% of coding tasks reached a pull request (Takerngsaksiri et al., 2024). No study shows that reviewing a plan improves design quality or whether users notice flawed design decisions.

## 8. Checking the finished result against the goal

- **LLM judges are unreliable.** LLMs "frequently misclassify correct code implementation as non-compliant or defective", and prompts asking for explanations and fixes make it worse (Jin & Chen, 2025, 2026). The best judges align with developer preference "only 6-18% above random chance" (Mittal et al., 2026). Even the best judge in another study "frequently misjudges the correctness of the code" (Crupi et al., 2025). The choice of evaluator model changed agreement with humans from 31.8% to 93.6% (Tran et al., 2026).
- **Executable acceptance tests help.** Acceptance tests derived from the requirements and run in a browser improved agent accuracy on 20 web apps by 15.5–23.7 points with capable models. Unreliable test feedback removed the gain (Wan et al., 2026). Self-testing in the browser during generation predicted benchmark score (r = 0.72) (Tran et al., 2026).
- **Narrow checks beat broad generic ones.** In a production prompt-to-app system, "lightweight smoke checks and backend contract tests deliver most reliability lift, whereas broad end-to-end suites often reject working apps" (Kniazev et al., 2026).

All these checks compare against written requirements, not the user's own goal.

## 9. LLMs on requirements tasks

LLM follow-up interview questions were "no worse than the human-authored questions", and better when guided by common interviewer mistakes (Shen et al., 2025). Experts largely agreed with an LLM's overall ratings of user-story quality (Trendowicz et al., 2026). But the best of ten models detected a median of only 47% of expert-identified requirement issues, and "necessity and correctness issues are almost always missed". The authors warn that chaining such modules in agents "risks compounding these deficiencies" (Shefa et al., 2026). Most of this literature tests GPT models in controlled settings (Zadenoori et al., 2025).

## 10. What the research could not find

- Any study measuring whether an agent's finished work meets the user's own goal, as judged by the user.
- A real-world rate of intent misses per task.
- A controlled comparison of specification-first and prompt-only work on user intent.
- Any test of restating the task to the user, or of design-decision questions, in repository-level agents.
- Whether users notice flawed design decisions, and whether plan review improves design.
- A comparison of examples with prose plans for validating an agent's work.
- Requirements-engineering sources on separating a stated solution from the need, such as Wiegers on solution ideas in requirements, could not be read in full and were not used.

Open question (low priority): terminology (validation and verification, spec-driven development, twin peaks).

The research board is in `.research/code-better-right-thing/`.

## References

Akli, A., Papadakis, M., Cordy, M., & Le Traon, Y. (2026). *When prompt under-specification improves code correctness: An exploratory study of prompt wording and structure effects on LLM-based code generation*. arXiv. https://arxiv.org/abs/2604.24712

Bourque, P., & Fairley, R. E. (Eds.). (2014). *Guide to the software engineering body of knowledge (SWEBOK), version 3.0*. IEEE Computer Society. https://ieeecs-media.computer.org/media/education/swebok/swebok-v3.pdf

Chen, Y., Chang, S., Chawa, K., Lin, F., Chen, B., Wang, S., & Hassan, A. E. (2026). *SpecFirst: Behavioral specification elicitation as a first-class step in agent-based program synthesis from scratch*. arXiv. https://arxiv.org/abs/2607.27167

Crupi, G., Tufano, R., et al. (2025). *On the effectiveness of LLM-as-a-judge for code generation and summarization*. arXiv. https://arxiv.org/abs/2507.16587

Dhanorkar, S., Passi, S., & Vorvoreanu, M. (2026). *Human oversight of agentic systems in practice: Examining the oversight work, challenges, and heuristics of developers using software agents*. arXiv. https://arxiv.org/abs/2606.05391

Fakhoury, S., Naik, A., Sakkas, G., Chakraborty, S., & Lahiri, S. K. (2024). LLM-based test-driven interactive code generation: User study and empirical evaluation. *IEEE Transactions on Software Engineering*. https://arxiv.org/abs/2404.10100

Fang, Z., Jin, D., Dong, Y., Li, Y., Zhang, K., Jin, Z., & Li, G. (2026). *ClarifyCodeBench: Evaluating LLMs on clarifying ambiguous requirements for code generation*. arXiv. https://arxiv.org/abs/2607.00711

Feng, S., Chen, B., Meyer, B. H., & Mussbacher, G. (2026). LLM-assisted repository-level generation with structured spec-driven engineering. In *FSE Companion '26*. ACM. https://arxiv.org/abs/2605.02455

Gunter, C. A., Gunter, E. L., Jackson, M., & Zave, P. (2000). A reference model for requirements and specifications. *IEEE Software, 17*(3), 37–43. https://typeset.io/pdf/a-reference-model-for-requirements-and-specifications-3mcvvzbem6.pdf

Haing, S., Vidra, N., & Setty, S. (2026). *DevIntent: How much does LLM-generated code violate developer intent?* arXiv. https://arxiv.org/abs/2608.07614

Hill, B. (2026). Specification artifacts in open-source pull request workflows do not reduce defects: An empirical test of spec-driven development claims. In *ESEM 2026* (LIPIcs Vol. 394, Article 84). Schloss Dagstuhl. https://drops.dagstuhl.de/storage/00lipics/lipics-vol394-esem2026/LIPIcs.ESEM.2026.84/LIPIcs.ESEM.2026.84.pdf

ISO/IEC/IEEE. (2018). *ISO/IEC/IEEE 29148:2018 Systems and software engineering — Life cycle processes — Requirements engineering* [Preview]. https://www.vde-verlag.de/iec-normen/preview-pdf/info_isoiecieee29148{ed2.0}en.pdf

Jiang, B., Cheng, H., Fu, Y., Koziolek, A., Li, J., & Zhang, W. (2026). *Requirements after the first edit: Mining late requirement emergence and rework in real-world coding-agent sessions*. arXiv. https://arxiv.org/abs/2609.03028

Jin, H., & Chen, H. (2025). Uncovering systematic failures of LLMs in verifying code against natural language specifications. In *ASE 2025*. https://arxiv.org/abs/2508.12358

Jin, H., & Chen, H. (2026). *Are LLMs reliable code reviewers? Systematic overcorrection in requirement conformance judgement*. arXiv. https://arxiv.org/abs/2603.00539

Kniazev, E., Kravchenko, A., Rekun, I., Broadhead, J., Shamgunov, N., Sah, P., Nichite, P., Yamshchikov, I., et al. (2026). app.build: A production framework for scaling agentic prompt-to-app generation with environment scaffolding. In *SANER 2026 Industrial Track*. https://arxiv.org/abs/2509.03310

Kumar, A., Dutta, A., Gulwani, S., Soares, G., Sarkar, A., & Murphy-Hill, E. (2026). *Plans work in mysterious ways: Evaluating a plan mode for spreadsheet agents*. arXiv. https://arxiv.org/abs/2607.23670

Li, J., Bai, R., Luo, Y., Zhang, Y., Yang, W., Sun, Z., Zhao, T., Jin, D., Li, L., & Jin, Z. (2026). *Bridging the gap between user intent and LLM: A requirement alignment approach for code generation*. arXiv. https://arxiv.org/abs/2604.16198

Mittal, A., Shar, R., Wu, Z., Agarwal, S., Wu, T., Donahue, C., Talwalkar, A., Chi, W., & Chen, V. (2026). *Comparing developer and LLM biases in code evaluation*. arXiv. https://arxiv.org/abs/2603.24586

Mu, F., Shi, L., Wang, S., Yu, Z., Zhang, B., Wang, C., Liu, S., & Wang, Q. (2023). *ClarifyGPT: Empowering LLM-based code generation with intention clarification*. arXiv. https://arxiv.org/abs/2310.10996

Nuseibeh, B. (2001). Weaving the software development process between requirements and architectures. In *Proceedings of STRAW 2001*. https://www.cin.ufpe.br/~straw01/epapers/paper05/paper05.html

Orlanski, G., Roy, D., Yun, A., Shin, C., Gu, A., Ge, A., et al. (2026). *SlopCodeBench: Benchmarking how coding agents degrade over long-horizon iterative tasks*. arXiv. https://arxiv.org/abs/2603.24755

Parnas, D. L., & Clements, P. C. (1986). A rational design process: How and why to fake it. *IEEE Transactions on Software Engineering, SE-12*(2). https://rd.springer.com/content/pdf/10.1007/3-540-15199-0_6.pdf

Prasad, S., Austen, S., Fisler, K., & Krishnamurthi, S. (2026). Meaningful human-in-the-loop checking of GenAI synthesis for restricted languages. In *ECOOP 2026* (LIPIcs Vol. 372). https://drops.dagstuhl.de/storage/00lipics/lipics-vol372-ecoop2026/LIPIcs.ECOOP.2026.22/LIPIcs.ECOOP.2026.22.pdf

Ricca, F., Torchiano, M., Ceccato, M., & Tonella, P. (2007). Talking tests: An empirical assessment of the role of Fit acceptance tests in clarifying requirements. In *IWPSE 2007*. https://profs.scienze.univr.it/ceccato/papers/2007/iwpse2007.pdf

Rueda, S., Panach, J. I., & Distante, D. (n.d.). Requirements elicitation methods based on interviews in comparison: A family of experiments. *Information and Software Technology*. https://www.uv.es/777DB0+NCctPQs=/Files/Journals/IST_2020Requirements_elicitation.pdf

Shefa, J., Salado, A., Wach, P., & Topcu, T. G. (2026). *Two truths and a lie? Benchmarking off-the-shelf LLMs for requirements quality assessment*. arXiv. https://arxiv.org/abs/2609.03230

Shen, Y., Singhal, A., & Breaux, T. (2025). *Requirements elicitation follow-up question generation*. arXiv. https://arxiv.org/abs/2507.02858

Slater, T. (2025). *Quantitative analysis of technical debt and pattern violation in large language model architectures*. arXiv. https://arxiv.org/abs/2512.04273

Takerngsaksiri, W., Pasuksmit, J., Thongtanunam, P., Tantithamthavorn, C., & Zhang, R. (2024). *Human-in-the-loop software development agents*. arXiv. https://arxiv.org/abs/2411.12924

Tang, N., Chen, C., Xu, G., Shi, Y., Huang, Y., McMillan, C., Dong, T., & Li, T. J.-J. (2026). *How coding agents fail their users: A large-scale analysis of developer-agent misalignment in 20,574 real-world sessions*. arXiv. https://arxiv.org/abs/2605.29442

Tran, H., Nashold, L., Krishnan, R., Bigeard, A., Gu, A., et al. (2026). *Vibe Code Bench: Evaluating AI models on end-to-end web application development*. arXiv. https://arxiv.org/abs/2603.04601

Trendowicz, A., Seifert, D., Jedlitschka, A., Ciolkowski, M., & Strahilov, A. (2026). *DeepQuali: Initial results of a study on the use of large language models for assessing the quality of user stories*. arXiv. https://arxiv.org/abs/2602.08887

Wan, Y., Liang, T., Xu, J., Xiao, J., Huo, Y., & Lyu, M. R. (2026). From runnable code to shippable applications: Test-driven development for full-stack web application generation. In *ASE 2026*. https://arxiv.org/abs/2605.17242

Wang, Y., Pradel, M., & Liu, Z. (2026). Are "solved issues" in SWE-bench really solved correctly? An empirical study. In *ICSE 2026*. https://arxiv.org/abs/2503.15223

Wiegers, K., & Beatty, J. (2016). *Guest article: Beyond requirements development* [Adapted from *Software requirements* (3rd ed.)]. Microsoft Press blog. https://learn.microsoft.com/en-us/archive/blogs/microsoft_press/guest-article-beyond-requirements-development

Wu, J. J. (2026). *AssumptionMiner: Extracting, tracing, and revising implicit assumptions in LLM code generation*. arXiv. https://arxiv.org/abs/2607.22898

Wu, Z., Li, Y., Tafjord, O., & Kim, B. (2026). *XYEval: Agents say yes to bad advice*. arXiv. https://arxiv.org/abs/2609.23939

Xu, J., Deng, K., Li, W., et al. (2025). *SWE-Compass: Towards unified evaluation of agentic coding abilities for large language models*. arXiv. https://arxiv.org/abs/2511.05459

Yang, C., Shi, Y., Ma, Q., Liu, M. X., Kästner, C., & Wu, T. (2026). *What prompts don't say: Understanding and managing underspecification in LLM prompts*. arXiv. https://arxiv.org/abs/2505.13360

Yerukola, A., Hwang, J. D., Zheng, M., Godsey, J., Kim, H., Pyatkin, V., Hu, J., & Sap, M. (2026). *XYBench: Can LLMs respond pragmatically to queries with misconceptions?* arXiv. https://arxiv.org/abs/2609.06842

Zadenoori, M. A., Dabrowski, J., Alhoshan, W., Zhao, L., & Ferrari, A. (2025). *Large language models (LLMs) for requirements engineering (RE): A systematic literature review*. arXiv. https://arxiv.org/abs/2509.11446

Zave, P., & Jackson, M. (1997). Four dark corners of requirements engineering. *ACM Transactions on Software Engineering and Methodology, 6*(1), 1–30. https://pamelazave.com/4dc.pdf

Zhu, Y., Tsantalis, N., & Rigby, P. C. (2026). *AI-generated smells: An analysis of code and architecture in LLM and agent-driven development*. arXiv. https://arxiv.org/abs/2605.02741
