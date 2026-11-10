# Explaining for understanding: what an AI agent can do

Research findings for the better-ai skills  
Prepared for Nicolas · Search date: 9 November 2026

**The best-supported way to make an explanation leave an accurate understanding is to name the misconception the user is likely to hold and refute it. The main risk is that an explanation makes people feel they understand more than it makes them understand.** Four findings stand out:

- **Refuting a misconception works.** Texts that state a common misconception, say it is wrong and explain the correct idea did better than standard texts across 44 comparisons. The effect is moderate, g = 0.41, or 0.28 after correcting for publication bias (Schroeder & Kucera, 2022). Repeating the misconception in order to correct it does not reliably backfire (Swire-Thompson et al., 2020).
- **Feeling you understand is not understanding.** People overrate how well they understand how things work, much more than they overrate what they know about facts or procedures (Rozenblit & Keil, 2002). Two explanations, one containing misconceptions and one correct, left learners equally sure they understood. The one with misconceptions also left them with more misconceptions (Kulgemeyer & Wittwer, 2023).
- **AI explanations make this worse.** LLM explanations increased reliance on wrong answers as much as on correct ones. Giving sources, or explanations that showed inconsistencies, reduced reliance on wrong answers (Kim et al., 2025). Learning a topic from LLM summaries left shallower knowledge than web search with the same facts, across seven experiments (Melumad & Yun, 2025).
- **Explainers cannot fix the curse of knowledge by trying harder.** Experts misjudge what laypeople know (the "curse of knowledge"). Trying to set their own knowledge aside did not help them judge better (Tullis & Feder, 2022). What helped was specific information about the person: experts then made targeted changes, not just simpler wording (Nückles et al., 2005).

The rest of the evidence is thinner:

- Analogies help novices draw inferences but cost literal accuracy, and they can mislead (Donnelly & McDaniel, 1993, 2000).
- Irrelevant detail lowers learning and makes bad explanations look good (Mayer, 2005; Weisberg et al., 2008).
- Asking the user to explain back has support in learning studies, but not in one-off explanations (Bisra et al., 2018).

**Scope.** This report covers explanations given in a conversation whose goal is that the user UNDERSTANDS: that they hold an accurate model of a topic, mechanism or system. It does not cover teaching the user to do something without AI, which is in `sources/ai-agent-teaching-new-topics.md`, or general text design, which is in `sources/writing-for-human-cognition.md`. Expertise reversal and seductive details also appear in `sources/visual-storytelling.md` and `sources/visual-representation-of-information.md`.

**Status.** The research stopped at the `medium` level: no high- or medium-priority question is open. One question is contested (section 7). I checked 37 of the board's 66 claims against their pages. Seven claims could not be confirmed and are marked unverified; this report flags the two it uses (Aslanov et al. and the coherence finding). The research board is in `.research/explaining-for-understanding/`.

**Reading level of the evidence.** These sources were read in full or in large part: Schroeder and Kucera (2022), Swire-Thompson et al. (2020), Rozenblit and Keil (2002), Tullis and Feder (2022), Kulgemeyer and Wittwer (2023), Melumad and Yun (2025), Bisra et al. (2018), Richland and Zhao (2026) and Yen and Leasure (2019). Most others were read as abstracts. Many primary papers could not be read, because of publisher blocks or PDFs the tools could not decode. They include the expertise reversal papers, Wittwer and Renkl's work on instructional explanations, McNamara's coherence studies and Lombrozo's 2016 review. Most studies use students reading short science texts, tested the same day. No study read compares explanation methods in a conversation with an AI.

## 1. Findings at a glance

