# Neurodivergent diagnoses and how an AI agent should communicate: research findings

Research summary · Search date: 9 November 2026
Board: `.research/neurodivergent-communication/` (19 questions; claims marked verified or unverified against their sources).
Related: `writing-for-neurodivergent-readers.md` (7 November 2026).

The question started from the diagnoses in DSM-5-TR and ICD-11, then asked how an AI agent's text, explanations, questions and teaching should adapt for neurodivergent users. The aim was to find changes for the skills in this repository.

**Most communication advice for neurodivergent readers rests on guidance and user reports, not on controlled tests.** The best-supported findings are these:
- People need different things, so the user should set the format; the agent should not infer needs from a diagnosis label.
- Literal, specific wording helps, mainly for readers with weaker language skills.
- Dyslexia fonts do not help, while text-to-speech gives a modest gain.
- Supportive, specific questions work better than open ones for autistic adults.

## 1. Which diagnoses count

DSM-5-TR and ICD-11 mostly agree on the neurodevelopmental group. The few differences matter little for communication.

| Group | DSM-5-TR (APA, n.d.) | ICD-11 6A00–6A0Z (Find-A-Code, 2026a) |
|---|---|---|
| Intellectual | Intellectual disability | Disorders of intellectual development |
| Communication and language | Speech sound, language, stuttering, social (pragmatic) communication disorder | Developmental speech or language disorders. Social (pragmatic) communication disorder is not separate: it is the qualifier 6A01.22, which is not used when autism explains the difficulty better (Find-A-Code, 2026b) |
| Autism | Autism spectrum disorder | Autism spectrum disorder |
| ADHD | ADHD | ADHD |
| Learning | Specific learning disorder | Developmental learning disorder |
| Motor | Developmental coordination disorder, stereotypic movement disorder, **tic disorders including Tourette's** | Developmental motor coordination disorder, stereotyped movement disorder. **Tics are classed as neurological (8A05.0)** but cross-listed in the chapter (Tebartz van Elst et al., 2025) |

Two limits on these sources:
- The APA list comes from its patient pages, not the DSM-5-TR text, so the specifiers and the "other specified" categories are not confirmed.
- The ICD-11 list comes from a coding-site copy, because the WHO browser could not be read.

**"Neurodivergent" has no medical definition** (NNLM, n.d.), so which conditions it covers is contested:
- **Core:** the conditions most often named are ADHD, autism, developmental coordination disorder and dyslexia (Doyle, 2020).
- **Extended by some authors:** Tourette syndrome, dyscalculia, dysgraphia, acquired brain injury, and mental health conditions such as depression and anxiety (Doyle, 2020).
- **Walker's definition:** a mind that diverges from "dominant societal standards of 'normal'". It includes divergence produced by experience as well as innate divergence (Walker, 2014).
- **Diagnosis not required:** Scotland's National Autism Implementation Team says neurodivergent people "do not necessarily have a neurodevelopmental disorder" (Shah et al., 2022).

## 2. Communication practices, by strength of evidence

