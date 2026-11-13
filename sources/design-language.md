# Creating, applying and reviewing a design language with an AI agent

Research findings · Search date: 13 November 2026

The evidence supports a design language as a way to keep work fast and consistent, and supports several rules about how an agent should create and check one. It does not support most rules about how to construct the parts: no controlled study was found for type scale ratios, the number of sizes, typeface pairing or fixed spacing scales, and palette evidence comes mostly from charts. Three findings matter most for an agent. Generated interfaces converge on the same look. Agents often do not implement design requirements they were given or stated themselves. People largely agree on what colours and typefaces express, but the agreement varies by person, nation and context.

**Scope.** A design language (also called a design system or style guide) for interfaces: what it contains, how it is derived from what a person or organisation wants to express, how its parts are constructed, how it is written so that people and agents apply it, and how a design language or a design is reviewed. Rules for a single page are in `design-better.md`, and the process of building one interface is in `design-process.md`. The goal is to decide what `/design-better` can tell an agent to do when it creates, applies or reviews a design language.

**Status.** This run was cut short at the user's request, and it is less complete than the two earlier ones. No high- or medium-priority question that was admitted is open. Of 47 questions, 25 are answered, 1 is contested, 2 found nothing, 3 were merged or set out of scope, and 16 are open at low priority. Eleven of those were proposed late and set to low without the usual review of their stakes, so some may deserve research. Twelve Sonnet workers and one coordinator ran the research: 78 sources and 116 claims. Sonnet verifiers opened the source pages: 98 claims are verified, 11 are unverified and 7 were not checked. The coordinator set 6 of the verified ones by correcting the claim to match the copied passage. This report does not rely on unverified or unchecked claims. Most sources were read as abstracts or through a fetch tool's extraction, and many are preprints, so most answers are thin.

## How firmly the evidence supports each rule

| Rule a skill could state | Support | Section |
|---|---|---|
| A design language speeds building and keeps it consistent | Small studies; depends on builders using it | 1 |
| A design language makes interfaces easier to use | Not found | 1 |
| Check what was built against the design language, do not trust the agent followed it | Several studies of generated interfaces | 2 |
| Write the design language in a structured form | One study | 2 |
| Name your default look and depart from it | Sameness is measured; the remedy is tested only outside interfaces | 3 |
| Keep structure simple and typical | Two studies; experts and some audiences differ | 4 |
| Derive choices from the qualities the user wants, then check they come through | Agreement on meaning is measured; whole designs tested once | 5 |
| Ask who the audience is before fixing colour and density | Large rating study | 5 |
| Keep meaning-carrying colours few and pair them with a shape or label | Chart studies | 6 |
| Type scale ratios, number of sizes, pairing, spacing scales | Convention only, except heading size steps | 7 |
| Review against a fixed list of criteria; say what works, specifically | Two studies from one group | 8 |
| Check page-wide consistency explicitly when a model reviews | One study | 8 |
| Which documentation content builders use | Not found | 9 |

## 1. What a design language changes

- Sources describe a design system as component libraries, design guidelines and style guides, and say it differs from a style guide by carrying the identity of the organisation (Lamine & Cheng, 2022). A design token is a name with at least a value (Chenais et al., 2026). "Design language" has no standard definition in the sources found.
- Building is faster with one. Eight developers coded a form in a median of 2 hours with a design system against 4.2 hours from scratch; the study calls itself small, and its consistency ratings were subjective (Sparkbox, n.d.). In an industry experiment, AI assistance that knew the design system cut delivery time against manual and design-system-only work (Silva et al., 2026; abstract only).
- A thesis found that efficiency, consistency and learning vary with how firmly design knowledge is written into a maintained, shared artefact (Gjidoda, 2026).
- No study was found that measures usability or perception for the audience with and without a design system.

**Challenge.** No study was found in which a design system slowed work or lowered consistency. The limit is adoption: at one large company, adoption of a mature design system stayed limited because of knowledge gaps, slow evolution and lack of flexibility, in 76 interviews (Richter et al., 2025; abstract only). A vendor survey reports that buy-in satisfaction fell from 42% to 32% in a year (zeroheight, 2026). Interviewed leaders found evolving their systems considerably difficult (Lamine & Cheng, 2022).

