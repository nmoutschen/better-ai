# Inclusivity: research findings

Research summary · Search date: 8 November 2026
Board: `.research/inclusivity/` (28 questions, every cited claim checked against its source).

The question was how the skills in this repository can make their outputs more inclusive. It had two passes. The first pass covered inclusive wording, accessibility standards, and bias in LLM output. The second pass covered adapting to each user, and inclusive features that help everyone (the "curb-cut effect").

Two findings matter most. First, **some alternatives built for a specific group help most readers**: visuals added to text, captions, and simpler text for readers new to a topic. But they help less, or get in the way, for readers who already know the topic. Second, **adapting to a user works when it follows what the user knows and what they state, and fails when it follows a guess about who they are**. Learning-style matching has little support, models guess demographics from stereotyped cues, and stored personalization raises sycophancy.

## 1. Features that help most readers, and their limits

| Feature | Evidence | Limit |
|---|---|---|
| Visuals added to text | Graphics improved reading comprehension, g = 0.39 across 39 experiments (Guo et al., 2020). Illustrations in science texts, g = 0.23 (Lei et al., 2025). | Decorative, irrelevant material lowered learning when it came as audio, text, or text with a picture (Sundararajan & Adesope, 2020, as reported by Désiron & Schneider, 2024). |
| Captions | Over 100 studies show captions improve comprehension, attention and memory, including for hearing adults and people watching in another language (Gernsbacher, 2015). | Automatic captions with errors interfere. |
| Simpler text | Simpler summaries gave the best reading experience to readers new to a topic (August et al., 2024). Fluency gains were larger for slower readers (Gruteke Klein et al., 2025). | For general adult readers the gain is small: reading was easier for 42%, but comprehension improved for only 2%. Readers who knew the topic skipped details such as study limitations in overly plain summaries. |
| Plain language for experts | Experts also want short text they can scan (Loranger, 2017). | Usability article; no sample size reported. |
| Identical text in two channels | On-screen text identical to the narration impaired recall and transfer, and learners preferred it anyway (Yue et al., 2013). | Slightly reworded text did better than identical text. |
| Dyslexia font | No gain in reading rate or accuracy, even for dyslexic pupils (Wery & Diliberto, 2016). | Small study. |
| Universal Design for Learning | Contested. A review of 13 studies found mixed results and loose links between the guidelines and the interventions (Ok et al., 2016). A critic says UDL lacks evidence that it raises learning (Boysen, 2021, via Ashman, 2021). | Positive reviews and a 2023 meta-analysis could not be read. |

Microsoft's inclusive design method holds that "solving for one" extends to many, but the guide gives no outcome data (Microsoft Design, 2025). Access needs can also conflict, so one feature can help some people and constrain others (Tang & Piper, 2026).

**What this means for the skills:** offering a visual with the text, and a simpler version for readers new to a topic, are supported as defaults. Both should leave out decoration, avoid repeating the prose word for word, and keep limitations. Readers who know the topic should be able to skip them.

## 2. Adapting to the user

### 2.1. Adapt to knowledge, not to learning style

- Matching instruction to a learner's stated style: only 26% of outcome measures in a 2024 meta-analysis showed the pattern the theory needs. The authors call any benefit "far from conclusive" (Clinton-Lisell & Litzinger, 2024). Willingham et al. (2015) state that scientific support for learning-style theories is lacking.
- Learners misjudge what helps them. They rate blocked study above interleaved study, although interleaving gives better memory later (Krasnoff & Overkott, 2022).
- Support that helps beginners can lose its value or hurt more experienced learners. This is the expertise reversal effect (Kalyuga et al., 2012). Reducing worked examples as each student progressed beat reducing them on a fixed schedule, in two experiments (Salden et al., 2010).
- A 2025 meta-analysis of 60 experiments, seen only through a secondary summary, reports that giving beginners support matters more than withholding it from experts (Tetzlaff et al., 2025, via Tips for Teachers, 2026). This suggests including support when the reader's level is unknown.
- For LLMs, only satisfaction has been measured. Responses adapted to the expertise inferred from each query raised satisfaction from 3.71 to 4.36 out of 5, with 40 participants (Park et al., 2026).

**What this means for the skills:** `teach-better` already adapts to performance and avoids personalizing to interests. The evidence supports that approach. It also supports adapting detail to what the reader knows, and not to a stated style.

