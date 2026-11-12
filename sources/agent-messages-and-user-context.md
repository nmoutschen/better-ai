# Agent messages and what the user holds in mind

Research findings for the better-ai skills  
Prepared for Nicolas · Search date: 11 November 2026

**Language models assume the user shares their context instead of checking that they do, and post-training makes this worse. Trying to set aside what you know does not fix the writer's side of the problem. What has support is checking concrete cues: has this reader seen this, did they accept this name, how far back is the thing referred to.** LLMs make 77.5% fewer grounding acts than humans in the same conversations (Shaikh et al., 2024). They also start clarification three times less often than humans, and early grounding failures lead to later ones (Shaikh et al., 2025). In people, lowering reliance on their own knowledge did not improve their estimates of what others know (Tullis & Feder, 2022), and neither did incentives to ignore it (Kennedy, 1995, as cited by Tullis & Feder, 2022). Speakers can adapt with a simple signal, "has my listener heard this before?" (Galati & Brennan, 2010). For the specific cases in an agent's messages, such as earlier plans, the agent's own labels and status updates after a break, the evidence is nearby rather than direct. No study measures the cost of a reference several chat turns back, or tests a recap written for a real user.

**Scope.** How an AI agent's messages fail to match what the user currently holds in mind during an ongoing conversation or task, and what a writer or agent can do about it. Covered: common ground and grounding, audience design, the curse of knowledge, how distance to an earlier mention affects reading, conceptual pacts on names, repeating known content, resuming after an interruption, handovers, status updates and agent transparency, and LLM drift over many turns. The goal is to decide which rules to add to `/write-better`.

**Status.** All 7 high-priority and 6 medium-priority questions are closed: 12 answered, 1 answered with only indirect evidence (status updates). One low-priority question is open: how to return to the main task after a side question. 37 sources in English; searches in German and French found nothing usable beyond English sources. All 63 recorded claims were checked against their source pages. Many sources were read as abstracts only, and the text says so where it matters. The research board is in `.research/shared-context-in-agent-messages/`.

## 1. LLMs assume shared context

- **Fewer grounding acts.** Given the same conversation, LLM replies were 77.5% less likely than human replies to contain grounding acts, such as a clarification question or a restatement of what the other person meant. The models tend to assume they understood and go on to give suggestions, which the authors call *presumptive grounding* (Shaikh et al., 2024).
- **Training makes it worse.** Supervised fine-tuning did not improve grounding, and preference optimization eroded it (Shaikh et al., 2024).
- **Early failures cascade.** In logs of human-LLM conversations, LLMs started clarification three times less often and made follow-up requests sixteen times less often than humans. Grounding failures early in a conversation raised the chance of later failures. The authors call their own fix preliminary and say training must change (Shaikh et al., 2025). Both papers share a first author, so this is not independent replication.
- **Benchmarks show the same pattern.** When the person could not see the AI's actions, the AI often did not clarify or repair, and did not update its assumptions after a repair. People adopted the AI's labels for objects and carried the load of remembering them, unless they asked the AI to list them (Poelitz et al., 2026). Vision-language models could not produce and resolve references interactively well enough for smooth communication (Zeng et al., 2026, abstract only).
- **LLMs lose the user's details over turns.** When task details arrived over several turns, every top model tested scored lower (39% on average). The drop came mostly from unreliability, and the models did not recover from wrong assumptions made early. Strong models lost as much as small ones. Repeating all earlier user information each turn recovered only part of the loss (Laban et al., 2025). Agents given a goal in the system prompt drifted from it over long contexts in every model tested (Arike et al., 2025, abstract only).

**What this means for write-better:** The agent's default is to assume shared context. A rule that relies on the agent's sense of what the user knows starts from a biased judgment.

## 2. How people judge what their reader knows, and what helps