| Finding | Evidence | Strength |
|---|---|---|
| **Refuting the misconception beats a standard explanation** (g = 0.41; 0.28 adjusted) | Schroeder and Kucera (2022), 44 comparisons | Moderate, mostly same-day tests |
| **Repeating the myth to correct it does not reliably backfire** | Swire-Thompson et al. (2020) | Review, misinformation research |
| **Refutation corrects misconceptions held with high confidence**; low-confidence ones did not benefit | Van Loon et al. (2015), N = 114 eighth graders | One study, abstract |
| **People overrate their understanding of how things work**; trying to explain lowers the rating | Rozenblit and Keil (2002) | Strong, repeated across 12 studies |
| **A wrong explanation leaves the same feeling of understanding** as a correct one | Kulgemeyer and Wittwer (2023), N = 149 | One experiment |
| **AI explanations raise reliance on wrong answers as much as right ones**; sources reduce it | Kim et al. (2025), N = 308, pre-registered | One study, abstract |
| **LLM summaries give shallower knowledge than web search** with the same facts | Melumad and Yun (2025), 7 experiments, n ≈ 10,400 | Strong for its task |
| **Consulting ChatGPT inflated self-rated ability to explain** more than reading the same text | Aslanov et al. (2026), 34 per group | One small study, not verified by me |
| **Experts cannot de-bias themselves; specific information about the listener helps** | Tullis and Feder (2022); Nückles et al. (2005), 80 pairs | Two studies, one abstract |
| **Analogies help inference but cost literal accuracy**, and can hurt knowledgeable learners | Donnelly and McDaniel (1993, 2000) | Abstracts |
| **Several aligned comparisons beat one concrete analogy** | Richland and Zhao (2026) | Review |
| **Irrelevant detail lowers learning** and makes bad explanations look good | Mayer (2005); Weisberg et al. (2008) | Strong for detail; allure effect modest in replication |
| **Explaining it yourself beats reading an explanation** (g = .35), and any explanation beats none | Bisra et al. (2018), 64 studies | Meta-analysis, learning contexts |
| **Do people prefer simple explanations?** | Lombrozo (2007) vs Zemla et al. (2023) | **Contested** |

## 2. Correcting misconceptions

A refutation states a common misconception, says it is wrong, and explains the correct idea. In a meta-analysis of 44 comparisons, refutation texts did better than other texts, with "a moderate overall effect size (g = 0.41, p < 0.001, 95% CI [0.30, 0.51], n = 3,869)" (Schroeder & Kucera, 2022). After correcting for publication bias, the effect fell to g = 0.28, still a small-to-moderate effect. The effect did not vary significantly with the reader's age or prior knowledge, and only five of the 44 comparisons favoured the standard text.

Three limits apply:

- Most tests were on the same day; only two studies found effects lasting more than a month (Schroeder & Kucera, 2022).
- A later experiment found that refutation texts changed how students read but not what they learned (Hunsu et al., 2023).
- The texts were short passages written by researchers, not conversation.

Agents may worry that naming the misconception plants it. Misinformation research does not support that worry: "avoiding the repetition of the original misconception within the correction appears to be unnecessary" (Swire-Thompson et al., 2020). The same review advises pairing the misconception "clearly and saliently" with the correction. This is indirect evidence, because it comes from corrections of news claims, not from explanations.

Refutation helped most where it was needed most. In one study, refutation texts corrected misconceptions students held with high confidence, while "low-confidence misconceptions did not benefit from reading refutation texts" (Van Loon et al., 2015). No study read tests whether an explainer should first ask the user what they believe.

## 3. Understanding versus the feeling of understanding

People believe they understand how devices and natural phenomena work far better than they do. When they try to explain step by step, their rating of their own understanding drops: "Attempts to explain the various phenomena led to a decrease in self-rated understanding" (Rozenblit & Keil, 2002). The illusion is specific to explanations: "Procedures and Narratives show no drop, while Geography Facts show only a small drop." Warning people that they would be tested reduced the illusion but did not remove it.

Receiving an explanation can create the same illusion. Physics learners who watched an explainer video built around misconceptions "developed an equal belief of understanding, but more misconceptions and fewer scientifically correct conceptions than those from the control group" (Kulgemeyer & Wittwer, 2023). So the user's sense that an explanation was clear cannot tell the agent whether it was correct. A 2025 preprint found that demanding follow-up tasks after an explainer video reduced the illusion more than the video alone, and that learners with less prior knowledge were more prone to it (Hörnlein & Kulgemeyer, 2025, abstract only).

## 4. AI explanations specifically

Three studies bear directly on AI:

- **Reliance.** In a pre-registered experiment (N = 308), "the presence of explanations increases reliance on both correct and incorrect responses" from an LLM. Reliance on incorrect answers fell "when sources are provided or when explanations exhibit inconsistencies" (Kim et al., 2025).
- **Depth.** Across seven experiments, people who learned a topic from LLM summaries developed "shallower knowledge than when they learn through standard web search, even when the core facts in the results are the same" (Melumad & Yun, 2025).
- **Perceived ability.** In one small study, students who consulted ChatGPT overestimated their ability to explain most. They overestimated more than students who read identical texts without the chat, and their explanations were rated lower (Aslanov et al., 2026). A worker read this PDF, but I could not open it to check the quotes.