| Practice | Evidence | Strength |
|---|---|---|
| **Let the user set communication preferences; do not tailor content to a disclosed diagnosis** | Six LLMs told a user was autistic "disproportionately recommended avoiding" social events, new experiences and relationships. Autistic interviewees were split between finding this affirming and infantilizing (Wohn et al., 2026). One prototype uses a profile the user sets instead, with dimensions such as literalness, verbosity tolerance and pacing (Muniganti et al., 2026). That prototype has not been tested with users. | Moderate: a large audit, but few interviews |
| **Literal, specific wording without idioms** | The AASPIRE guidelines, co-developed with autistic users, say to be "specific and precise in language use; avoid colloquialisms, idioms, and ambiguity" (Raymaker et al., 2019). A meta-analysis of 41 studies found autistic people understand figurative language less well, but **the gap was small and not significant once groups were matched on language ability** (Kalandadze et al., 2018). Literal wording therefore helps by language skill, not by diagnosis. | Moderate |
| **Short, but still precise** | AASPIRE says to make content "as short as possible without sacrificing precision" (Raymaker et al., 2019). Neurodivergent users report that LLM output is "very neurotypical" and needs many rounds of re-prompting (Carik et al., 2024). In an autoethnography, eight neurodivergent heavy users of AI asked for concise answers, and one wrote "GPT just loves essays" (Glazko et al., 2025). | Weak to moderate. The Glazko quotes were not checked against the verbatim page text. |
| **Supportive, specific questions instead of open ones** | Autistic adults recall as much as non-autistic adults when questioning is supportive (Norris & Maras, 2022). Splitting interview questions into parts and giving them in writing helped autistic candidates (Maras et al., 2020). | Moderate for autistic adults. The Maras result comes from a summary page. Nothing was found for other groups. |
| Some users find questions themselves hard | One autistic user dropped a prompt "because my brain does not like it when people ask me questions" (Carik et al., 2024). | Anecdote |
| **Dyslexia: no special fonts. Offer text-to-speech. Left-aligned text** | A dyslexia-friendly letterform gave no benefit to 64 dyslexic and 64 non-dyslexic children. Wider letter spacing on its own slowed reading (Galliussi et al., 2020). Text-to-speech gave a small-to-moderate comprehension gain to students with reading disabilities (Wood et al., 2018). Dyslexia Scotland (2025) recommends left alignment and 1.5 line spacing, and says dyslexia fonts lack consistent evidence. | Moderate for fonts and text-to-speech. Layout advice is guidance only. |
| ADHD: break long reading into stages | Adults with ADHD understood a long digital text less well than controls. With stage-by-stage reading instructions, comprehension "was comparable across both groups" (Brann & Sidi, 2024). | One study (n = 210), read as an abstract |
| ADHD: headings, chunking, summaries | Three searches found **no controlled study**. | Not found |
| Easy Read and simplified text for intellectual disability | A 2026 review of 29 studies calls the evidence base "underdeveloped and largely… low-quality" (Wilson et al., 2026). In a trial with 60 adults, neither linguistic simplification nor mediation improved comprehension (Buell et al., 2020). | Moderate evidence that the benefit is unproven |
| Say when the answer may be wrong | Glazko et al. (2025) report users wanting the AI to flag uncertainty, and they recommend built-in validation. | Weak; quotes not checked |
| Teaching: explicit instruction and breaking tasks into steps | A UK evidence review reports these as effective for autistic pupils, but says the evidence base for systematic programmes "is still limited" (Antalek et al., 2025). | Weak; quotes not checked (PDF unreadable). Only autistic learners are covered. |

## 3. Where sources disagree

- **Double empathy problem:** the idea that miscommunication between autistic and non-autistic people runs both ways, not from an autistic deficit.
  - **2020 study:** information degraded only in mixed autistic/non-autistic chains (Crompton et al., 2020; n = 72).
  - **2025 registered replication:** it found "no difference in information transfer" between single-neurotype and mixed chains (Crompton et al., 2025; N = 311). Rapport was still lower in mixed chains, and disclosing a diagnosis improved rapport.
  - **Critique:** one paper calls the concept poorly defined (Livingston et al., 2025); its text could not be checked.
  - For an agent, the firmer result concerns rapport and tone, not how much information gets across.
- **Identity-first vs person-first wording:** 87% of autistic adults in a US sample preferred identity-first language (Taboas et al., 2022). A Dutch study is reported to find the opposite, but it could not be read, and the US quote was not checked either.
- **Conflicting needs across groups,** such as full detail against brevity: **not found**. No source says how to resolve this. The W3C cognitive accessibility note recommends personalization and a "short summary for long pieces of content" (Seeman-Horwitz et al., 2021). That suggests letting the user choose rather than picking one default.

## 4. What this means for the skills

The current `write-better` already has several of these rules: no dyslexia fonts, literal wording, and no tailoring content to a disclosed diagnosis. The evidence above supports them. The findings that could add something are these:
- Literal wording matters by language skill, not by diagnosis.
- Supportive, specific questions help autistic adults. This is relevant to `ask-better`.
- Staged instructions for long reading help ADHD readers. This is relevant to `teach-better`.
- No evidence was found for chunking or summaries aimed at ADHD readers.

## 5. Gaps and open items

