# Linking abstract rules to concrete cases, for an AI agent that teaches one user

Research register · Search date: 10 November 2026

**Scope.** What evidence shows that linking an abstract rule, formula or symbol to concrete cases helps learners, including concreteness fading (concrete, then pictorial, then abstract). The report also asks whether an AI agent that teaches one user (the `teach-better` skill) should use it.

**Status.** 9 questions closed. 7 answered, 2 contested. No meta-analysis of concreteness fading exists. Controlled studies disagree, and many primary papers could not be read. No study tested an LLM tutor.

The best-supported point is not the fading sequence but the link. A design review found that failing to tell learners how the concrete and abstract forms connect was the most common flaw, and it went with null results (Suh et al., 2020). Teaching mathematics with concrete materials beat symbols alone, d = 0.37 overall but only 0.13 on transfer (Carbonneau et al., 2013). Fading from concrete to abstract gave the best transfer in one undergraduate study (Goldstone & Son, 2005). Later classroom studies found it no better than presenting both forms at once (Lichtenberger et al., 2024), or than introducing the concrete form briefly (Kokkonen et al., 2022, abstract only).

## 1. What the technique is

- Concreteness fading is "a three-step progression": concrete (enactive), pictorial (iconic), then abstract (symbolic), after Bruner (Volodin et al., 2025).
- School practice uses many names for the same sequence: CRA (concrete, representational, abstract), CSA, CPA, VRA, and two-stage variants (Suh et al., 2020).
- "Concrete" has several dimensions: physicality, perceptual richness, familiarity and narrative context. So many continua exist (Suh et al., 2020).
- All implementations in the review presented the forms one after the other, never at the same time. Most used three stages, within one lesson or across many (Suh et al., 2020).

## 2. Evidence, with how strong it is

### 2.1. Concrete materials against symbols alone

**Evidence: one meta-analysis, in mathematics.**

- Across 55 studies from kindergarten to college (N = 7,237), teaching with concrete manipulatives beat abstract symbols alone, d = 0.37 (Carbonneau et al., 2013).
- By outcome: retention 0.59, problem solving 0.46, transfer 0.13 (Carbonneau et al., 2013).
- Overall, high guidance gave larger effects than low guidance. For transfer the pattern reversed: low guidance, and perceptually rich materials, did better (Carbonneau et al., 2013).

### 2.2. Fading against other sequences

**Evidence: contested.**

- With 84 undergraduates, fading from a concrete to an idealized simulation gave better transfer than concrete only, idealized only, or concrete introduced later (Goldstone & Son, 2005).
- With 187 high school students, fading and presenting both forms at once were "statistically equivalent" (Lichtenberger et al., 2024). The authors say support for fading comes mainly from mathematics, while physics results are equivocal.
- With 70 high school physics students, full three-step fading and brief introduction of the concrete form were equally effective (Kokkonen et al., 2022, abstract only).
- Two mathematics studies found fading advantages of d = 0.83 and 0.76 on immediate tests against other sequences (McNeil & Fyfe, 2012; Fyfe et al., 2015, both as reported by Lichtenberger et al., 2024). The originals could not be read.
- **Delayed tests.** Almost none. One doctoral thesis found that an immediate fading advantage shrank after two weeks: the concrete-only group improved and the fading group stayed stable (Cofone, 2020).

### 2.3. Too concrete

**Evidence: several studies, different ages.**

- More contextualized, concrete materials gave poorer transfer, in undergraduates and in middle-school students (Day et al., 2015, abstract only).
- Children's response to perceptual richness changed with age. First and second graders learned more from a rich diagram, and fourth and fifth graders generalized more from a bland one (Menendez et al., 2022, abstract only).
- An earlier finding that abstract examples beat concrete ones in undergraduates was attributed to badly designed concrete examples. Improved concrete examples did as well as abstract ones or better (Trninic et al., 2020).

### 2.4. Making the link explicit

**Evidence: one design review and one experiment.**

- The review "reports that failing to tell learners how representations connect was the most common design flaw, associated with null results" (Suh et al., 2020, as summarized on the board).
- Instruction that only described procedures produced the most overgeneralization. Instruction that "highlighted links between the formula and its visual referent" did about as well as letting learners search first (Hallinen et al., 2021, abstract only).

### 2.5. Delivery by a computer or an LLM

**Evidence: none for LLMs.**

- An online tutor that faded an animation into Python code gave no significant advantage over code alone, with 50 university students (Markova, 2021, abstract only).
- No LLM study was found. Adapting the fading pace to each learner's performance appears untested.

## 3. Where the evidence disagrees

- **Order of the forms.** Abstract only beat fading in some undergraduate studies, concrete only beat fading in grades 5–6, and concrete-to-abstract beat the reverse in others (Suh et al., 2020). Abstract-to-concrete beat concrete-to-abstract on transfer for DC circuits (Johnson et al., 2014, as reported by Lichtenberger et al., 2024).
- **Domain.** The positive results come mostly from basic mathematics. Physics results are equivocal (Lichtenberger et al., 2024).
- **Costs.** The switch between forms added learning time in one study (Jaakkola & Veermans, 2020, abstract only; unverified on the board). No study measured cognitive load or learner opinions.

## 4. What this means for `teach-better`

These are inferences from the evidence above, not tested rules. The report does not change the skill.