### 2.2. Use what the user states, not what you infer

- An adaptive interface helped only when its predictions were accurate (Gajos et al., 2008).
- LLMs infer users' demographics from stereotyped cues. For some groups the inference persists after the user states a different identity (Neplenbroek et al., 2025).
- In a benchmark of 21 models, 29% of attempts to personalize without asking the user did worse than a generic answer (Li et al., 2026).
- Responses differ by how the user writes. ChatGPT replies to non-standard English varieties were 19% worse for stereotyping and 15% worse for condescension (Fleisig et al., 2024). Answers to African American English input were less accurate (Zhou et al., 2025). Undesirable behaviour was more frequent for users with lower English proficiency, less education, or from outside the US (Poole-Dayan et al., 2024).
- Microsoft's human-AI guidelines recommend letting users set how the system behaves, and limiting disruptive changes when it adapts (Amershi et al., 2019).
- An accessibility working-group contributor warns that preference settings can reveal a disability (Wolberger, 2022). This is one person's view.

**What this means for the skills:** principle 2.3 already forbids adapting to a guessed trait. The evidence extends it: the way a user writes (dialect, spelling, fluency) says nothing about their ability. Offering choices about the output, such as "a diagram?" or "a shorter version?", avoids asking about the person. This is a design inference that no study has tested.

### 2.3. Stored personalization has costs

- User memory profiles gave the largest increase in agreement sycophancy, up to +45% for one model (Jain et al., 2026).
- Across 13 models, user profiles and retrieved memories worsened irrelevant personalization, preference narrowing and sycophancy (Wang et al., 2026).
- In 80 ChatGPT users' memories, 96% were created by the system rather than the user, and 28% held personal data as defined by GDPR (Dash et al., 2026).

**What this means for the skills:** when a skill records preferences, it should record ones the user stated, about the output, and not inferred traits.

## 3. Inclusive wording and accessibility (first pass)

- **Wording.** Google, Microsoft, GOV.UK and a summary of APA 7 agree on several points: gender-neutral wording, singular "they" or rewording for unknown people, replacing ableist idioms, and varying names and cultures in examples (Google, n.d.; Microsoft, n.d.; Government Digital Service, n.d.; MGH Institute of Health Professions, n.d.). They conflict on disability wording. Microsoft and Google default to person-first wording, GOV.UK requires "disabled people", and APA allows either. The NCDJ guide and Apple's style guide say to ask the people concerned (National Center on Disability and Journalism, 2021; Apple, 2026). Singular "they" was read as fast as "he" or "she" for generic people, and slower when the person's gender was known (Foertsch & Gernsbacher, 1997).
- **Other languages.** In French and German, inclusive writing is disputed by official bodies (Rat für deutsche Rechtschreibung, 2021; Godard & Walsh, 2017; Landot, 2017).
- **Accessibility of generated pages.** WCAG 2.2 requires the following: text alternatives, structure that software can read, 4.5:1 text contrast, colour never the only signal, descriptive headings, a declared page language, and a way to pause motion (W3C, 2024). For charts, it advises giving the data as a table where practical (W3C Web Accessibility Initiative, 2026). Blind and sighted readers value different parts of a chart description (Lundgard & Satyanarayan, 2021).
- **Terminal output.** Box-drawing decoration, spinners and redrawn screens work poorly with screen readers (Hecht & Feller, 2025; Anthropic, 2026; Sampath et al., 2021).
- **Language of sources.** AI systems that answer from retrieved documents cite English or same-language sources more often, even over more relevant documents (Ki et al., 2025; Sharma et al., 2024). AI search under-cited domestic outlets in Latin America (Kerche et al., 2026). Retrieval in several languages beat retrieval in one (Ranaldi et al., 2025).
- **Instructions to debias.** Contested. Prompts reduced stereotyped answers on benchmarks (Kamruzzaman & Kim, 2024), and scoring the responses themselves favoured prompting over retraining (Xu et al., 2025). But the gains may come from evasive answers (Yang et al., 2025), self-correction can turn right answers wrong (Liu et al., 2024), and diversity tuning made Gemini "way more cautious than we intended" (Raghavan, 2024).

## 4. What the evidence does not show