- **Open:** Q-15, whether these adaptations help or hurt other readers. It is low priority and was not researched.
- **Thin evidence:** the ADHD, dyslexia-layout and teaching rows rest on one or two sources each.
- **Blocked sources that could change the answer:**
  - the Morsanyi idiom meta-analysis
  - the British Dyslexia Association style guide
  - controlled dyslexia line-length studies by Rello et al.
  - autistic-led organisations' guidance
  - the full text of Livingston et al. (2025)

## References

American Psychiatric Association. (n.d.). *Neurodevelopmental disorders*. Psychiatry.org. https://www.psychiatry.org/patients-families/neurodevelopment-disorders

Antalek, C., Castro-Kemp, S., Dixon, F., & Romualdez, A. M. (2025). *Identifying and supporting the needs of autistic children and young people: A rapid evidence review*. UK Department for Education. https://assets.publishing.service.gov.uk/media/68d660f58c739d679fb1de1f/Identifying_and_supporting_the_needs_of_autistic_children_and_young_people_a_rapid_evidence_review.pdf

Brann, A., & Sidi, Y. (2024). Metacognitive scaffolding for digital reading and mind-wandering in adults with and without ADHD. *Learning and Instruction, 95*, 102051. https://cris.openu.ac.il/iw/publications/metacognitive-scaffolding-for-digital-reading-and-mind-wandering-/

Buell, S., Langdon, P., Pounds, G., & Bunning, K. (2020). An open randomized controlled trial of the effects of linguistic simplification and mediation on the comprehension of "easy read" text by people with intellectual disabilities. *Journal of Applied Research in Intellectual Disabilities, 32*(2), 219–231. https://ueaeprints.uea.ac.uk/id/eprint/72356/

Carik, B., Ping, K., Ding, X., & Rho, E. H. (2024). *Exploring large language models through a neurodivergent lens: Use, challenges, community-driven workarounds, and concerns*. arXiv. https://arxiv.org/html/2410.06336v1

Crompton, C. J., Foster, S. J., Wilks, C. E. H., Dodd, M., Efthimiou, T. N., Ropar, D., Sasson, N. J., Lages, M., & Fletcher-Watson, S. (2025). Information transfer within and between autistic and non-autistic people. *Nature Human Behaviour, 9*(7), 1488–1500. https://pmc.ncbi.nlm.nih.gov/articles/PMC12283400/

Crompton, C. J., Ropar, D., Evans-Williams, C. V. M., Flynn, E. G., & Fletcher-Watson, S. (2020). Autistic peer-to-peer information transfer is highly effective. *Autism, 24*(7), 1704–1712. https://www.research.ed.ac.uk/en/publications/autistic-peer-to-peer-information-transfer-is-highly-effective/

Doyle, N. (2020). Neurodiversity at work: A biopsychosocial model and the impact on working adults. *British Medical Bulletin, 135*(1), 108–125. https://pmc.ncbi.nlm.nih.gov/articles/PMC7732033

Dyslexia Scotland. (2025, September 12). *Dyslexia-friendly typed formats*. https://dyslexiascotland.org.uk/dyslexia-friendly-typed-formats

Find-A-Code. (2026a). *Neurodevelopmental disorders (6A00-6A0Z)* [Reproduction of WHO ICD-11 MMS]. https://www.findacode.com/icd-11/block-1516623224.html

Find-A-Code. (2026b). *6A01.22 Developmental language disorder with impairment of mainly pragmatic language* [Reproduction of WHO ICD-11 MMS]. https://findacode.com/icd-11/code-854708918.html

Galliussi, J., Perondi, L., Chia, G., Gerbino, W., & Bernardis, P. (2020). Inter-letter spacing, inter-word spacing, and font with dyslexia-friendly features: Testing text readability in people with and without dyslexia. *Annals of Dyslexia, 70*(1), 141–152. https://pmc.ncbi.nlm.nih.gov/articles/PMC7188700

Glazko, K., Cha, J., Lewis, A., Kosa, B., Wimer, B. L., Zheng, A., Zheng, Y., & Mankoff, J. (2025). Autoethnographic insights from neurodivergent GAI "power users". In *Proceedings of the SIGCHI Conference on Human Factors in Computing Systems (CHI 2025)*. https://pmc.ncbi.nlm.nih.gov/articles/PMC12645485/