**What this means for the skill (my reading):** the skill can say a design language keeps work consistent. It cannot say it makes an interface usable, so the checks of `design-better.md` still apply. A design language helps only if it is short enough and current enough to be used.

## 2. Agents following a design language

- Generative UI tools do not implement what they say. Over a quarter of the design rationales the tools stated were not implemented, and four of five tools implemented 6% or fewer of the functional principles stated in prompts (Imteyaz et al., 2026; abstract only).
- Looking right is not following the requirements: eight multimodal models that reconstructed designs visually still showed substantial gaps on implementation requirements (Shi et al., 2026; abstract only).
- A structured, parameterised specification captured design intent more faithfully than prompt text (Chen et al., 2025; abstract only).
- Automated checks find violations at scale. In 60,756 Android screens, 7,497 broke at least one guideline of their design system, detected with precision 0.81 and recall 0.90 (Yang et al., 2021). A comparison of mock-ups with implementations found 82 violations in 71 screen pairs, mostly layout, resources such as colour and components, and text (Moran et al., 2018).
- No controlled study was found that compares tokens, a written specification, a component library and examples as the form given to an agent, and none of token linting.

**Challenge.** Machine checking raised adherence where it was tested: using accessibility audit results as a training reward cut inaccessible output by 87.5% and 58.1% under two auditors (Yoon et al., 2025; abstract only). That is a trained model, not an agent given a specification at run time.

**What this means for the skill (my reading):** after building, the agent checks the result against the design language by searching for values and components that are not in it. Writing values in tables with names is a guide with one study behind it.

## 3. Sameness of generated designs

- Across five generative UI tools, outputs converge in visual appearance and layout, and vary more in colour (Imteyaz et al., 2026; abstract only).
- Model-generated design solutions were less diverse than human ones on every topic tested, in a study of design concepts, not interfaces. A prompt with a critique step gave the highest diversity among the prompt methods, and higher temperature did not reliably raise it (Ma et al., 2024).
- Some variety remains: in 73 homepages built with coding agents, some builders escaped the dominant styles (Boussioux et al., 2026).
- Sameness is not unique to models. Per a review of one study, human-made websites also became more alike over a decade, in step with shared libraries (Kolko, 2025; secondary).

**Challenge.** No study was found that contradicts the convergence finding, and none that tests a remedy on rendered interfaces. Claims about specific recurring defaults, such as particular gradients or typefaces, appeared only in blogs.

**What this means for the skill (my reading):** the agent names the look it would produce by default and makes at least one direction depart from it, then reviews its directions against each other. The remedy is tested only on design concepts, so it gets soft wording.

## 4. What people judge as appealing

- Websites with low visual complexity and a typical look were rated most appealing (Tuch et al., 2012; abstract only).
- Perceived complexity and colourfulness, with demographic variables, explain about half of the variance in appeal ratings given after half a second, and these first judgments later affect opinions of usability and trustworthiness (Reinecke et al., 2013; abstract only).
- The level of colourfulness and complexity that people like most differs by gender, education and country, in 2.4 million ratings (Reinecke & Gajos, 2014).

**Challenge.** Design experts rated as unaesthetic many pages that laypersons had rated aesthetic, in a small study (Bölte et al., 2017). A 2025 study reported to find novelty a stronger predictor than typicality could not be read.

**What this means for the skill (my reading):** keep structure simple and familiar and put the distinct character into a few elements. This is a default for a general audience, not a rule, and section 3 pulls the other way.

## 5. From what the user wants to express to visual choices

- People agree on what colours express. Colour-emotion associations share one pattern across 30 nations (r = .88), with differences growing between nations that are linguistically or geographically apart (Jonauskaite et al., 2020).
- The agreement has limits. A review of 132 studies finds the associations reliable but not shared by everyone, with individual differences, and expects them to change in specific contexts (Jonauskaite & Mohr, 2025). A culture difference appeared for red against green and not for red against white (Kawai et al., 2022).
- Typefaces carry personality, mostly display and script faces, with serif and sans serif neutral (Shaikh & Chaparro, 2016; abstract only). The same holds in Arabic (Jordan et al., 2017).
- One test manipulated whole web pages: simplicity and cohesion produced a bold personality, contrast, density and regularity an analytical one, and the tested attributes did not produce a sophisticated one (Park, 2006; abstract only).

