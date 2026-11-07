# Writing for neurodivergent readers: research findings

Research summary · Search date: 7 November 2026
Follows up on open question Q20 in `writing-for-human-cognition.md`.

For most rules, writing for neurodivergent readers means writing clearly for everyone. The studies found mostly show that changes which help dyslexic, autistic or ADHD readers also help other readers, but help them more. The specific risk for AI is different. When a user discloses a diagnosis, models change their content and format based on stereotypes, and some users find the result patronising. Neither change has been tested for whether readers understand more.

## 1. Adapt to what the user says they prefer, not to their diagnosis

Three 2025–2026 studies show the same pattern. None of them measured whether readers understood more.

- **Advice changes with disclosure (Wohn et al., CHI 2026).** The authors generated 345,000 responses from 6 models. When the user disclosed autism, most models applied four stereotypes: introverted, dangerous, obsessive, and aromantic. Most models then advised users to avoid socialising, new experiences, and relationships. Of the 11 autistic people interviewed, some found this supportive and others found it infantilising.
- **Tailoring relies on stereotypes (Höhn et al., SIGDIAL 2025).** The authors compared responses to personas who disclosed or masked a neurodivergent identity. Models tailored their responses using stereotypes, and some models' safety mechanisms refused service.
- **"Adapting" made answers longer (NDBench, preprint, April 2026).** The authors collected 576 responses from 2 models. When the system prompt told models to adapt for a neurodivergent user, the responses got longer, with more headings and more detailed steps. No human readers tested whether this helped.

Two more sources describe how this feels to readers. In a study of 20 adults with dyslexia, over-simplified text felt patronising (DFT-GEN, preprint, 2026). Those readers understood the concepts but needed more time to decode dense text. Separately, posts from autistic users describe models that agree too readily and so validate fixations or paranoia (Ma et al., 2026, 3,984 posts).

**What this means for the skill:** Rule 1.1 of `write-better` already follows this approach, because it puts the user's stated preference above the general rules. The skill has no rule against changing *content* because of a disclosed diagnosis. This research supports adding one.

## 2. Evidence for each existing rule

The `write-better` rules hold up. The evidence for most of them is small studies of one group, measured over a short time.

| Rule | Evidence | Verdict |
|---|---|---|
| **4.8 Say what you mean literally** | Overall, autistic participants scored lower on figurative language (meta-analysis of 41 studies, g = −0.57). When groups were matched on language ability, the gap became small and non-significant (Kalandadze et al., 2018). Autistic and non-autistic college students interpreted indirect requests equally well (Frost, 2022). Autistic adults did find irony hard (Deliens et al., 2018). | Keep. The gap tracks language ability more than autism. Irony and sarcasm are the clearest problem. |
| **4.9 Be specific** | Discomfort with uncertainty was linked to weaker understanding of implied meaning in autistic adults (Wilson & Bishop, 2022, registered report). No study tested vague words such as "soon" directly. | Keep. The support is indirect. |
| **4.1 Use common words** | For dyslexic readers, more frequent words led to faster reading and shorter words led to better understanding (Rello et al., 2013, n = 46). Replacing words automatically had no effect (n = 96). Showing a simple synonym next to the hard word worked better than replacing it. | Keep, with a qualification: explaining a word beside it can work better than swapping it out. |
| **4.7 Put the main verb early** | An eye-tracking study of 20 autistic adults reading Easy Read texts recommends fewer words before the main verb, and shorter words and sentences (Yaneva et al., 2015). | Keep. |
| **3.4 Live text, no dyslexia fonts or Bionic Reading** | Read-aloud tools improved comprehension for students with reading disabilities (meta-analysis, d = 0.35; Wood et al., 2018). Bionic Reading showed no reliable gain, and one test found lower comprehension. | Keep. |
| **3.2 / 3.3 Structure and condensing** | Ten interviewees with attention difficulties all said a restructured LLM response was easier to read (Lee et al., C&C 2026). This is self-report only. The earlier review found that feeling something is easier does not show better understanding. | Keep. Do not treat "easier to read" as proof. |