Kalandadze, T., Norbury, C., Nærland, T., & Næss, K.-A. B. (2018). Figurative language comprehension in individuals with autism spectrum disorder: A meta-analytic review. *Autism, 22*(2), 99–117. https://pmc.ncbi.nlm.nih.gov/articles/PMC5843023/

Livingston, L. A., Hargitai, L. D., & Shah, P. (2025). The double empathy problem: A derivation chain analysis and cautionary note. *Psychological Review, 132*(3), 744–757. https://doi.org/10.1037/rev0000468

Maras, K., Norris, J., Nicholson, J., Heasman, B., Remington, A., & Crane, L. (2020). *Ameliorating the disadvantage for autistic job seekers: An initial evaluation of adapted employment interview questions* [Summary page]. Centre for Research in Autism and Education. https://crae.ioe.ac.uk/ameliorating-the-disadvantage-for-autistic-job-seekers

Muniganti, V., Doctor, F., Anisi, H., & Bourazeri, A. (2026). *ATTUNE* [Conference paper, IEEE SMC 2026, in press]. University of Essex Research Repository. https://repository.essex.ac.uk/43775/

Network of the National Library of Medicine. (n.d.). *Neurodiversity*. NNLM. https://www.nnlm.gov/reading-club/topic/331

Norris, J. E., & Maras, K. (2022). Supporting autistic adults' episodic memory recall in interviews: The role of executive functions, theory of mind, and language abilities. *Autism, 26*(2), 513–524. https://pmc.ncbi.nlm.nih.gov/articles/PMC8814938

Raymaker, D. M., Kapp, S. K., McDonald, K. E., Weiner, M., Ashkenazy, E., & Nicolaidis, C. (2019). Development of the AASPIRE web accessibility guidelines for autistic web users. *Autism in Adulthood, 1*(2), 146–157. https://pmc.ncbi.nlm.nih.gov/articles/PMC6485264

Seeman-Horwitz, L., Bradley Montgomery, R., Lee, S., & Ran, R. (Eds.). (2021, April 29). *Making content usable for people with cognitive and learning disabilities*. W3C Working Group Note. https://www.w3.org/TR/coga-usable/

Shah, P. J., Boilson, M., Rutherford, M., Prior, S., Johnston, L., Maciver, D., & Forsyth, K. (2022). Neurodevelopmental disorders and neurodiversity: Definition of terms from Scotland's National Autism Implementation Team. *The British Journal of Psychiatry, 221*(3), 577–579. https://www.cambridge.org/core/product/C6582CFF0E5E00F2F0F38F294A6659D1/core-reader

Taboas, A., Doepke, K., & Zimmerman, C. (2022). Preferences for identity-first versus person-first language in a US sample of autism stakeholders. *Autism*. https://doi.org/10.1177/13623613221130845

Tebartz van Elst, L., Riedel, A., & Biscaldi-Schäfer, M. (2025). The reclassification of neurodevelopmental disorders in ICD-11. *Der Nervenarzt*. https://www.springermedizin.de/the-reclassification-of-neurodevelopmental-disorders-in-icd-11/51520996

Walker, N. (2014). *Neurodiversity: Some basic terms & definitions*. NEUROQUEER. https://neuroqueer.com/neurodiversity-terms-and-definitions/

Wilson, H., Irvine, K., Alexander, R. T., & Mengoni, S. E. (2026). Easy Read health information for people with intellectual disabilities: A systematic review of the evidence. *Journal of Applied Research in Intellectual Disabilities, 39*(1), e70195. https://pmc.ncbi.nlm.nih.gov/articles/PMC12893875/

Wohn, C., Çarık, B., Ding, X., Lee, S. W., Kim, Y.-H., & Rho, E. H. (2026). *"Are we writing an advice column for Spock here?" Understanding stereotypes in AI advice for autistic users*. arXiv. https://arxiv.org/abs/2601.12690

Wood, S. G., Moxley, J. H., Tighe, E. L., & Wagner, R. K. (2018). Does use of text-to-speech and related read-aloud tools improve reading comprehension for students with reading disabilities? A meta-analysis. *Journal of Learning Disabilities, 51*(1), 73–84. https://pmc.ncbi.nlm.nih.gov/articles/PMC5494021/