**What this means for the skill (my reading):** common meanings of colours and typefaces are a starting point. The agent then shows directions and asks which qualities each expresses, because some intended qualities do not come through. The audience must be known before colour and density are fixed.

## 6. Colour

- People read colour categories less accurately as the number of categories rises from 2 to 10 (Tseng et al., 2023; abstract only). Pairing colour with shape improved accuracy, most for 5 to 8 categories (Tseng et al., 2026; abstract only). Both studies are on charts.
- Outside charts, a study of colour schemes for coloured text at fixed contrast found that the choice of hues changed how fast readers found information (Ng et al., 2024; abstract only).
- For colour vision deficiency, most tools only simulate it and few help designers generate palettes (Geddes et al., 2025; abstract only).
- Two contrast metrics disagree on a large share of colour pairs, and neither had been validated against legibility data in the article read (Waller, 2022).
- Light against dark variants conflict: cognitive test scores were higher in light mode in one study (Gazit et al., 2025; abstract only), and dark mode improved accuracy on some dashboard tasks in another (Ettling et al., 2025; abstract only).
- No user test of palettes built in perceptual colour spaces was found.

**What this means for the skill (my reading):** define colours by role, check each allowed text and background pair, keep meaning-carrying colours few and never rely on colour alone. The number is a guide from chart research. A dark variant is a choice.

## 7. Type and spacing

- Reviews find no most legible typeface and no significant effect of serifs; legibility depends on the reader and the situation (Ho Sang & Petrarca, 2025; Beier & Thiessen, 2025; abstracts only).
- Size is the strongest cue to a heading's level, and differences of about 20% in relative size are easier to tell apart (Williams & Spyridakis, 1992; abstract only). Headings that combine bold with a larger size helped readers find information faster (Timpany, 2018; abstract only). Both are on documents.
- Wider line spacing improved the speed and accuracy of visual search on web pages, and left-aligned text performed better although users preferred justified text (Ling & van Schaik, 2007; abstract only).
- No controlled study was found on the number of sizes or weights, typeface pairing, or fixed spacing scales.

**Challenge (contested).** Typeface features do matter for some readers. Wider letters raised acuity in an experiment with low-vision and control groups (Mangas, 2024; a write-up by a type foundry), and one research summary reports that no single font suited all readers (Readability Matters, 2022). The primary papers were blocked.

**What this means for the skill (my reading):** typeface choice follows the qualities the user wants. A small set of sizes and a spacing scale are stated as design choices. Heading steps of about a fifth and avoiding narrow letterforms get soft wording.

## 8. Reviewing a design

- A rubric of expert criteria made critiques by novices as valuable to designers as critiques by experts (Yuan et al., 2015; abstract only). Organising critique around design principles let novices produce more critiques than free-form critique (Wu et al., 2013; abstract only).
- Designers found feedback most helpful when it was positive and specific (Yuan et al., 2015).
- A model reviewing interface mock-ups against guidelines had lower precision than human evaluators with a similar overall score (0.466 against 0.478). Of 100 distinct violations, the model found 9 alone, 29 together with humans, and humans found 62 alone. Humans found more page-wide violations, and the model's usefulness fell over iterations (Duan, Warner, et al., 2024).
- Model critique does not yet match human evaluators; prompting with a dataset of expert critiques gave a 55% gain (Duan, Chen, et al., 2024; abstract only).
- No study was found that measures the effect of the form of a critique on the quality of the final design.

**What this means for the skill (my reading):** a review of a design language works through a fixed list, reports what works and must be kept, and checks consistency across whole screens, which is where model reviews are weakest.

## 9. Documentation and change

- No study was found that measures which documentation content builders use: rules, rationale, examples or code.
- At one company, designers and developers could not find their way around a guide organised by the system's own logic, and the team reorganised it and added search (Sanderson-Harris, n.d.). In open-source design systems, issues about documentation mostly report missing or wrong component documentation (Lamine & Cheng, 2022).
- A vendor audit of 375 sites reports average token coverage of about 40%; its method is not described (OverlayQA, 2026).
- No quantitative study of versioning, deprecation or exceptions was found.

**What this means for the skill (my reading):** the document's form, examples of correct and wrong use, and the rule that changes go through the user are design choices.