LLM accuracy matters because users cannot catch errors themselves. In one benchmark, human evaluators were "deceived by incorrect responses from GPT-4 Turbo" on science questions (Bajpai et al., 2024, preprint abstract). LLM-written analogies helped high-school students, but teachers had to guide their use (Shao et al., 2025, preprint abstract).

## 5. Adapting to what the user knows

**Experts cannot fix the curse of knowledge by trying harder.** People's own knowledge distorts their estimates of what others know. In Tullis and Feder (2022), "Experimentally reducing reliance on one's own knowledge did not improve the accuracy of estimates." The authors conclude that the problem is that "estimators lack diagnostic cues about others' knowledge."

**Specific information about the listener does help.** In 80 expert–layperson pairs, experts "often fail to consider the limited domain knowledge of laypersons." Giving them information about the specific layperson made the communication more effective and efficient. It worked by enabling "specific partner adjustments", not by making experts simplify in general (Nückles et al., 2005, abstract). The abstract does not say how effectiveness was measured.

**The right amount of guidance depends on prior knowledge.** Guidance that helps a novice can be redundant for someone who knows more (the expertise reversal effect). The primary papers could not be read. A blog summary of a 2025 meta-analysis of 60 studies reports that more structure helped learners with little prior knowledge and less structure helped those with more (Watson, 2025, low trust). Text coherence shows the same pattern: low-knowledge readers learned more from texts with explicit links between ideas, and high-knowledge readers learned more from less explicit texts. This finding replicated in linear text but not in hypertext (Salmerón et al., 2005, quote unverified).

**How to find out what the user knows.** Two 2026 preprints propose that an agent ask targeted questions about the user's expertise, or infer it from behaviour. The second reports higher satisfaction, not better understanding (Cao & Huang, 2026; Park et al., 2026).

## 6. Analogies

Analogies trade one kind of understanding for another. Novices "consistently answered basic-level questions most accurately when concepts were expressed literally," but answered inference questions better after analogies (Donnelly & McDaniel, 1993, abstract). For learners with prior knowledge, "analogy decreased performance when the same targets were presented to facilitate contact with prior knowledge" (Donnelly & McDaniel, 2000, abstract).

How the analogy is presented also matters. A 2026 review finds that "instructional designs that incorporate carefully aligned, multiple comparisons are particularly effective". By contrast, "single, highly concrete analogies may support initial sensemaking but carry a greater risk of misunderstanding" (Richland & Zhao, 2026). A teaching study says students may misread an analogy without supporting cues such as imagery or gestures (University of California, Irvine, 2007). Science-education authors call it crucial to state where the analogy breaks down, because "alternative conceptions often follow" when it does (Toma & Rahman, 2021). This last point is practitioner guidance, not an experiment.

## 7. Detail, mechanism and simplicity

**Irrelevant detail hurts.** People learn more deeply when extraneous material is left out. Mayer's coherence principle was supported in 10 of 11 tests (Mayer, 2005, abstract). A meta-analysis of 58 studies found that interesting but irrelevant details lower learning (Zaske, 2020, press release). Irrelevant detail also makes bad explanations look good: neuroscience jargon had "a particularly striking effect on nonexperts' judgments of bad explanations" (Weisberg et al., 2008). A 2024 replication found that effect modest (Väth et al., 2024, via a third-party summary).

**People value mechanism.** Compared with judgments of causal strength, judgments of explanation quality are "more sensitive to mechanism and less sensitive to covariation" (Vasil & Lombrozo, 2022). This measures what people judge to be a good explanation, not what they learn from it.

**Whether people prefer simple explanations is contested.**

- Lombrozo (2007) found that people prefer simpler explanations and treat simplicity as evidence of truth: "simpler explanations are assigned a higher prior probability". The preference was overcome only when probability information "unambiguously supports a complex explanation".
- Zemla et al. (2023) found that "the presence of causal mechanisms in an explanation is one factor that reduces adherence" to simplicity. They also found that complex explanations promote "a greater sense of understanding".
- Blom et al. (2024) found that satisfaction depended on how consistently the causes related to each other.