- **No full model of the partner.** Speakers do not keep a full model of what their partner knows. They use what is easy to access and rely on the listener to signal trouble (Horton & Brennan, 2016). One account holds that people are egocentric at first and take the partner's view only through later repair (Horton & Brennan, 2016).
- **A one-bit signal works.** Speakers retelling a story shortened it and dropped detail for a listener who had already heard it, and much less for a new listener. The authors propose that a one-bit model, "has my audience heard this before?", is enough to guide this (Galati & Brennan, 2010, abstract only).
- **Trying harder does not work.** Lowering people's reliance on their own knowledge did not make their estimates of novices more accurate. The authors attribute the error to missing cues about what the other person knows (Tullis & Feder, 2022). Incentives to ignore one's own knowledge did not reduce the bias either (Kennedy, 1995, as cited by Tullis & Feder, 2022).
- **Feedback on outcomes helps.** Narrative feedback about how the other person actually did reduced egocentric bias, and accuracy-only feedback did not (Damen et al., 2021, abstract only). The bias also shrank with experience and feedback (Loewenstein et al., 2006, abstract only).

**What this means for write-better:** A rule like "imagine what the user knows" has no support. Concrete checks have some support: did the user see this item, did they use this name. The user's reaction is the feedback that corrects the estimate.

## 3. Names one side made up

- **Names are agreed in pairs.** When people refer to the same thing repeatedly, they settle on a name. The name is tied to the partner it was agreed with: after such an agreement, listeners were slower when the original partner switched to a new name than when a new partner used it (Metzing & Brennan, 2003, abstract only).
- **One side cannot create a shared name.** When a listener cannot tell what a name refers to, the two work out a new expression together. A name only one side proposed is not shared until the other accepts it (Heeman & Hirst, 1995, describing Clark & Wilkes-Gibbs, 1986).
- **New partners start over.** With a new partner, speakers think about the object afresh and put in about as much effort to ground their references as with the first partner (Horton & Brennan, 2016).
- **AI labels shift the work.** People adopted an AI's labels and carried the memory load themselves (Poelitz et al., 2026).

**What this means for write-better:** A label the agent invented mid-task, such as "phase 2" or "Option B", is not a shared term unless the user has used or accepted it. A label agreed many turns ago, or in an earlier session, may need grounding again. Evidence on time gaps is thin.

## 4. How far back a reference points

- **Distance costs time.** Adults read a sentence faster when the thing it referred to was mentioned one sentence back than two or three sentences back. Later experiments put the boundary at the last clause. The authors read this as the last clause processed holding a privileged place in working memory (Clark & Sengul, 1979).
- **The boost fades fast.** A pronoun's boost to its referent was gone by the end of the next sentence (Love & McKoon, 2011). Search snippets mention studies that found no distance effect, but none of them could be read.
- **Long chats are hard to trace.** No study measures comprehension by how many chat turns back a reference points. In long chats with an LLM, users struggled to trace which of their earlier requests had been met. In a 20-person study, users without a goal tracker scrolled through long logs to find what went wrong. The same paper cites work finding that chats in writing tasks often stay at 10 turns or fewer because the growing log is tiring (Coscia et al., 2025).

**What this means for write-better:** The sentence-level results do not tell how costly a reference to an earlier plan or to tool output is. They show the cost rises quickly with distance even within a paragraph. A rule to restate what an earlier item is, rather than only pointing to it, is a reasonable design choice, not a tested rule.

## 5. Repeating what the reader knows

- **Repetition costs knowledgeable readers.** A review of 63 studies found that repeating the same content hinders learners with high prior knowledge, while novices may benefit (Trypke et al., 2023).
- **The right restatement helps.** Restating the last one or two sentences before an interruption cancelled the cost of the interruption, and restating the theme did not (Glanzer et al., 1984, as reported by Ledoux & Gordon, 2006; not read directly).

**What this means for write-better:** Restating what the user just said or decided adds reading without help. A short restatement of the specific item the user needs right now, after a gap, can help. The two findings point in the same direction: restate the specific thing the reader needs to continue, and only that.

## 6. Resuming after a break