## What the research does not cover

- Usability or perception for the audience with and without a design language.
- A comparison of the forms in which a design language is given to an agent.
- A tested remedy for sameness on rendered interfaces.
- Type scale ratios, number of sizes, typeface pairing, spacing scales, and palettes built in perceptual colour spaces.
- Which properties make an interface look trustworthy or distinctive.
- Which documentation content is used.
- Legibility and type needs of non-Latin scripts in interfaces.

## Open questions

Sixteen low-priority questions were not researched. They include: adoption and maintenance cost against benefit; references and citing works of the typeface reviews and of several studies above; type for non-Latin scripts; palette size outside charts; documentation in adjacent fields; a blocked study on novelty and typicality of websites; and the typeface personality studies that could not be read.

The research board is at `.research/design-language/` in the main checkout.

## References

Beier, S., & Thiessen, M. (2025). Applying cognitive and perceptual science to typeface choices. *Ergonomics*. https://adk.elsevierpure.com/en/publications/applying-cognitive-and-perceptual-science-to-typeface-choices/

Bölte, J., Hösker, T. M., Hirschfeld, G., & Thielsch, M. T. (2017). Electrophysiological correlates of aesthetic processing of webpages: A comparison of experts and laypersons. *PeerJ, 5*, e3440. https://pmc.ncbi.nlm.nih.gov/articles/PMC5463973/

Boussioux, L., Zhao, Z., & Cho, K. (2026). *One tool, one taste? How vibe coding trades collective diversity for individual creativity*. arXiv. https://arxiv.org/html/2609.38183

Chen, Y., Shi, C., & Chen, L. (2025). *SpecifyUI: Supporting iterative UI design intent expression through structured specifications and generative AI*. arXiv. https://arxiv.org/abs/2509.07334

Chenais, L., McMahon, K., Powers, D., Ström-Awn, M., & Vitan, D. (Eds.). (2026). *Design tokens format module 2025.10*. W3C Design Tokens Community Group. https://www.designtokens.org/tr/drafts/format/

Duan, P., Chen, C., Li, G., Hartmann, B., & Li, Y. (2024). *UICrit: Enhancing automated design evaluation with a UI critique dataset*. arXiv (UIST 2024). https://arxiv.org/abs/2407.08850

Duan, P., Warner, J., Li, Y., & Hartmann, B. (2024). Generating automatic feedback on UI mockups with large language models. *ACM CHI 2024*. https://arxiv.org/pdf/2403.13139

Ettling, T. J., Steinmann, D., Bektas, K., & Abbad-Andaloussi, A. (2025). An eye tracking study on the effects of dark and light themes on user performance and workload. *ACM Symposium on Eye Tracking Research & Applications (ETRA 2025)*. https://alexandria.unisg.ch/handle/20.500.14171/122292

Gazit, T., Tager-Shafrir, T., Zhong, H.-X., Hung, P. C. K., & Cheung, V. (2025). The dark side of the interface: Examining the influence of different background modes on cognitive performance. *Ergonomics, 69*(5). https://eprints.whiterose.ac.uk/id/eprint/231852/

Geddes, C., Eggertson, E. C., Sutton, J., & Tigwell, G. W. (2025). Designing for colour vision deficiency: A scoping review of resources that support designers in choosing accessible colours. *ASSETS 2025*. ACM. https://researchprofiles.ku.dk/en/publications/designing-for-colour-vision-deficiency-a-scoping-review-of-resour/

Gjidoda, L. (2026). *The impact of a standardized UX library on efficiency, interface consistency, and team learning* [Bachelor thesis, Hochschule für Wirtschaft FHNW]. https://studierendenprojekte.wirtschaft.fhnw.ch/view/5089

Ho Sang, B., & Petrarca, D. (2025). Beyond (type)face value: A systematic literature review examining design factors influencing the legibility and readability of typography. *Visible Language, 59*(3). https://journals.uc.edu/index.php/vl/article/view/8855

Imteyaz, K., Imteyaz, K., Rajpal, N., Shaikh, K., Muller, M., & Savage, S. (2026). *Design theater: Evaluating the gap between user-facing design reasoning and implementation in generative UI tools*. arXiv. https://arxiv.org/abs/2607.22928