No read source found evidence on which elements of a causal explanation improve understanding, such as the chain of causes or explaining why and not only what, or on how much mechanism to include.

## 8. Checking understanding without a lesson

**Explaining it yourself helps.** In a meta-analysis of 64 studies, prompting learners to explain material to themselves beat giving them an instructional explanation (g = .35), and beat giving no additional explanation by more (g = .67) (Bisra et al., 2018). Two findings within it matter for an explainer:

- Learners who could also get an explanation on demand did worse than learners who only got the prompts.
- Results were best "when learners were prompted to compare their self-explanations to instructional explanations".

These studies come from learning settings, so they support offering an explain-back step, not requiring one.

**Teach-back has weak evidence.** In teach-back, the person restates what they were told. A review of 26 studies found that every study combined teach-back with other interventions, so "outcomes found in this review may be associated with those interventions and not with teach-back itself" (Yen & Leasure, 2019). The evidence on retention "was limited".

**Conversation may help more than a monologue.** In a study with a human expert answering follow-up questions, conversation improved self-reported comprehension of AI explanations (Zhang et al., 2023). Comprehension was self-rated, which section 3 shows is unreliable. Overhearing a dialogue beat a monologue only on written recall (Driscoll et al., 2003). No read study compares a chat with an AI against a single AI explanation.

## 9. What this means for an `/explain-better` skill

The evidence supports rules that the current skills do not contain:

| Candidate rule | Evidence | Already in another skill? |
|---|---|---|
| Name the likely misconception, say it is wrong, and explain the correct idea | Section 2 | No |
| Don't treat the user's sense of clarity as evidence of understanding; offer a short explain-back or prediction | Sections 3, 8 | `write-better` §5 for the writer's own judgment; `teach-better` for lessons |
| Give sources and state inconsistencies, because AI explanations raise reliance on wrong answers | Section 4 | Partly: `write-better` §4.2 states limits |
| Ask the user what they know or believe, rather than guessing harder | Section 5 | `teach-better` §1.2, for lessons |
| Prefer several aligned comparisons to one analogy; state where an analogy breaks; use analogies with care for experts | Section 6 | No |
| Make causal links explicit for novices, less so for experts | Section 5 | `write-better` §2.2, without the expert caveat |
| Leave out irrelevant and impressive-sounding detail | Section 7 | `write-better` §2.1 |

About five of these rules are specific to explaining, and two repeat `write-better`. The strongest evidence is for refutation and for the illusion of understanding. The rules on analogies, adapting to the user and checking understanding rest on thin or indirect evidence, and none was tested on AI explanations in conversation.

## 10. Open questions and gaps

- **Contested:** whether people prefer simple explanations, and whether that preference leads them to accept wrong ones (section 7).
- **Not found:**
  - which elements of a causal explanation improve understanding
  - how an explainer can check understanding in a one-off explanation
  - whether asking for the user's belief before refuting it helps
  - how to assess prior knowledge quickly, such as Kalyuga's rapid tests, which appeared only in search text
- **Blocked sources that could change the answer:**
  - Wittwer and Renkl (2008) and their 2010 meta-analysis on when instructional explanations fail
  - the primary expertise reversal papers and the 2025 meta-analysis
  - McNamara and Kintsch (1996) on coherence
  - Lombrozo's 2016 review of explanatory preferences
  - Fernbach et al. (2013), where explaining policies moderated political views, read only through a press release
  - Clement (1993) on bridging analogies

## References

Aslanov, I., Felmer, P., & Guerra, E. (2026). *Evidence for an illusion of understanding in AI-assisted explanations* [Conference paper]. Cognitive Science Society proceedings. eScholarship. https://escholarship.org/content/qt8cr599sr/qt8cr599sr.pdf

Bajpai, P., Chatterjee, N., Dutta, S., & Chakraborty, T. (2024). *Can LLMs replace Neil deGrasse Tyson? Evaluating the reliability of LLMs as science communicators* (arXiv:2409.14037). arXiv. https://arxiv.org/abs/2409.14037

Bisra, K., Liu, Q., Nesbit, J. C., Salimi, F., & Winne, P. H. (2018). Inducing self-explanation: A meta-analysis. *Educational Psychology Review, 30*(3), 703–725. https://www.gwern.net/doc/psychology/spaced-repetition/2018-bisra.pdf