- **A cue tied to the last action helps.** A salient cue marking the last action, such as a red arrow, cut the time to resume. A subtle cue, the cursor left at the last spot, was no better than no cue (Trafton et al., 2005). Earlier work found that a visible marker did not help, so the evidence is mixed (Trafton et al., 2005).
- **Cues must stay the same.** Time to prepare before leaving reduced the cost of resuming, but the benefit was lost when the visual cues changed during the break (Hodgetts & Jones, 2006). Interruptions that prevented rehearsing the goal led to slower resumption (Monk et al., 2004).
- **Showing past activity helps programmers.** Automated cues showing their prior activity doubled programmers' task success after an interruption, compared with their own notes (Parnin & DeLine, 2010, abstract only). Programmers who resume rarely start at once: only 10% of sessions began coding within a minute, because they hunt for task context first (Parnin & Rugaber, 2011).
- **Recorded state sometimes did not help.** One small thesis found a tool that recorded work state helped only when people did not consult it at the moment of resuming (Almangush, 2017, abstract only).
- **No direct test.** No controlled test of a prose recap of what changed during a break was found.

**What this means for write-better:** When the user comes back after a break, the first lines should give a specific cue to where they left off: the last thing done and the next step. A general recap has less support. A changed setting, such as "I reorganised the files while you were away", removes the cues the user relied on and needs to be stated.

## 7. Handovers and status updates

- **Structured handovers.** Effective clinical handovers use a fixed, named structure. I-PASS gives illness severity first, then a summary, an action list, situation awareness with if/then contingencies, and a synthesis by the receiver (Starmer et al., 2022). After I-PASS was introduced, written handoffs with all five parts rose from 10.4% to 73.5%, and handoff-related adverse events fell 47%, in a design without a randomized control (Starmer et al., 2022). SBAR and ISBAR separate the current Situation from the Background history (Lazzari & Rabottini, 2025). The evidence for ISBAR is weak, with few randomized trials (Lazzari & Rabottini, 2025).
- **What an agent should report.** A situation-awareness model of agent transparency says an agent should report what it is doing, why, and what it will do next. In one experiment (n = 180, a game task), reporting what the agent was doing gave the best task performance, and the reasons raised trust without changing workload (Daronnat et al., 2022). The paper's discussion and abstract disagree on which type of explanation did better.
- **Coding-agent users want the changes.** Developers using an in-IDE agent found its explanations too verbose, and the verbosity once made a participant miss a link. They wanted to see the changes rather than long analysis. When the agent changed more than asked, they had to reject the change and restrict it (Kumar et al., 2025). Engineers wanted agents to explain their reasoning, raise knowledge gaps and ask questions, and to present a plan for approval before acting (Dong et al., 2025).
- **One tested fix is a separate view.** A persistent graph of the project beside the chat improved comprehension compared with chat alone in a 16-person randomized study (Chou et al., 2026, abstract only). The authors note that delegating to an agent can erode the developer's understanding of the project over time.

**What this means for write-better:** A status message should give the current state first and keep history separate, then list what the user must act on. No source compares current-state reports with change reports, so how much history to include is a design choice.

## 8. Asking instead of assuming

- **Users preferred being asked.** Users preferred documents an LLM wrote after asking follow-up questions, and valued open-ended questions over simple information-gathering (Tix, 2024, abstract only).
- **Asking selectively works better.** Asking only on the 10% of inputs an uncertainty estimate picked doubled the gain of asking at random (Zhang & Choi, 2023, abstract only).
- **Asking can underperform.** In a small comparison, a clarifying-question prompt scored below a checklist prompt and used more tokens (Ghosh, 2026, abstract only).

`/ask-better` already covers when to ask. These findings support asking selectively, not by default.

## 9. Gaps

- No study measures how a reference several chat turns back, or to output the user never saw, affects comprehension. The rules for those cases extend sentence-level and resumption findings.
- No study tests an agent-written recap or status report with real users. The multi-turn studies use simulated users.
- No source compares reporting the current state with reporting the changes since last time.
- No adult study was found on how long an agreed name stays shared after a time gap.
- Blocked or not read directly: Epley et al. (2004) on time pressure and insufficient adjustment; Brennan & Clark (1996); Horton & Keysar (1996); the Cochrane handover review; Kalyuga's expertise-reversal papers; Garrod & Sanford (1977), reported in snippets to find no distance effect.
- Open, low priority: how to return to the main task after a side question.

## References