## 3. A rule the skill does not have yet: bold the key ideas

Bolding the main ideas improved comprehension for dyslexic readers in an eye-tracking study of 62 people, 31 of them dyslexic (Rello et al., 2014). A meta-analysis found that highlighting chosen by the author improved memory and comprehension in general student groups (effect size 0.44). One limit applies: the earlier review (Q07) found that emphasis can lower recall of the parts that are not emphasised. If the skill adds this rule, it should limit bolding to a few key ideas.

## 4. What the evidence does not show

- **No study tests AI output formatting with neurodivergent readers and measures comprehension.** Some studies record what readers say they prefer (Lee et al., 2026). Others examine what models produce (NDBench, Wohn et al.).
- **Preference and performance differ.** In Rello's work, only about half of participants could say which text settings made them read faster. Among autistic adults, individual characteristics explained little of the variation in communication preferences (Merken et al., 2026). So a fixed "neurodivergent style" is unlikely to fit everyone.
- **Easy Read lacks evidence that it works.** A 2026 systematic review of 29 studies found that readers valued Easy Read health information, but the studies were mostly low quality and gave little evidence that it helped.
- **ADHD has the thinnest evidence.** No controlled study of text segmentation, length or signalling with adult ADHD readers was found.

One more point applies to the format, not the wording: autistic adults consistently preferred written over spoken communication (Howard & Sedgewick, 2021, n = 245; Merken et al., 2026, n = 147).

## Sources

- Wohn et al. (CHI 2026), [Stereotypes in AI advice for autistic users](https://arxiv.org/abs/2601.12690)
- Höhn, Philippy & André (SIGDIAL 2025), [Autism self-disclosures and LLM-powered robots](https://aclanthology.org/2025.sigdial-1.40)
- Gupta & Buryi (preprint 2026), [NDBench](https://arxiv.org/pdf/2605.00113)
- Ma et al. (2026), ["I use ChatGPT to humanize my words"](https://arxiv.org/abs/2601.17946)
- Carik et al. (2025), [LLMs through a neurodivergent lens](https://arxiv.org/abs/2410.06336)
- Lee et al. (C&C 2026), [Too Long to Read?](https://dl.acm.org/doi/10.1145/3803784.3816862)
- DFT-GEN (preprint 2026), [Fidelity-preserving dyslexia-friendly texts](https://arxiv.org/pdf/2608.13583)
- Kalandadze et al. (2018), [Figurative language in autism meta-analysis](https://discovery.ucl.ac.uk/id/eprint/10045348/)
- Frost (2022), [Indirect requests by autistic adults](https://researchautism.org/research-item/interpretation-of-indirect-requests-by-autistic-adults/); Deliens et al. (2018), [Indirect requests vs irony](https://bibi.ulb.ac.be/papers/Deliens2018.pdf)
- Wilson & Bishop (2022), [Preference for certainty in conversation](https://peerj.com/articles/13110)
- Rello et al. (2014), [Keyword highlighting and dyslexia](https://aclanthology.org/W14-1204); Rello et al. (2013), [Simplify or help?](https://a11y-paradise.onrender.com/reviews/69c080e9fbe1707d6a0f3216)
- Highlighting meta-analysis, [Educational Psychology Review](https://link.springer.com/10.1007/s10648-021-09654-1)
- Yaneva, Temnikova & Mitkov (2015), [Accessible texts for autism](https://unpaywall.org/10.1145%2F2700648.2809852)
- Wood et al. (2018), [Text-to-speech meta-analysis](https://vivo.weill.cornell.edu/display/pubid28112580)
- [Bionic Reading coverage (Quartz)](https://qz.com/2182666/does-bionic-reading-work-typographers-and-scientists-weigh-in)
- [Easy Read systematic review (2026)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12893875/)
- Howard & Sedgewick (2021) and Merken et al. (2026), [communication preferences](https://bohrium.dp.tech/paper/arxiv/812115908938956801)
- Xu et al. (2025), [Human–AI interaction design for neurodivergent users (scoping review)](https://www.tandfonline.com/doi/full/10.1080/17483107.2025.2579822)