Blom, M., Singh, R., Miller, T., Sonenberg, L., Trentelman, K., & Saulwick, A. (2024). *Explainable agency: Human preferences for simple or complex explanations* (arXiv:2403.12321). arXiv. https://arxiv.org/abs/2403.12321

Cao, Z., & Huang, C. (2026). *Clarify user expertise: Towards proactive conversational agents tailoring responses to user proficiency* (arXiv:2608.22266). arXiv. https://arxiv.org/abs/2608.22266

Donnelly, C. M., & McDaniel, M. A. (1993). Use of analogy in learning scientific concepts. *Journal of Experimental Psychology: Learning, Memory, and Cognition, 19*(4), 975–987. https://profiles.wustl.edu/en/publications/use-of-analogy-in-learning-scientific-concepts/

Donnelly, C. M., & McDaniel, M. A. (2000). Analogy with knowledgeable learners: When analogy confers benefits and exacts costs. *Psychonomic Bulletin & Review, 7*(3), 537–543. https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%22Analogy%20with%20knowledgeable%20learners%22&format=json&resultType=core

Driscoll, D. M., Craig, S. D., Gholson, B., Ventura, M., Hu, X., & Graesser, A. C. (2003). Vicarious learning: Effects of overhearing dialog and monologue-like discourse in a virtual tutoring session. *Journal of Educational Computing Research, 29*(4), 431–450. https://digitalcommons.memphis.edu/facpubs/8941

Hörnlein, M., & Kulgemeyer, C. (2025). *Learning science and the illusion of understanding: Exploring the effects of integrating learning tasks after explainer videos* (arXiv:2512.02824). arXiv. https://arxiv.org/abs/2512.02824

Hunsu, N. J., Adesope, O., & McCrudden, M. T. (2023). The effects of text structure on students' use of comprehension strategies and cognitive outcomes during science text processing. *Frontiers in Education, 8*. https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2023.1112804/full

Kim, S. S. Y., Vaughan, J. W., Liao, Q. V., Lombrozo, T., & Russakovsky, O. (2025). *Fostering appropriate reliance on large language models: The role of explanations, sources, and inconsistencies* (arXiv:2502.08554). arXiv. https://arxiv.org/abs/2502.08554

Kulgemeyer, C., & Wittwer, J. (2023). Misconceptions in physics explainer videos and the illusion of understanding: An experimental study. *International Journal of Science and Mathematics Education, 21*(2), 417–437. https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8932681/fullTextXML

Lombrozo, T. (2007). Simplicity and probability in causal explanation. *Cognitive Psychology, 55*(3), 232–257. https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:17097080%20AND%20SRC:MED&format=json&resultType=core

Mayer, R. E. (2005). Principles for reducing extraneous processing in multimedia learning: Coherence, signaling, redundancy, spatial contiguity, and temporal contiguity principles. In *The Cambridge handbook of multimedia learning*. Cambridge University Press. https://www.cambridge.org/core/books/abs/cambridge-handbook-of-multimedia-learning/principles-for-reducing-extraneous-processing-in-multimedia-learning-coherence-signaling-redundancy-spatial-contiguity-and-temporal-contiguity-principles/C98AB3A6CE760DD63C048936EA0B3B44

Melumad, S., & Yun, J. H. (2025). Experimental evidence of the effects of large language models versus web search on depth of learning. *PNAS Nexus, 4*(10), pgaf316. https://academic.oup.com/pnasnexus/article/4/10/pgaf316/8303888

Nückles, M., Wittwer, J., & Renkl, A. (2005). Information about a layperson's knowledge supports experts in giving effective and efficient online advice to laypersons. *Journal of Experimental Psychology: Applied, 11*(4), 219–236. https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:16393032&format=json&resultType=core

Park, Y., Tark, J., & Gong, T. (2026). *ExPerT: Personalizing LLM responses to users' domain expertise via query-wise semantic and keystroke behavioral cues* (arXiv:2607.01242). arXiv. https://arxiv.org/abs/2607.01242

Richland, L. E., & Zhao, H. (2026). Relational reasoning and educational applications. *Behavioral Sciences, 16*(2), 210. https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12938770/fullTextXML