Almangush, R. (2017). *Exploring resumption aids for tasks involving 3D models on tablets* [Master's thesis, Dalhousie University]. DalSpace. https://dalspace.library.dal.ca/handle/10222/72862

Arike, R., Donoway, E., Bartsch, H., & Hobbhahn, M. (2025). *Technical report: Evaluating goal drift in language model agents* (arXiv:2505.02709). arXiv. https://arxiv.org/abs/2505.02709

Chou, C., Lee, S. Y.-T., Choudhuri, R., & Ma, K.-L. (2026). *Vibe-GUIDE: A graph-based user interface in IDEs for oversight in vibe coding* (arXiv:2609.23859). arXiv. https://arxiv.org/abs/2609.23859

Clark, H. H., & Sengul, C. J. (1979). In search of referents for nouns and pronouns. *Memory & Cognition, 7*(1), 35–41. https://web.stanford.edu/~clark/1970s/Clark,%20H.H.%20_%20Sengul,%20C.%20J.%20_In%20search%20of%20referents%20for%20nouns%20and%20pronouns_%201979.pdf

Coscia, A., Guo, S., Koh, E., & Endert, A. (2025). OnGoal: Tracking and visualizing conversational goals in multi-turn dialogue with large language models. *UIST 2025*. https://arxiv.org/html/2508.21061

Damen, D., van Amelsvoort, M., van der Wijst, P., Pollmann, M., & Krahmer, E. (2021). Lifting the curse of knowing: How feedback improves perspective-taking. *The Quarterly Journal of Experimental Psychology, 74*(6), 1054–1069. https://research.tilburguniversity.edu/en/publications/lifting-the-curse-of-knowing-how-feedback-improves-perspective-ta/

Daronnat, S., Azzopardi, L., & Halvey, M. (2022). Comparing levels and types of situational-awareness based agent transparency in human-agent collaboration. *Proceedings of the Human Factors and Ergonomics Society Annual Meeting, 66*(1), 1169–1173. https://strathprints.strath.ac.uk/88153/1/Daronnat-etal-PHFESAM-2022-Comparing-levels-and-types-of-situational-awareness.pdf

Dong, T., Sampath, H., Lee, J. Y., Shi, S. Y., & Macvean, A. (2025). *From correctness to collaboration: Toward a human-centered framework for evaluating AI agent behavior in software engineering* (arXiv:2512.23844). arXiv. https://arxiv.org/html/2512.23844v1

Galati, A., & Brennan, S. E. (2010). Attenuating information in spoken communication: For the speaker, or for the addressee? *Journal of Memory and Language, 62*(1), 35–51. https://researchconnect.stonybrook.edu/en/publications/attenuating-information-in-spoken-communication-for-the-speaker-o/

Ghosh, S. (2026). *Less back-and-forth: A comparative study of structured prompting* (arXiv:2605.20149). arXiv. https://arxiv.org/abs/2605.20149

Heeman, P. A., & Hirst, G. (1995). Collaborating on referring expressions. *Computational Linguistics, 21*(3). https://ar5iv.labs.arxiv.org/html/cmp-lg/9504003

Hodgetts, H. M., & Jones, D. M. (2006). Contextual cues aid recovery from interruption: The role of associative activation. *Journal of Experimental Psychology: Learning, Memory, and Cognition, 32*(5), 1120–1132. https://www.interruptions.net/literature/Hodgetts-JEP_LMC06.pdf

Horton, W. S., & Brennan, S. E. (2016). The role of metarepresentation in the production and resolution of referring expressions. *Frontiers in Psychology, 7*. https://doi.org/10.3389/fpsyg.2016.01111

Kumar, A., et al. (2025). *Sharp tools: How developers wield agentic AI in real software engineering tasks* (arXiv:2506.12347). arXiv. https://arxiv.org/html/2506.12347v2

Laban, P., Hayashi, H., Zhou, Y., & Neville, J. (2025). *LLMs get lost in multi-turn conversation* (arXiv:2505.06120). arXiv. https://arxiv.org/abs/2505.06120

Lazzari, C., & Rabottini, M. (2025). The use of Introduction, Situation, Background, Assessment, and Recommendation handover in the COVID-19 pandemic and non-COVID clinical settings: A systematic review and meta-analysis. *Frontiers in Health Services*. https://www.frontiersin.org/journals/health-services/articles/10.3389/frhs.2025.1380948/full

Ledoux, K., & Gordon, P. C. (2006). Interruption-similarity effects during discourse processing. *Memory, 14*(7), 789–803. https://pmc.ncbi.nlm.nih.gov/articles/PMC1766328

Loewenstein, G., Moore, D. A., & Weber, R. A. (2006). Misperceiving the value of information in predicting the performance of others. *Experimental Economics, 9*(3), 281–295. https://www.cambridge.org/core/journals/experimental-economics/article/misperceiving-the-value-of-information-in-predicting-the-performance-of-others/B376A716365733DD735B7E2524F91C43

Love, J., & McKoon, G. (2011). Rules of engagement: Incomplete and complete pronoun resolution. *Journal of Experimental Psychology: Learning, Memory, and Cognition, 37*(4), 874–887. https://pmc.ncbi.nlm.nih.gov/articles/PMC3130815

Metzing, C., & Brennan, S. E. (2003). When conceptual pacts are broken: Partner-specific effects on the comprehension of referring expressions. *Journal of Memory and Language, 49*(2), 201–213. https://researchconnect.stonybrook.edu/en/publications/when-conceptual-pacts-are-broken-partner-specific-effects-on-the-/

Monk, C. A., Boehm-Davis, D. A., & Trafton, J. G. (2004). Recovering from interruptions: Implications for driver distraction research. *Human Factors*. https://www.interruptions.net/literature/Monk-HF04.pdf

Parnin, C., & DeLine, R. (2010). Evaluating cues for resuming interrupted programming tasks. *CHI '10*. ACM. https://www.microsoft.com/en-us/research/publication/evaluating-cues-for-resuming-interrupted-programming-tasks/

Parnin, C., & Rugaber, S. (2011). Resumption strategies for interrupted programming tasks. *Software Quality Journal*. https://sites.cc.gatech.edu/reverse/repository/resumptionstrategies.pdf

Poelitz, C., Doshi-Velez, F., & Lindley, S. (2026). *A benchmark to assess common ground in human-AI collaboration* (arXiv:2602.21337). arXiv. https://arxiv.org/abs/2602.21337

Shaikh, O., Gligorić, K., Khetan, A., Gerstgrasser, M., Yang, D., & Jurafsky, D. (2024). Grounding gaps in language model generations. *Proceedings of NAACL 2024*. https://arxiv.org/html/2311.09144v2

Shaikh, O., Mozannar, H., Bansal, G., Fourney, A., & Horvitz, E. (2025). Navigating rifts in human-LLM grounding: Study and benchmark. *Proceedings of ACL 2025*. https://arxiv.org/html/2503.13975v2

Starmer, A. J., Spector, N. D., O'Toole, J. K., et al. (2022). Implementation of the I-PASS handoff program in diverse clinical environments: A multicenter prospective effectiveness implementation study. *Journal of Hospital Medicine*. https://pmc.ncbi.nlm.nih.gov/articles/PMC10964397/

Tix, B. J. (2024). *Follow-up questions improve documents generated by large language models* (arXiv:2407.12017). arXiv. https://arxiv.org/abs/2407.12017

Trafton, J. G., Altmann, E. M., & Brock, D. P. (2005). Huh, what was I doing? How people use environmental cues after an interruption. *Proceedings of the Human Factors and Ergonomics Society 49th Annual Meeting*. https://www.interruptions.net/literature/Trafton-HFES05.pdf

Trypke, M., Stebner, F., & Wirth, J. (2023). Two types of redundancy in multimedia learning: A literature review. *Frontiers in Psychology, 14*. https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1148035/full

Tullis, J. G., & Feder, B. (2022). The "curse of knowledge" when predicting others' knowledge. *Memory & Cognition*. https://pmc.ncbi.nlm.nih.gov/articles/PMC9794110/

Zeng, P., Li, W., Paige, A. J., Wang, Z., Kaliosis, P., Samaras, D., Zelinsky, G., Brennan, S. E., & Rambow, O. (2026). *LVLMs and humans ground differently in referential communication* (arXiv:2601.19792). arXiv. https://arxiv.org/abs/2601.19792

Zhang, M. J. Q., & Choi, E. (2023). *Clarify when necessary: Resolving ambiguity through interaction with LMs* (arXiv:2311.09469). arXiv. https://arxiv.org/abs/2311.09469