1. **Do not adopt fading as a fixed sequence.** Classroom studies found it no better than showing both forms at once, and the delayed evidence is one thesis.
2. **Always state the link.** When a card shows a formula or rule next to a concrete case, name which part of the case each symbol stands for. A two-column table works: symbol, and what it is in the example. This is the best-supported point, and it fits the skill's existing rule to add a table next to the explanation (section 3.1).
3. **Keep concrete examples lean.** Extra context and irrelevant detail hurt transfer. The example should contain the features the rule needs, and little else.
4. **Concrete first is reasonable for new learners.** It is consistent with the skill's worked example first for new material. The evidence does not show that the order matters for adults.
5. **Check transfer with a different surface.** Concrete materials helped retention more than transfer. The skill's rule to include a quiz problem that differs from the examples (section 4.1) covers this.
6. **A candidate for a small addition to existing cards, not a separate tool.** The evidence supports a rule about linking, not a new card type.

## 5. Method

- Research board: `.research/concrete-abstract-linking/` (not committed). It holds every question, claim and source, with each source marked by how it was read.
- Workers on a cheaper model researched the questions. The coordinator checked the quotes cited above against their sources. Exceptions: Springer and some university pages returned bot-check pages or hid the abstract. The affected claims (Jaakkola & Veermans, 2018, 2020; Liu et al., 2026; Fyfe et al., 2014; the CRA single-case review; Markova's thesis page; one Turku record) are marked unverified on the board. This report cites only Jaakkola and Veermans (2020) among them, and says so.
- Abstract-only sources are marked "abstract only" in the text, and support only what their abstracts state.

## 6. Open questions

- **Primary pro-fading studies** (McNeil & Fyfe, 2012; Fyfe et al., 2015; Ottmar & Landy, 2017) could not be read. Their effect sizes here are secondhand.
- **Delayed tests of fading.** Only one unreviewed thesis.
- **Prior knowledge.** No fading study on it was readable. One study of static visuals found concrete visuals better for learners with low prior knowledge and abstract ones better for learners with high prior knowledge (Zheng et al., 2022; unverified on the board). Whether this carries to fading is untested.
- **Adults learning alone, and LLM tutors.** No study found.

## 7. Sources

Carbonneau, K. J., Marley, S. C., & Selig, J. P. (2013). A meta-analysis of the efficacy of teaching mathematics with concrete manipulatives. *Journal of Educational Psychology, 105*(2), 380–400. https://www.uv.es/tamin/master_da/articulo_metaanalisis_manipulativo.pdf

Cofone, R. (2020). *Concreteness fading with Montessori materials to teach mathematical equivalences in primary school* [Doctoral thesis, Università degli Studi Roma Tre]. https://arcadia.sba.uniroma3.it/bitstream/2307/40843/1/COFONE_ConcretenessFadingMontessori.pdf

Day, S. B., Motz, B. A., & Goldstone, R. L. (2015). The cognitive costs of context: The effects of concreteness and immersiveness in instructional examples. *Frontiers in Psychology*. https://pubmed.ncbi.nlm.nih.gov/26648905/

Goldstone, R. L., & Son, J. Y. (2005). The transfer of scientific principles using concrete and idealized simulations. *The Journal of the Learning Sciences, 14*(1), 69–110. https://typeset.io/pdf/the-transfer-of-scientific-principles-using-concrete-and-18wws3vney.pdf

Hallinen, N. R., Sprague, L. N., Blair, K. P., Adler, R. M., & Newcombe, N. S. (2021). Finding formulas: Does active search facilitate appropriate generalization? *Cognitive Research: Principles and Implications*. https://pubmed.ncbi.nlm.nih.gov/34279745/

Jaakkola, T., & Veermans, K. (2020). Learning electric circuit principles in a simulation environment with a single representation versus "concreteness fading" through multiple representations. *Computers & Education, 148*, 103811. https://research.utu.fi/converis/portal/detail/Publication/46049389?lang=en_US

Kokkonen, T., Lichtenberger, A., & Schalk, L. (2022). Concreteness fading in learning secondary school physics concepts. *Learning and Instruction, 77*, 101524. https://doi.org/10.1016/j.learninstruc.2021.101524

Lichtenberger, A., Kokkonen, T., & Schalk, L. (2024). Learning with multiple external representations in physics: Concreteness fading versus simultaneous presentation. *Journal of Research in Science Teaching*. https://www.utupub.fi/bitstreams/6a9fab27-966b-4c59-8d45-ba320b9f245b/download

Markova, N. (2021). *Investigating concreteness fading in the programming domain with an online computer tutor* [Master's thesis, Carleton University]. https://curve.carleton.ca/8d1d203a-db6d-465d-89f6-9b10f69c8aab

Menendez, D., Rosengren, K. S., & Alibali, M. W. (2022). Detailed bugs or bugging details? The influence of perceptual richness across elementary school years. *Journal of Experimental Child Psychology*. https://pubmed.ncbi.nlm.nih.gov/34416553/

Suh, S., Lee, M., & Law, E. (2020). How do we design for concreteness fading? Survey, general framework, and design dimensions. In *Proceedings of Interaction Design and Children (IDC '20)*. ACM. https://sanghosuh.github.io/papers/concreteness_idc.pdf

Trninic, D., Kapur, M., & Sinha, T. (2020). The disappearing "advantage of abstract examples in learning math". *Cognitive Science, 44*, e12851. https://edrl.berkeley.edu/wp-content/uploads/2020/08/Trninic-2020-CogSci.pdf

Volodin, S., Khodr, H., Dillenbourg, P., & Johal, W. (2025). *Going down the abstraction stream with augmented reality and tangible robots: The case of vector instruction*. arXiv. https://arxiv.org/abs/2504.14562

Zheng, R., Cordner, H., & Spears, J. (2022). The impact of annotation on concrete and abstract visual representations in science education: Testing the expertise reversal effect. *Research and Practice in Technology Enhanced Learning, 17*, 18. https://link.springer.com/content/pdf/10.1186/s41039-022-00194-y.pdf