Jonauskaite, D., Abu-Akel, A., Dael, N., et al. (2020). Universal patterns in color-emotion associations are further shaped by linguistic and geographic proximity. *Psychological Science, 31*(10), 1245–1260. https://eprints.whiterose.ac.uk/169496/

Jonauskaite, D., & Mohr, C. (2025). Do we feel colours? A systematic review of 128 years of psychological research linking colours and emotions. *Psychonomic Bulletin & Review, 32*(4), 1457–1486. https://pmc.ncbi.nlm.nih.gov/articles/PMC12325498/

Jordan, T. R., AlShamsi, A. S., Yekani, H. A. K., AlJassmi, M., Al Dosari, N., Hermena, E. W., & Sheen, M. (2017). What's in a typeface? Evidence of the existence of print personalities in Arabic. *Frontiers in Psychology, 8*. https://www.frontiersin.org/articles/10.3389/fpsyg.2017.01229/full

Kawai, C., Zhang, Y., Lukacs, G., Chu, W., Zheng, C., Gao, C., Gozli, D., Wang, Y., & Ansorge, U. (2022). The good, the bad, and the red: Implicit color-valence associations across cultures. *Psychological Research, 87*(3), 704–724. https://pmc.ncbi.nlm.nih.gov/articles/PMC10017663/

Kolko, J. (2025, July 12). *Investigating the homogenization of web design: A mixed-methods approach, by Sam Goree, Bardia Doosti, David J. Crandall, Norman Makoto Su* [Review]. https://www.jonkolko.com/phd/writing/25-07-12-homogenization-of-web-design

Lamine, Y., & Cheng, J. (2022). *Understanding and supporting the design systems practice*. arXiv (to appear in Empirical Software Engineering). https://arxiv.org/abs/2205.10713

Ling, J., & van Schaik, P. (2007). The influence of line spacing and text alignment on visual search of web pages. *Displays, 28*(2), 60–67. https://research.tees.ac.uk/en/publications/the-influence-of-line-spacing-and-text-alignment-on-visual-search/

Ma, K., Grandi, D., McComb, C., & Goucher-Lambert, K. (2024). *Exploring the capabilities of large language models for generating diverse design solutions*. arXiv. https://arxiv.org/html/2405.02345

Mangas, H. (2024, June 3). *Designing fonts with low-vision readers in mind: A reading acuity experiment*. Typotheque. https://www.typotheque.com/research/designing-fonts-with-low-vision-readers-in-mind

Moran, K., Li, B., Bernal-Cardenas, C., Jelf, D., & Poshyvanyk, D. (2018). *Automated reporting of GUI design violations for mobile apps*. arXiv (ICSE 2018). https://ar5iv.labs.arxiv.org/html/1802.04732

Ng, H. Y., He, Z., & Huang, T.-H. K. (2024). *What color scheme is more effective in assisting readers to locate information in a color-coded article?* arXiv (IEEE VIS 2024). https://arxiv.org/abs/2408.06494

OverlayQA. (2026). *Design token drift: We audited 375 sites. Only 7.5% got it right*. https://overlayqa.com/blog/design-token-drift-study/

Park, S.-E. (2006). Analysis of the relationship between e-brand personalities and visual attributes. *Archives of Design Research, 19*(4), 187–204. https://koreascience.kr/article/JAKO200634718446371.page

Readability Matters. (2022, March 29). *Research highlight: Towards individuated reading experiences*. https://readabilitymatters.org/articles/towards-individuated-reading-experiences

Reinecke, K., & Gajos, K. Z. (2014). Quantifying visual preferences around the world. *CHI 2014*, 11–20. ACM. https://eecs.harvard.edu/~kgajos/papers/2014/reinecke14visual.shtml

Reinecke, K., Yeh, T., Miratrix, L., Mardiko, R., Zhao, Y., Liu, J., & Gajos, K. Z. (2013). Predicting users' first impressions of website aesthetics with a quantification of perceived visual complexity and colorfulness. *CHI 2013*. ACM. https://www.eecs.harvard.edu/~kgajos/papers/2013/reinecke13predicting.shtml

Richter, K. S., Rüssel, J., & Karczewski, K. (2025). Improving design system adoption with inner source. *CHI EA '25*. ACM. https://doi.org/10.1145/3706599.3706705

