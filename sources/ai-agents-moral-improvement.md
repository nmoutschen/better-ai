# Using AI agents to help people become morally better

Research register · Search date: 7 November 2026

**Scope.** This report covers AI systems that help people improve their own moral reasoning, character, or conduct, such as chatbots, LLM assistants, and autonomous agents. It does not cover making the AI itself ethical, except where that affects how the AI influences people. The goal is to map the designs that researchers propose, the evidence on whether those designs work, and the risks sources raise, so that the findings can inform how such an agent is designed or used.

**Status.** Researchers have proposed several designs. The best supported asks the user questions instead of handing down verdicts. Almost no study shows that talking to an AI makes people more moral. The strongest evidence shows that chatbots can easily shift people's moral judgments, in either direction and often without the person noticing. For anyone designing such an agent, this means changing what people think is the easy part, and no study has yet shown that an agent can make those changes improvements. All high- and medium-priority questions are answered. Three low-priority questions remain open (section 5).

## 1. Designs that researchers propose

Most of this literature is philosophy. Its central term is the **artificial moral advisor (AMA)**: an AI that gives moral guidance to a person. Landes et al. (2024) sort AMAs into three types.

| Type | What the AI does | Main criticism |
|---|---|---|
| Exhaustive (replaces the person) | Makes the moral decision for the user | The user stays passive, which "could potentially lead to a gradual erosion of human moral skills" (Landes et al., 2024) |
| Auxiliary (applies the user's values) | The user enters their own value ranking or picks a value framework, and the AI uses it to formulate recommendations | The user's role "is reduced to either accepting the result of the deliberation of the virtual advisor or not" (Lara, 2021) |
| Socratic (asks questions) | Starts with no predefined values and questions the user, so the user reaches their own decision | Volkman and Gabriels (2023) argue it cannot really be neutral |

**Authority machines and inspiration machines.** Landes et al. (2024) describe two ends of a spectrum. An authority machine hands down answers. An inspiration machine prompts the user to think. They argue that "if AMAs are to genuinely enhance people morally, they should be designed as inspiration and not authority machines." Lara (2021) argues for the same position, describing an assistant that "rather than making moral decisions for us, instructs us, through dialogue, so that we make them ourselves."

**Several mentors instead of one neutral assistant.** Volkman and Gabriels (2023) reject both the all-knowing oracle and the neutral Socratic assistant. They propose several AI interlocutors "with their own distinct points of view reflecting their training in a diversity of concrete wisdom traditions," with the user still making the decision.

**A personalized advisor.** Giubilini et al. (2024) propose a model trained on the user's own writing. It would help users "infer and explicitly express their occasionally changing values and preferences" (as described by Landes et al., 2024). The authors write that "the feasibility of LLMs providing such personalized moral insights remains uncertain," and that the needed abilities "have not yet been applied to or tested in the context of providing personalized self-knowledge" (Giubilini et al., 2024).

**Gap.** A 2025 chapter reportedly splits proposals into substitutive, value-driven, and value-open enhancement. It was seen only as a search snippet and could not be read, so its definitions are unknown.

## 2. Evidence on whether AI makes people more moral

### 2.1. Studies of improvement

Studies that test whether AI makes people more ethical report null, small, or narrow results.

- **AI teammates in classroom discussion** (Jin et al., 2026, preprint). 217 university students discussed a self-driving-car dilemma in groups of three. A supportive AI teammate "increased grounded/qualified claims relative to control," but "shifts in final moral decisions were driven primarily by participants' initial stance rather than condition." A contrarian AI teammate showed no difference from the human-only groups on the reasoning index.
- **Chatbot conversations with toxic Reddit users** (Foote et al., 2026, preprint). 893 users who had recently posted toxic content were invited to talk with a chatbot. Some reflected on their behavior, but "we did not observe a significant change in toxic behavior in the following month compared to a control group."
- **Advice on honesty** (Leib et al., 2023, preprint). "Dishonesty-promoting advice increases dishonesty, whereas honesty-promoting advice does not increase honesty."
- **Advice in bargaining games** (Babin & Chauhan, 2026). Advice from a human or from a generative AI increased generous choices, but "players preferred human advice over that from genAI and were more willing to pay for it."
- **GPT-5 moral advice** (Teo & Lieder, 2026). In a preregistered experiment with 460 participants, GPT-5's advice "had no net effect on the prosociality or extremity of people's decisions," but "consulting GPT-5 made participants significantly more confident about their final decisions." *Unverified: the PDF returned an access error when checked, and the authors' names come from search results.*
- **Small prototypes.** These studies show positive signs, but none used a randomized control group:
  - AI ethics-discussion agents used by 45 STEM students (Seo et al., 2026).
  - PerspectiveCoach, a reflection tool used by 18 software developers, which showed "increased self-awareness, broadened perspectives, and more nuanced ethical articulation" (Olson et al., 2026).
  - An engineering ethics chatbot used by 25 students. It was compared with an earlier cohort, not a randomized control, and students "demonstrated higher engagement levels, cited ethical codes more frequently" (Smith et al., 2025).
  - SocrAI, a proposed Socratic assistant, has no reported test. Its proponent says "it won't tell you what is good or wrong" (Gallagher, 2023).

### 2.2. Evidence that AI shifts moral judgment

The evidence that AI changes moral judgment is stronger than the evidence that it improves it.

- **Inconsistent advice still shifts judgment** (Krügel et al., 2023; peer-reviewed; 1,851 participants recruited, 767 analyzed). "ChatGPT turns out highly inconsistent as a moral advisor," yet its advice changed users' judgments on trolley-type dilemmas. Knowing that a bot gave the advice "does not immunize users against this influence," and "users underestimate the influence of ChatGPT's advice on their moral judgment." The authors conclude that "Transparency, however, is not sufficient to enable the responsible use of AI." A later experiment by the same team found that users followed advice without a justification as readily as advice with one (Kruegel et al., 2025, preprint).
- **Lasting shifts from short conversations** (Teng et al., 2026, preprint, 53 participants). "The brief conversations induced significant directional shifts in moral judgments, accepting stricter standards as well as advocating greater leniency (… Cohen's d = 0.735-1.576), with increasing strengths of this effect during a two-week follow-up." The control condition produced no changes, and participants "remained unaware of the persuasive intent."
- **People rate AI moral advice highly** (Dillion et al., 2025). When raters were not told which advice came from an AI, they "perceived GPT as demonstrating moral reasoning that slightly surpassed that of a renowned ethicist." Persuasive advice is not the same as correct advice, which is why this matters.
- **Sycophantic AI** (Cheng et al., 2025, preprint). Sycophantic AI means AI that tells users what they want to hear. "Sycophantic AI models significantly reduced participants' willingness to take actions to repair interpersonal conflict."

### 2.3. How well LLMs reason as moral assistants

On a benchmark of open LLMs as moral assistants, "most models struggle with abductive reasoning, especially in generation," and "Llama models underperform consistently in dynamic tasks, even at 70B scale" (Galatolo et al., 2025). Abductive reasoning means inferring the most likely explanation from incomplete facts. Sources disagree on consistency. Dillion et al. (2025) report that "the ethical stance of GPT remained consistent across different generations," while Krügel et al. (2023) found ChatGPT highly inconsistent. The two studies used different models and tasks.

## 3. Risks that sources raise

Nearly all of these risks are argued by philosophers rather than measured in studies.

- **Moral deskilling.** People who rely on an AI's answers may lose their own moral skill. "This would amount to moral deskilling" (Landes et al., 2024). Giubilini et al. (2024) raise the same risk for personalized advisors. Hovd (2023) disputes the premise and argues that the likelier source of deskilling is change in institutions, not individuals losing skill. No study measures deskilling or dependence directly.
- **Manipulation.** Lara and Rodríguez-López (2025) name two conditions that make an influence manipulative. First, "it seeks to influence the agent with criteria that are alien to him or her." Second, it is not transparent. They conclude that "well-designed nudges could be useful and effective tools for our moral enhancement in a way that respects our autonomy and is free from manipulation." *Unverified: the paper is behind a login and the quotes could not be checked.*
- **Displaced responsibility.** An AMA cannot be a morally responsible agent, so "using AMAs to offload human responsibility is inadequate" (Constantinescu et al., 2022). *Unverified for the same reason.*
- **Design that is not neutral, and misuse.** Landes et al. (2024) argue that "the way AMAs are designed is not neutral." Giubilini and Savulescu (2018) discuss "how a malevolent agent could use this technology to pursue morally bad goals." The same authors argue that an AMA "would respect and indeed enhance individuals' moral autonomy."
- **Privacy.** For a personalized advisor, "since the type of information required is potentially highly sensitive, privacy issues need to be adequately addressed" (Giubilini et al., 2024).
- **A related experiment on delegation** (Köbis et al., 2025). Honest reporting fell from about 95% without delegation to about 75% when participants delegated to a rule-based machine. LLM agents "were far more likely than human agents to carry out fully unethical instructions," and guardrails reduced this compliance but "usually not eliminated" it. This study is about delegating tasks, not about moral advice.

## 4. Design principles

These principles come from argument, not from tests. Only the first is supported by two independent sources (Lara, 2021; Landes et al., 2024). The others each rest on a single source.

1. Ask questions instead of giving verdicts: "a conversational stance that questions users, instead of telling them what to do" (Landes et al., 2024).
2. Give reasons. "If the AMA does not offer reasons for its recommendations, then it operates as an authority machine" (Landes et al., 2024).
3. Do not build in a fixed set of values. The AMA "would not work on a set of predefined values, either inputted by users or by various moral experts" (Landes et al., 2024). Volkman and Gabriels (2023) disagree and propose several value traditions instead.
4. Build privacy in, and let users keep ownership. "Privacy must be embedded in every aspect of the system's design," and "users must be able to retain ownership over their AI systems" (Koralus, 2025, writing about AI and independent thinking in general).

## 5. What the research could not find, and open questions

**Missing evidence:**
- A long-term study of AI and moral character.
- A randomized trial that uses a validated measure of moral reasoning, such as the Defining Issues Test (DIT-2).
- A deployed product with a published, controlled evaluation of its outcomes.
- An empirical study of moral deskilling or dependence on AI.

**Sources that could not be read** and could change parts of the answer:
- Lara and Deckers (2020), the original Socratic-assistant paper (Neuroethics; repository copies blocked).
- The SocrAI paper (Science and Engineering Ethics, 2025; behind a login).
- O'Neill, Klincewicz and Kemmer (2023), *Ethical issues with artificial ethics assistants* (Oxford Handbook of Digital Ethics), which covers privacy of moral data (seen only as a paraphrased abstract).
- The 2025 chapter *AI-aided moral enhancement – exploring opportunities and challenges* (PhilArchive, blocked).
- *Morally programmed LLMs reshape human morality* (arXiv 2604.10222), a lead found late and not read.

**Open low-priority questions:**
- Which terms the field uses, and what each refers to.
- Perspectives in non-English and non-Western literature, such as Chinese and Spanish-language philosophy journals.
- Whether a chatbot's empathy or reflective prompting carries over into kinder behavior. A registered trial, "Spillover of Empathy", was found but not read.

**Method note.** The research board is at `.research/ai-moral-improvement/`. Every quote in this report was checked against its source, except the claims marked *unverified*. A preprint and its journal version count as one source.

## 6. Sources

Babin, J. J., & Chauhan, H. S. (2026). Chatbot or humanaut? How the source of advice impacts prosocial behavior. *Journal of Behavioral and Experimental Economics, 121*. https://scholarworks.uni.edu/facpub/6909

Cheng, M., Lee, C., Khadpe, P., Yu, S., Han, D., & Jurafsky, D. (2025). *Sycophantic AI decreases prosocial intentions and promotes dependence* [Preprint]. arXiv. https://arxiv.org/abs/2510.01395

Constantinescu, M., Vică, C., Uszkai, R., & Voinea, C. (2022). Blame it on the AI? On the moral responsibility of artificial moral advisors. *Philosophy & Technology*. https://link.springer.com/article/10.1007/s13347-022-00529-z

Dillion, D., Mondal, D., Tandon, N., & Gray, K. (2025). AI language model rivals expert ethicist in perceived moral expertise. *Scientific Reports, 15*. https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11790977/fullTextXML

Foote, J., Kumar, D., Jha, B., Funkhouser, R., Bitsikokos, L., Goel, H., & Chiu, H.-C. (2026). *Taming toxic talk: Using chatbots to intervene with users posting toxic comments* [Preprint]. arXiv. https://arxiv.org/abs/2601.20100

Galatolo, A., Rappuoli, L. A., Winkle, K., & Beloucif, M. (2025). *Beyond ethical alignment: Evaluating LLMs as artificial moral assistants* [Preprint]. arXiv. https://arxiv.org/html/2508.12754

Gallagher, B. (2023, January 30). Can AI help us be better people? [Interview with J. Rueda]. *Nautilus*. https://nautil.us/can-ai-help-us-be-better-people-260216/

Giubilini, A., Porsdam Mann, S., Voinea, C., Earp, B., & Savulescu, J. (2024). Know thyself, improve thyself: Personalized LLMs for self-knowledge and moral enhancement. *Science and Engineering Ethics, 30*(6). https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11582191/fullTextXML

Giubilini, A., & Savulescu, J. (2018). The artificial moral advisor. The "ideal observer" meets artificial intelligence. *Philosophy & Technology, 31*(2), 169–188. https://pmc.ncbi.nlm.nih.gov/articles/PMC6004274

Hovd, S. N. (2023). Tools of war and virtue: Institutional structures as a source of ethical deskilling. *Frontiers in Big Data*. https://pmc.ncbi.nlm.nih.gov/articles/PMC9982729/

Jin, Y., Martinez-Maldonado, R., Shi, W., Huang, S., Zheng, M., Han, X., Gašević, D., & Yan, L. (2026). *When machines join the moral circle: The persona effect of generative AI agents in collaborative reasoning* [Preprint]. arXiv. https://arxiv.org/abs/2511.01205

Köbis, N., Rahwan, Z., Rilla, R., Supriyatno, B. I., Bersch, C., Ajaj, T., Bonnefon, J.-F., & Rahwan, I. (2025). Delegation to artificial intelligence can increase dishonest behaviour. *Nature*. https://pmc.ncbi.nlm.nih.gov/articles/PMC12488497/

Koralus, P. (2025). *The philosophic turn for AI agents: Replacing centralized digital rhetoric with decentralized truth-seeking* [Preprint]. arXiv. https://arxiv.org/html/2504.18601v1

Kruegel, S., Ostermaier, A., & Uhl, M. (2025). *ChatGPT's advice drives moral judgments with or without justification* [Preprint]. arXiv. https://arxiv.org/abs/2501.01897

Krügel, S., Ostermaier, A., & Uhl, M. (2023). ChatGPT's inconsistent moral advice influences users' judgment. *Scientific Reports, 13*, 4569. https://pmc.ncbi.nlm.nih.gov/articles/PMC10079665/

Landes, E., Voinea, C., & Uszkai, R. (2024). Rage against the authority machines: How to design artificial moral advisors for moral enhancement. *AI & Society, 40*(4), 2237–2248. https://pmc.ncbi.nlm.nih.gov/articles/PMC12078386/

Lara, F. (2021). Why a virtual assistant for moral enhancement when we could have a Socrates? *Science and Engineering Ethics, 27*(4), 42. https://pmc.ncbi.nlm.nih.gov/articles/PMC8241637/

Lara, F., & Rodríguez-López, B. (2025). Socratic nudges, virtual moral assistants and the problem of autonomy. *AI & Society*. https://link.springer.com/article/10.1007/s00146-023-01846-3

Leib, M., Köbis, N., Rilke, R. M., Hagens, M., & Irlenbusch, B. (2023). *Corrupted by algorithms? How AI-generated and human-written advice shape (dis)honesty* [Preprint]. arXiv. https://arxiv.org/abs/2301.01954

Olson, L., Guzmán, E., & Kunneman, F. (2026). *PerspectiveCoach: Exploring LLMs for developer reflection* [Preprint]. arXiv. https://arxiv.org/abs/2601.02559

Seo, Y., Jang, S., Park, H., Gutierrez, R. S., Seering, J., & Lee, U. (2026). *Ethics training agents: Facilitating group-based ethics education with role-playing and discussion for ethical reflection and exploration* [Preprint]. arXiv. https://arxiv.org/abs/2609.11529

Smith, R. L., III, Castles, R. T., & Sondergard, E. F. (2025). *The engineering ethics coach: Integrating AI chatbots to strengthen ethical decision-making in engineering economy* [Conference paper]. ASEE Annual Conference & Exposition. https://nemo.asee.org/public/conferences/365/papers/47087/view

Teng, Y., Zhong, Q., Thordsen, K. M. T. N., Montag, C., & Becker, B. (2026). *Brief chatbot interactions produce lasting changes in human moral values* [Preprint]. arXiv. https://arxiv.org/abs/2604.21430

Teo, S., & Lieder, F. (2026). *Does moral advice from large language models make people more prosocial toward outgroups?* eScholarship, University of California. https://escholarship.org/content/qt710517mw/qt710517mw.pdf

Volkman, R., & Gabriels, K. (2023). AI moral enhancement: Upgrading the socio-technical system of moral engagement. *Science and Engineering Ethics, 29*(2), 11. https://pmc.ncbi.nlm.nih.gov/articles/PMC10036265/