Rozenblit, L., & Keil, F. (2002). The misunderstood limits of folk science: An illusion of explanatory depth. *Cognitive Science, 26*(5), 521–562. https://pmc.ncbi.nlm.nih.gov/articles/PMC3062901/

Salmerón, L., Cañas, J. J., Kintsch, W., & Fajardo, I. (2005). Reading strategies and hypertext comprehension. *Discourse Processes, 40*(3), 171–191. https://www.uv.es/lasalgon/papers/2005_DP.pdf

Schroeder, N. L., & Kucera, A. C. (2022). Refutation text facilitates learning: A meta-analysis of between-subjects experiments. *Educational Psychology Review, 34*(2), 957–987. https://pmc.ncbi.nlm.nih.gov/articles/PMC8784251

Shao, Z., Yuan, S., Gao, L., He, Y., Yang, D., & Chen, S. (2025). *Unlocking scientific concepts: How effective are LLM-generated analogies for student understanding and classroom practice?* (arXiv:2502.16895). arXiv. https://arxiv.org/abs/2502.16895

Swire-Thompson, B., DeGutis, J., & Lazer, D. (2020). Searching for the backfire effect: Measurement and design considerations. *Journal of Applied Research in Memory and Cognition, 9*(3), 286–299. https://pmc.ncbi.nlm.nih.gov/articles/PMC7462781

Toma, M. J., & Rahman, S. M. H. (2021). Analogy in secondary physics teaching-learning: Teachers' views and practices in Bangladesh. *Asia-Pacific Forum on Science Learning and Teaching, 20*(2), Article 1. https://www.eduhk.hk/apfslt/v20_issue2/rahman/page2.htm

Tullis, J. G., & Feder, B. (2022). The "curse of knowledge" when predicting others' knowledge. *Memory & Cognition*. https://pmc.ncbi.nlm.nih.gov/articles/PMC9794110/

University of California, Irvine. (2007, May 24). *"Teaching gap" exists among US and Asian math teachers, study says* [Press release]. EurekAlert! https://www.eurekalert.org/news-releases/743133

Van Loon, M. H., Dunlosky, J., Van Gog, T., Van Merriënboer, J. J. G., & De Bruin, A. B. H. (2015). Refutations in science texts lead to hypercorrection of misconceptions held with high confidence. *Contemporary Educational Psychology, 42*, 39–48. https://research-portal.uu.nl/en/publications/refutations-in-science-texts-lead-to-hypercorrection-of-misconcep/

Vasil, N., & Lombrozo, T. (2022). Explanations and causal judgments are differentially sensitive to covariation and mechanism information. *Frontiers in Psychology, 13*. https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2022.911177/full

Väth et al. (2024). *Replicating the "seductive allure of neuroscience explanations" effect* [Summary of a Royal Society Open Science article]. explore.psychsafety.com. https://explore.psychsafety.com/n/vath-et-al-2024.md

Watson, A. (2025, June 29). *One size doesn't fit all: Teaching experts and novices*. Learning & the Brain. https://www.learningandthebrain.com/blog/one-size-doesnt-fit-all-teaching-experts-and-novices/

Weisberg, D. S., Keil, F. C., Goodstein, J., Rawson, E., & Gray, J. R. (2008). The seductive allure of neuroscience explanations. *Journal of Cognitive Neuroscience, 20*(3), 470–477. https://pmc.ncbi.nlm.nih.gov/articles/PMC2778755

Yen, P. H., & Leasure, A. R. (2019). Use and effectiveness of the teach-back method in patient education and health outcomes. *Federal Practitioner, 36*(6), 284–289. https://pmc.ncbi.nlm.nih.gov/articles/PMC6590951

Zaske, S. (2020, March 19). *Seductive details inhibit learning*. WSU News, Washington State University. https://news.wsu.edu/press-release/2020/03/19/seductive-details-inhibit-learning

Zemla, J. C., Sloman, S. A., Bechlivanidis, C., & Lagnado, D. A. (2023). Not so simple! Causal mechanisms increase preference for complex explanations. *Cognition, 239*, 105551. https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:37478697%20AND%20SRC:MED&format=json&resultType=core

Zhang, T., Yang, X. J., & Li, B. (2023). *May I ask a follow-up question? Understanding the benefits of conversations in neural network explainability* (arXiv:2309.13965). arXiv. https://arxiv.org/abs/2309.13965