Sanderson-Harris, Z. (n.d.). *Does your design system have a UX problem?* Xero. https://www.xero.com/au/design/articles/does-your-design-system-have-a-ux-problem

Shaikh, D., & Chaparro, B. (2016). Perception of fonts: Perceived personality traits and appropriate uses. In *Digital fonts and reading*. World Scientific. https://portfolio.erau.edu/en/publications/perception-of-fonts-perceived-personality-traits-and-appropriate-/

Shi, C., Chen, Y., Zhou, T., Lu, Q., Yue, S., Hu, X., Ru, J., & Chen, L. (2026). *TaoD2C-Bench: Benchmarking MLLMs for industrial UI code generation beyond visual fidelity*. arXiv. https://arxiv.org/abs/2610.10374

Silva, L., Rocha, T., Davila, N., & Pinto, G. (2026). *Design-system-aware development with AI: Evaluating productivity and design consistency*. arXiv (SBES Industry 2026). https://arxiv.org/abs/2607.13156

Sparkbox. (n.d.). *Yes, design systems do improve developer efficiency and design consistency*. Sparkbox Foundry. https://sparkbox.com/foundry/design_system_roi_impact_of_design_systems_business_value_carbon_design_system

Timpany, C. (2018). *Typographic emphasis of headings: Methods of typographic emphasis to assist with search of unfamiliar and familiar text* [Doctoral thesis, University of Waikato]. https://researchcommons.waikato.ac.nz/handle/10289/12091?show=full

Tseng, C., Quadri, G. J., Wang, Z., & Szafir, D. A. (2023). *Measuring categorical perception in color-coded scatterplots*. arXiv (ACM CHI 2023). https://arxiv.org/abs/2303.15583

Tseng, C., Wang, A. Z., Quadri, G. J., & Szafir, D. A. (2026). *Redundant is not redundant: Automating efficient categorical palette design unifying color & shape encodings with CatPAW*. arXiv. https://arxiv.org/abs/2602.06792

Tuch, A. N., Presslaber, E., Stoecklin, M., Opwis, K., & Bargas-Avila, J. (2012). The role of visual complexity and prototypicality regarding first impression of websites: Working towards understanding aesthetic judgments. *International Journal of Human-Computer Studies, 70*(11), 794–811. https://research.google/pubs/the-role-of-visual-complexity-and-prototypicality-regarding-first-impression-of-websites-working-towards-understanding-aesthetic-judgments/

Waller, S. (2022). *Does the contrast ratio actually predict the legibility of website text?* University of Cambridge Engineering Design Centre. https://www.cedc.tools/article.html

Williams, T. R., & Spyridakis, J. H. (1992). Visual discriminability of headings in text. *IEEE Transactions on Professional Communication, 35*(2), 64–70. https://search.isc.ac/Inventory/49/900509.htm

Wu, W., Luther, K., Pavel, A., Hartmann, B., Dow, S., & Agrawala, M. (2013). *CrowdCritter: Strategies for crowdsourcing visual design critique* (UCB/EECS-2013-95). University of California, Berkeley. https://www2.eecs.berkeley.edu/Pubs/TechRpts/2013/EECS-2013-95.html

Yang, B., Xing, Z., Xia, X., Chen, C., Ye, D., & Li, S. (2021). Don't do that! Hunting down visual design smells in complex UIs against design guidelines. *ICSE 2021*. https://2021.icse-conferences.org/details/icse-2021-papers/87/Don-t-Do-That-Hunting-Down-Visual-Design-Smells-in-Complex-UIs-against-Design-Guidel

Yoon, J., Cho, J., Kim, J., Chung, J., Jeon, J., Lim, S., & Yu, Y. (2025). *A11yn: Aligning LLMs for web accessibility-aware UI generation*. arXiv. https://arxiv.org/abs/2510.13914

Yuan, A., Luther, K., Krause, M., Dow, S. P., & Hartmann, B. (2015). *Worker expertise and expert rubrics in crowdsourced design critique* (UCB/EECS-2015-223). University of California, Berkeley. https://www2.eecs.berkeley.edu/Pubs/TechRpts/2015/EECS-2015-223.html

zeroheight. (2026). *Design systems report 2026*. https://report.zeroheight.com/2026