- No test of layered or summary-first text.
- No evidence that alt text, transcripts or summaries help readers without disabilities.
- No controlled comparison, for AI assistants, of the user choosing settings versus the system adapting.
- No study of how burdensome preference questions are.
- No test of inclusivity instructions on long free-form text.
- No study of which accommodations carry over to everyone.
- Several key papers were blocked: Kalyuga et al. (2003), Pashler et al. (2008), and the 2023 UDL meta-analysis. The Tetzlaff and seductive-details meta-analyses are cited through other sources.
- Most AI personalization sources are 2026 preprints.

## Sources

- Amershi, Vorvoreanu & Horvitz (2019), [Guidelines for human-AI interaction design](https://www.microsoft.com/en-us/research/blog/guidelines-for-human-ai-interaction-design)
- Anthropic (2026), [Use Claude Code CLI with a screen reader](https://support.claude.com/en/articles/15924927-use-claude-code-cli-with-a-screen-reader)
- Apple (2026), [Writing about disability](https://support.apple.com/en-by/guide/applestyleguide/apd49cbb2b06/web)
- Ashman (2021), [UDL is the new learning styles](https://fillingthepail.substack.com/p/universal-design-for-learning-udl) (summarizes Boysen, 2021)
- August, Lo, Smith & Reinecke (CHI 2024), [Know your audience](https://arxiv.org/abs/2403.04979)
- Clinton-Lisell & Litzinger (2024), [Learning styles matching meta-analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC11270031/)
- Dash et al. (2026), [The algorithmic self-portrait](https://arxiv.org/abs/2602.01450)
- Désiron & Schneider (2024), [Information relevance and colorfulness in multimedia learning](https://frontiersin.org/articles/10.3389/fpsyg.2024.1393113/full)
- Fleisig et al. (2024), [Linguistic bias in ChatGPT](https://arxiv.org/abs/2406.08818)
- Foertsch & Gernsbacher (1997), [Singular they](https://pmc.ncbi.nlm.nih.gov/articles/PMC4293036)
- Gajos et al. (CHI 2008), [Predictability and accuracy in adaptive user interfaces](https://www.microsoft.com/en-us/research/?p=145411)
- Gernsbacher (2015), [Video captions benefit everyone](https://pmc.ncbi.nlm.nih.gov/articles/PMC5214590/)
- Godard & Walsh (2017), [Académie française and inclusive writing](https://theconversation.com/inclusivity-putting-french-language-in-mortal-danger-claims-lacademie-francaise-87408)
- Google (n.d.), [Write inclusive documentation](https://developers.google.com/style/inclusive-documentation)
- Government Digital Service (n.d.), [GOV.UK A to Z style guide](https://www.gov.uk/guidance/style-guide/a-to-z-of-gov-uk-style)
- Gruteke Klein et al. (2025), [Text simplification in L1 English readers](https://tmalsburg.github.io/ComprehensionWorkshop/abstracts/GrutekeKleinEtAl2025)
- Guo et al. (2020), [Graphics and reading comprehension meta-analysis](https://experts.boisestate.edu/en/publications/do-you-get-the-picture-a-meta-analysis-of-the-effect-of-graphics--3/)
- Hecht & Feller (2025), [Building a more accessible GitHub CLI](https://github.blog/engineering/user-experience/building-a-more-accessible-github-cli/)
- Jain et al. (2026), [Interaction context often increases sycophancy](https://arxiv.org/abs/2509.12517)
- Kalyuga, Rikers & Paas (2012), [Expertise reversal effects review](https://repub.eur.nl/pub/74301)
- Kamruzzaman & Kim (2024), [Prompting techniques for reducing social bias](https://arxiv.org/abs/2404.17218)
- Kerche et al. (NeurIPS 2026), [News variety for users in Latin America](https://neurips.cc/virtual/2026/170593)
- Ki et al. (2025), [Linguistic nepotism in multilingual RAG](https://arxiv.org/abs/2509.13930)
- Krasnoff & Overkott (2022), [Overestimating blocked learning](https://pmc.ncbi.nlm.nih.gov/articles/PMC10482805/)
- Landot (2017), [Circulaire sur l'écriture inclusive](https://blog.landot-avocats.net/2017/11/22/une-circulaire-pour-la-feminisation-des-titres-mais-contre-lecriture-inclusive/)
- Lei et al. (2025), [Illustrations in science texts meta-analysis](https://pure.ecnu.edu.cn/en/publications/effects-of-adding-illustrations-to-texts-on-students-science-achi/)
- Li et al. (2026), [PrefDisco](https://arxiv.org/abs/2510.00177)
- Liu, Xie & Zhang (2024), [Social bias in open-ended settings](https://arxiv.org/abs/2412.06134)
- Loranger (2017), [Plain language is for everyone, even experts](https://www.nngroup.com/articles/plain-language-experts/)
- Lundgard & Satyanarayan (2021), [Accessible visualization via natural language descriptions](https://arxiv.org/abs/2110.04406v1)
- MGH Institute of Health Professions (n.d.), [Bias-free language, APA 7](https://libguides.massgeneral.org/APA7/biasfree-language)
- Microsoft (n.d.), [Bias-free communication](https://learn.microsoft.com/en-us/style-guide/bias-free-communication)
- Microsoft Design (2025), [Inclusive 101](https://inclusive.microsoft.design/articles/inclusive-101-guidebook)
- National Center on Disability and Journalism (2021), [Disability language style guide](http://cronkite.asu.edu/ncdj/disability-language-style-guide)
- Neplenbroek, Bisazza & Fernández (EMNLP 2025), [How stereotypes shape LLM implicit personalization](https://arxiv.org/abs/2505.16467)
- Ok, Rao, Bryant & McDougall (2016), [UDL in pre-K to grade 12: systematic review](https://meadowscenter.org/library/universal-design-for-learning-in-pre-k-to-grade-12-classrooms-a-systematic-review-of-research/)
- Park, Tark & Gong (ACL 2026), [ExPerT](https://arxiv.org/abs/2607.01242)
- Poole-Dayan, Roy & Kabbara (2024), [LLM targeted underperformance](https://arxiv.org/abs/2406.17737)
- Raghavan (2024), [Gemini image generation got it wrong](https://blog.google/products/gemini/gemini-image-generation-issue/)
- Ranaldi, Haddow & Birch (2025), [Multilingual RAG](https://arxiv.org/html/2504.03616v2)
- Rat für deutsche Rechtschreibung (2021), [Geschlechtergerechte Schreibung](https://www.rechtschreibrat.com/geschlechtergerechte-schreibung-empfehlungen-vom-26-03-2021/)
- Salden et al. (2010), [Expertise reversal and worked examples](https://link.springer.com/doi/10.1007/s11251-009-9107-8)
- Sampath, Merrick & Macvean (CHI 2021), [Accessibility of command line interfaces](https://research.google/pubs/pub49865)
- Sharma, Murray & Xiao (2024), [Faux polyglot](https://arxiv.org/abs/2407.05502)
- Tang & Piper (2026), [Designing for collective access](https://arxiv.org/abs/2605.10085)
- Tips for Teachers (2026), [Research Bite #51](https://tipsforteachers.substack.com/p/research-bite-51-a-cornerstone-of) (summarizes Tetzlaff et al., 2025)
- W3C (2024), [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- W3C Web Accessibility Initiative (2026), [Understanding SC 1.1.1: Non-text content](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html)
- Wang et al. (2026), [Hidden costs of personalization](https://huggingface.co/papers/2608.28833)
- Wery & Diliberto (2016), [OpenDyslexic and reading](https://pmc.ncbi.nlm.nih.gov/articles/PMC5629233/)
- Willingham, Hughes & Dobolyi (2015), [The scientific status of learning styles theories](https://pure.psu.edu/en/publications/the-scientific-status-of-learning-styles-theories)
- Wolberger (2022), [APA position statement on permissions](https://lists.w3.org/Archives/Public/public-apa/2022Nov/0029.html)
- Xu et al. (ICLR 2026), [BiasFreeBench](https://arxiv.org/html/2510.00232v2)
- Yang et al. (2025), [Rethinking prompt-based debiasing](https://arxiv.org/abs/2503.09219)
- Yue, Bjork & Bjork (2013), [Reducing verbal redundancy in multimedia learning](https://eric.ed.gov/?id=EJ1007931)
- Zhou et al. (2025), [Disparities in LLM reasoning for African American English](https://arxiv.org/abs/2503.04099)
