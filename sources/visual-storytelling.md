# Visual storytelling: How an AI agent should introduce a dense document with a short sequence of visuals

Research findings for the show-better rebuild  
Prepared for Nicolas · Search date: 8 November 2026

The evidence supports an introduction deck that works as a **graphic organizer for the document**. It shows the document's structure and the relations between its main ideas, in forms that let the reader see what prose would make them work out. It does not repeat numbers a sentence already states. Organizers provided before or with a text improved comprehension of that text (g = 0.53 across 49 comparisons), and signals of a text's structure helped learning (d = .38). Graphics in general help comprehension only modestly (g = 0.39), and only graphics that organize information help, not ones that merely illustrate it. Plain diagrams supported transfer better than rich ones. No study tests a visual introduction placed before a research paper or business document, so the deck's design rests on these neighbouring findings.

**Scope.** This report extends `sources/visual-presentations.md` and `sources/visual-representation-of-information.md` and does not repeat them. Those cover segmenting, sentence headlines, emphasis, polish and trust, the encoding ranking, chart-type choice, and the failure modes of generated slides. This report covers:

1. When a visual does something prose cannot, and when text is as good.
2. The range of representation forms, and evidence on how well readers understand each.
3. How a sequence of visuals becomes a story.
4. How research papers and business documents are turned into visual introductions.
5. Plain-text diagrams for a terminal.

**Outcomes.** You asked for comprehension over recall. Each finding below names what its study measured: comprehension, transfer (applying knowledge to a new case), recall, preference, or reach.

**Status.** The research stopped at the `medium` level: every high- and medium-priority question is answered or contested. One question is contested (section 7). The quotes of all 101 claims on the board were checked against their pages, and all were confirmed. Ten were corrected on the way, for example where the original claim overstated the result. The research board is in `.research/visual-storytelling/`.

**Reading level of the evidence.** Most sources were read as abstracts or record pages, because the full texts of the main meta-analyses were blocked. Read in full or in long verbatim parts: Segel and Heer (2010), Hullman et al. (2013), Heer and Robertson (2007), Correll and Gleicher (2014), Peebles and Ali (2015), Hoffberg et al. (2020) and Lengler and Eppler (2007). Five claims rest on secondary sources (a blog, two press releases, Wikipedia), and they are marked where they appear.

## 1. Rules the evidence supports

| Candidate rule | Evidence | Strength |
|---|---|---|
| **Use a visual where it organizes information, not to illustrate or repeat it** | Graphics added to text improved reading comprehension, g = 0.39 over 39 studies, with no difference among pictures, pictorial diagrams and flow diagrams (Guo et al., 2020). In problem solving, organizational pictures improved accuracy, while informational pictures had no significant aggregate effect (Hu et al., 2021). For equivalent information, a representation's value depends on what it lets the reader recognise, infer and search directly (Larkin & Simon, 1987). | Moderate: two meta-analyses (abstracts) and a theory paper |
| **Treat the deck as an organizer for the document it introduces** | Instructor-provided graphic organizers improved comprehension of text (g = 0.53, 49 comparisons) and memory (g = 0.70, 37 comparisons). The authors warn that publication bias may inflate these effects (Ponce-Arias et al., 2025). Concept maps improved retention, by amounts that varied from small to large with the comparison condition (Nesbit & Adesope, 2006). | Moderate: two meta-analyses, abstract only; none isolates an organizer placed before the text |
| **Show the document's structure: its parts, their order, and the questions it answers** | Signals of structure improved learning, d = .38, with larger effects in higher-quality studies (Alpizar et al., 2020). Headings gave better memory for a text's subtopics than preview sentences, with no difference for facts, and any structure signal improved outlining of the text (Lorch et al., 2013). Preview instruction raised fourth graders' comprehension of expository text (Spires et al., 1992). | Moderate for signalling; weak for previews of whole documents |
| **Prefer plain, abstract forms over rich or concrete ones** | Adults who saw a plain diagram of metamorphosis transferred more accurately than those who saw a rich one, and both learned the taught case equally well (Menendez et al., 2020). Readers who knew more about the topic were less distracted by the rich details (Watson, 2020, a blog summary). Interesting but irrelevant details lowered learning outcomes across 58 studies (Zaske, 2020, a press release on Sundararajan & Adesope, 2020). | Moderate: consistent direction; key primaries read only as abstracts or summaries |
| **Adjust to what the reader knows** | Guidance that helps novices can harm more experienced learners (Wikipedia contributors, n.d., on the expertise reversal effect). Experts read bar and line versions of the same data equally well, while novices did not (Peebles & Ali, 2015). | Weak: secondary source plus one study |
| **Keep one structure across slides and move from general to specific** | Sequences built on parallelism improved memory and ratings. General-to-specific transitions were the most common in 42 professional narrative visualizations, in 28 of them (Hullman et al., 2013). | Moderate: one study read in full |
| **Keep the reader oriented between related views** | Animated transitions between related charts were more accurate than static switches, and staged animation usually did better still, though not for every chart type. The core problem is keeping viewers oriented, which matters most when they are not interacting (Heer & Robertson, 2007). | Moderate: one study; the earlier report found step-by-step reveal within a slide hurt (see section 5.3) |
| **Frame the content as a story where the content allows it** | Stories were understood and recalled better than essays: g = .48 for comprehension and .72 for memory, over 75+ samples (Mar et al., 2021). Narrative introductions to scientific explanations improved recall but slowed reading (Mensink et al., 2021). | Contested in size for scientific content: see section 7 |
| **Do not judge the deck by reach, preference or engagement** | Visual abstracts raised tweet impressions, retweets and link clicks, without measuring understanding (Hoffberg et al., 2020). Most readers preferred a comic of research results, again without measuring understanding (Kearns et al., 2022). Scrollytelling matched text on comprehension (Méndez & Such, 2026), and interactive simulations did not differ significantly from a static tutorial (Zhao et al., 2025). Polished generated posters scored poorly on a comprehension quiz (Pang et al., 2025). | Moderate: same direction across several designs |
| **Check every generated text diagram by code** | Language models read ASCII layouts far more reliably than they generate them, and even a reasoning model failed to construct accurate layouts in over half of cases (Huang et al., 2026). | Weak: one preprint, models only |

## 2. When a visual does something prose cannot

**Graphics help comprehension modestly, and their kind matters more than their style.** Across 39 studies, adding graphics to text improved reading comprehension with a moderate effect (g = 0.39). Pictures, pictorial diagrams and flow diagrams did not differ significantly from each other. Graphics helped more on open-ended tests than on true/false tests, so the benefit depends on how understanding is measured (Guo et al., 2020). In 51 studies of problem solving, pictures gave a small-to-medium accuracy gain. Organizational pictures helped, but informational or multiple pictures showed no significant aggregate effect (Hu et al., 2021).

**The reason is computational.** Larkin and Simon (1987) argue that two representations can hold the same information while differing in what the reader can do with it. A diagram's value comes from the operations it supports: recognising a pattern, drawing an inference directly, and finding the next item without searching. A diagram is better only when it lets the reader see a relation that the text would make them work out.

**What this means for the deck.** A visual that restates one or two numbers already in its headline gives the reader nothing to recognise or infer, so text is as good. The cases where a visual earns its place are the ones where the reader must see relations among many items at once: structure, sets, flows, distributions and comparisons. This is an inference from the evidence above, not a tested rule.

**Plain beats rich for transfer.** Adults who studied a plain diagram of a life cycle transferred their knowledge to other species more accurately than those who studied a detailed, colourful one, while both groups learned the taught case equally well (Menendez et al., 2020). In three experiments, students taught a rule with abstract symbols transferred it better than students taught with concrete objects (Grabmeier, 2005, a press release on Sloutsky et al., 2005). Learners who already knew the topic were less distracted by rich detail (Watson, 2020).

**Prior knowledge can reverse a benefit.** Guidance that helps novices, such as labels integrated into a diagram, can be redundant or harmful for experienced learners (Wikipedia contributors, n.d., summarizing Kalyuga et al.). Experts read the same data as a bar graph or a line graph equally well, while novices did not (Peebles & Ali, 2015). Evidence on spatial ability is thin. In one study of 6-year-olds, children with high spatial ability learned more from animation, and children with low spatial ability gained nothing from it (Ben Chikha et al., 2021).

## 3. The range of representation forms

### 3.1 Taxonomies

No single agreed taxonomy exists. Three cover the range from different angles:

- **By data type and task.** Shneiderman (1996) classifies visualizations by seven data types and seven tasks.
- **By data type, as a tour.** The Visualization Zoo moves from time series and statistical data to maps, hierarchies and networks (Heer et al., 2010).
- **By function.** Lengler and Eppler (2007) group over a hundred methods. Their groups go beyond charts to concept visualization (such as concept maps), metaphor visualization (such as a metro map or a story template, which convey an insight through the metaphor's characteristics), strategy visualization (such as a strategy canvas or a technology roadmap) and compound visualization, which combines several formats in one frame. The authors call the table an aid for choosing and combining methods, not an exhaustive list.

None of the three is tested on readers, and none covers plain-text diagrams.

### 3.2 Evidence by form

| Form | What it is for | Reader evidence |
|---|---|---|
| **Quantile dotplot** | A distribution or uncertainty shown as countable dots | Near-optimal, more consistent decisions under uncertainty in an incentivized task (Fernandes et al., 2018). Outcome: decision quality |
| **Violin or gradient plot** | A distribution around a mean | Judgments more consistent with statistical inference than bars with error bars: 89.2% and 88.5% against 83.2% (Correll & Gleicher, 2014). Outcome: inference about means |
| **Scatterplot** | Correlation between two measures | High precision and low variance between people when judging correlation (Kay & Heer, 2016). Outcome: perception |
| **Small multiples** | Change across many states, side by side | Faster than animation for dynamic graphs, but less accurate on some tasks (Archambault et al., 2011). Outcome: speed and accuracy |
| **Rescaled numbers** | Very large magnitudes | Restating large numbers on a smaller scale helped people discriminate and rank government budgets (Boyce-Jacino et al., 2022). Outcome: discrimination |
| **Slope chart, diverging bars** | Change between two states; deviation from a reference | No experiment found. Diverging stacked bars rest on a design argument (Heiberger & Robbins, 2014) |
| **Linear and Euler diagrams** | Sets and their overlaps | Linear diagrams were fastest and most accurate, and Venn diagrams worst (Chapman et al., 2014). For set sizes, Euler diagrams with numbers were most effective overall (Stapleton et al., 2019). Outcome: task time and errors |
| **Icicle and sunburst-style charts, treemaps** | Hierarchies | In a 12-person study, treemaps were slower and less preferred than icicle and sundown charts (Woodburn et al., 2019). Outcome: speed, accuracy, preference |
| **Node-link and matrix** | Networks | Neither is better overall: the result depends on the task (Okoe et al., 2017) |
| **Alluvial (Sankey-type) diagrams** | Flows of quantity between states | Accuracy falls as flows and crossings increase, and varies widely by task, from about 88% to about 57% (Arunkumar et al., 2021, synthetic data) |
| **Concept map** | Ideas and their relations | Retention gains from small to large, depending on the comparison condition (Nesbit & Adesope, 2006) |
| **Map** | Where things are | Seventh-graders who studied text with maps had a consistent but non-significant advantage over text alone (Ramirez & Gilmartin, 1996). Outcome: spatial learning |
| **Data comic** | A sequence of panels mixing visuals, text and characters | Preferred over infographics and illustrated text, with the authors reporting better understanding and recall (Wang et al., 2019). An interactive data comic was rated more engaging than text, and participants recalled and understood the data better (Fogwill & Manataki, 2024). Both read as abstracts; preference is the clearest result |
| **Cutaway, exploded view, annotated illustration, storyboard** | Inner structure of a physical thing; a sequence of scenes | No experiment found. Instructional advice says illustrations can reveal structure a photo cannot (Winkelman, n.d.) |
| **Interactive or scrollytelling page** | Reader-controlled exploration | Scrollytelling matched other formats, including plain text, on comprehension while improving experience (Méndez & Such, 2026, 454 participants). Interactive simulations did not differ significantly from a static PDF tutorial, and engagement did not predict learning (Zhao et al., 2025, 605 participants) |

**Gaps.** No primary study was read for causal diagrams, 2×2 positioning grids, or comparisons in concrete units, such as a large number restated as a familiar quantity.

### 3.3 Plain-text diagrams

**No study compares how well people understand text diagrams with rendered ones.** The nearest evidence: developers working at the command line preferred an interactive ASCII dependency graph to the two existing approaches (Isaacs & Gamblin, 2019; outcome: preference). Practitioners disagree. One developer judged ASCII diagrams poor for user-facing documentation, while others use them in specifications and code documentation (Gordon et al., 2015).

**Conventions from standards and tools:**
- Plain-text RFCs allow only ASCII art, with lines of at most 72 characters including indentation, and point readers to the HTML version for other figures (Flanagan, 2016).
- A terminal diagram renderer outputs Unicode box-drawing characters by default. It offers an ASCII-only fallback because box-drawing glyphs are not displayed everywhere, and it keeps a column-width budget. It supports flowcharts, state and sequence diagrams and pie charts, but not Gantt, entity-relationship or class diagrams (leboiko, 2026).

**Language models draw text diagrams badly.** Models read ASCII layouts far more reliably than they generate them. Even a reasoning model failed to construct accurate layouts in over half of cases (Huang et al., 2026). A generated text diagram therefore needs a check by code, such as a renderer or a script that verifies alignment.

## 4. Turning a sequence of visuals into a story

### 4.1 Structures

Segel and Heer (2010) derived seven genres of narrative visualization from 58 examples: magazine style, annotated chart, partitioned poster, flow chart, comic strip, slide show, and film or video. They describe three structures, ordered from author-driven to reader-driven:

1. **Martini glass:** an author-driven path first, then open exploration by the reader.
2. **Interactive slideshow:** each slide states its message, then invites interaction.
3. **Drill-down:** the author gives a theme and the reader chooses which instances to see.

The authors say no single genre is right for every case: the choice depends on the content and the audience, and their taxonomy is not tested on readers. Bach et al. (2018) add narrative design patterns, each with a purpose such as engaging the audience or evoking empathy.

**Reader evidence is thin.** In a study of 180 people, a slideshow layout gave better comprehension than a vertical scroll. Linking text to chart elements raised engagement and, with the slideshow layout, recall (Zhi et al., 2019). Narration in author-driven stories aided understanding but had no significant effect on long-term recall, compared with interactive visualizations without narration (Obie et al., 2020). No study tests the martini glass against the drill-down.

### 4.2 Continuity across slides

Hullman et al. (2013) studied 42 professional narrative visualizations. The most common transition went from general to specific (28 of 42), followed by changing the dimension shown (20) and changing the measure shown (19). In their experiments, sequences that used parallelism, the same structure from one visual to the next, improved memory and ratings. Transition types could be ranked by how costly they were for the audience to follow.

Heer and Robertson (2007) found that animated transitions between related charts helped readers stay oriented and were more accurate than static switches. Staged animation usually did better still, but in one chart type plain animation beat staged animation. No study was found on continuity between static slides, such as keeping one diagram and changing its highlight from slide to slide.

### 4.3 Narrative framing

A meta-analysis of more than 75 samples found stories understood and recalled better than essays. The overall effect was g = .55: .48 for comprehension and .72 for memory. No study characteristic moderated the effect significantly, and the analysis did not test prior knowledge (Mar et al., 2021). Most of the comparisons used narratives and essays with different content, not the same content framed two ways.

For science, a review of 36 studies found encouraging evidence for narrative texts, especially on delayed tests and in longer interventions (Soares et al., 2023). In three experiments, narrative introductions to scientific explanations improved recall but slowed reading (Mensink et al., 2021).

### 4.4 Questions before answers

Prequestions, questions posed before the material, raised later test scores on the questioned items. In one video study they also raised scores on items that were not questioned. The benefit was measured on immediate tests of short videos and was gone after a month in one classroom study (Nebel, 2017, a blog summary).

## 5. Research papers and business documents

### 5.1 Research papers

Papers are turned into visual abstracts, graphical abstracts and comics. **No study found measures whether these formats improve understanding.**

- Visual abstracts raised impressions, retweets and link clicks on Twitter, in a randomized crossover trial of 50 publications (Hoffberg et al., 2020). Outcome: reach.
- In one journal, papers without a graphical abstract got more downloads, views and citations than papers with one (Pferschy-Wenzig et al., 2016). This is observational and measures no understanding.
- Most of 1,236 participants preferred a comic version of research results over a lay summary or an abstract (Kearns et al., 2022). Outcome: preference.

Automatic systems select content in steps. Paper2Poster summarizes sections, matches each summary to a figure and refines the layout with visual feedback (Pang et al., 2025). PPTAgent outlines the slides, pairs each with a reference slide and edits it (Zheng et al., 2025). Both judge output with models, not readers. Paper2Poster has vision-language models answer quiz questions from the poster alone, and reports that GPT-4o posters looked good but scored poorly on the quiz. PPTAgent's model judge correlated with human ratings at 0.71.

### 5.2 Business documents

**Sources propose structures, but none has been tested on readers.**

- The Minto method organizes ideas as a pyramid under one main point. It identifies the reader's question through Situation, Complication and Question (Minto, n.d.).
- Amazon replaces slide presentations with six-page narrative memos, read silently at the start of meetings (Amazon, n.d.).
- A practitioner says a report read without a presenter must stand alone and can carry more text, while the version shown live should reveal one element at a time (Knaflic, 2013).
- Tufte (n.d.) argues, from opinion rather than experiment, that standard slide templates weaken reasoning. The Columbia accident board warned that a senior manager could read a dense slide and miss that it described a life-threatening situation (Thompson, 2003, quoting the board). This is an anecdote, not an experiment.

**The evidence on effect is thin.** When slides are read without the speaker, how they were written matters: detailed slides and big-points-only slides differed in their usefulness as summaries (Grudin et al., 1999). In randomized experiments, audiences did not remember or understand a business case differently after a PowerPoint talk or an oral talk (Moulton et al., 2017). That study concerns talks, not documents read alone.

## 6. The deck as an introduction to the document

This is the question closest to your goal, and its evidence is indirect.

- **Organizers help comprehension of the text.** Graphic organizers provided by an instructor improved comprehension of text (g = 0.53) and memory (g = 0.70). No moderator separated which readers benefited, and publication bias may inflate the effects (Ponce-Arias et al., 2025). For students with learning disabilities, graphic organizers gave greater reading-comprehension gains than comparison conditions, and framed outlines had large effects in the two studies that tested them (Kim et al., 2004, via an ASHA summary).
- **Signalling structure helps.** Signals that guide attention to a text's structure or key elements had a small-to-moderate effect on learning (d = .38), larger in higher-quality studies and in those that controlled for prior knowledge (Alpizar et al., 2020). Headings helped readers remember a text's subtopics better than preview sentences did, and any structure signal helped readers outline the text (Lorch et al., 2013).
- **Previews help, in the one study read.** Teaching fourth graders to attend to preview statements before key parts of a text improved their performance across comprehension and recall measures (Spires et al., 1992).

**What is missing.** No study read isolates an organizer placed before the text rather than during reading, and none tests a deck before a full research paper or business document. No study measures whether readers find their way around the document more easily after an introduction.

## 7. Where sources disagree

- **The size of the narrative benefit for scientific content.** The general meta-analysis finds a moderate story advantage for comprehension (g = .48; Mar et al., 2021). Search results reported a much smaller effect in a science-education meta-analysis (g = 0.16) that depends on prior knowledge. That paper could not be read, so the disagreement is unresolved.
- **Data comics.** The abstracts report better understanding and recall, but their clearest result is preference and engagement (Wang et al., 2019; Fogwill & Manataki, 2024).
- **Animated transitions.** They kept readers oriented between related charts (Heer & Robertson, 2007), while the earlier report found that revealing parts of a slide by animation lowered test scores. The two concern different things: a change between views, and a step-by-step reveal within one view.

## 8. What the research could not find

| Gap | Why it matters for the rebuild |
|---|---|
| No test of a visual introduction before a research paper or business document | The deck's central purpose rests on evidence from organizers and signalling in shorter texts |
| No test of whether an introduction helps readers find their way in a long document | The navigation benefit is assumed, not shown |
| No study of how well people understand text diagrams compared with rendered ones | The terminal path rests on conventions and practitioner opinion |
| No experiment on slope charts, diverging bars, causal diagrams, 2×2 grids, cutaways or storyboards | These forms can be offered, but their choice rests on design reasoning |
| No head-to-head test of story structures | The martini glass, slideshow and drill-down are design options, not ranked |
| No memo-versus-deck experiment for reading without a speaker | Business structures such as Minto's are untested on readers |
| Blocked or unreadable: the advance-organizer meta-analyses (Luiten, 1980; Mahar, 1992; Stone, 1983), Hegarty and Just (1993), Kalyuga's expertise-reversal papers, Tobler et al. (2024) on narrative in science education, and a study of 507 ASCII diagrams in large code bases | Reading them could settle when organizers help, the narrative effect size for science, and how text diagrams are used in practice |

## 9. Method

Thirteen worker agents researched 19 questions on a shared board, with five broadening searches by the coordinator first. The coordinator reopened five questions that were closed with too little searching, merged one duplicate question and one duplicate source, and refocused the brief on comprehension and on the deck as an introduction after your two corrections. Three verifier agents checked every claim's quote against its page. All 101 were confirmed. Ten were corrected on the way, for example where a claim overstated a result or a quote was paraphrased. One correction changed a conclusion: interactive simulations did not beat a static tutorial.

## 10. References

Alpizar, D., Adesope, O. O., & Wong, R. M. (2020). A meta-analysis of signaling principle in multimedia learning environments. *Educational Technology Research and Development, 68*(5), 2095–2119. <https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/A-meta-analysis-of-signaling-principle-in/99900601052901842>

Amazon. (n.d.). *2017 letter to shareholders*. About Amazon. <https://www.aboutamazon.com/news/company-news/2017-letter-to-shareholders>

Archambault, D., Purchase, H., & Pinaud, B. (2011). Animation, small multiples, and the effect of mental map preservation in dynamic graphs. *IEEE Transactions on Visualization and Computer Graphics, 17*(4), 539–552. <https://research.monash.edu/en/publications/animation-small-multiples-and-the-effect-of-mental-map-preservati/>

Arunkumar, A., Ginjpalli, S., & Bryan, C. (2021). *Bayesian modelling of alluvial diagram complexity*. arXiv. <https://ar5iv.labs.arxiv.org/html/2108.06023>

Bach, B., Stefaner, M., Boy, J., Drucker, S., Bartram, L., Wood, J., Ciuccarelli, P., Engelhardt, Y., Koppen, U., & Tversky, B. (2018). Narrative design patterns for data-driven storytelling. In *Data-driven storytelling*. Taylor & Francis. <https://www.microsoft.com/en-us/research/publication/narrative-design-patterns-for-data-driven-storytelling/>

Ben Chikha, A., Khacharem, A., Trabelsi, K., & Bragazzi, N. L. (2021). The effect of spatial ability in learning from static and dynamic visualizations: A moderation analysis in 6-year-old children. *Frontiers in Psychology, 12*, 583968. <https://pmc.ncbi.nlm.nih.gov/articles/PMC8249578/>

Boyce-Jacino, C., Peters, E., Galvani, A. P., & Chapman, G. B. (2022). Large numbers cause magnitude neglect: The case of government expenditures. *Proceedings of the National Academy of Sciences, 119*(28), e2203037119. <https://pmc.ncbi.nlm.nih.gov/articles/PMC9282355>

Chapman, P., Stapleton, G., Rodgers, P., Micallef, L., & Blake, A. (2014). Visualizing sets: An empirical comparison of diagram types. In *Diagrams 2014*, Lecture Notes in Computer Science 8578. Springer. <https://research.brighton.ac.uk/en/publications/visualizing-sets-an-empirical-comparison-of-diagram-types/>

Correll, M., & Gleicher, M. (2014). Error bars considered harmful: Exploring alternate encodings for mean and error. *IEEE Transactions on Visualization and Computer Graphics, 20*(12), 2142–2151. <https://vis.mit.edu/classes/6.859/readings/pdfs/Corell-ErrorBarsConsideredHarmful.pdf>

Fernandes, M., Walls, L., Munson, S., Hullman, J., & Kay, M. (2018). Uncertainty displays using quantile dotplots or CDFs improve transit decision-making. *Proceedings of ACM CHI*. <https://idl.uw.edu/papers/uncertainty-bus>

Flanagan, H. (2016). *Requirements for plain-text RFCs* (RFC 7994). RFC Editor. <https://www.rfc-editor.org/rfc/rfc7994.html>

Fogwill, M., & Manataki, A. (2024). Interactive data comics for communicating medical data to the general public: A study of engagement and ease of understanding. *Computers and Graphics, 124*, 104055. <https://research-repository.st-andrews.ac.uk/handle/10023/30818>

Gordon, J., Martinelli, S., & Fargetta, M. (2015, May 11). *[openstack-dev] [nova][all] Architecture diagrams in ascii art?* OpenStack-dev mailing list. <https://lists.openstack.org/pipermail/openstack-dev/2015-May/063906.html>

Grabmeier, J. (2005, October 9). *Students learn better when the numbers don't talk and dance*. Ohio State News. <https://news.osu.edu/students-learn-better-when-the-numbers-dont-talk-and-dance/>

Grudin, J., Gupta, A., He, L., & Sanocki, E. (1999). *Comparing presentation summaries: Slides vs. reading vs. listening* (MSR-TR-99-68). Microsoft Research. <https://www.microsoft.com/en-us/research/?p=152399>

Guo, D., Zhang, S., Wright, K. L., & McTigue, E. M. (2020). Do you get the picture? A meta-analysis of the effect of graphics on reading comprehension. *AERA Open, 6*(1). <https://experts.boisestate.edu/en/publications/do-you-get-the-picture-a-meta-analysis-of-the-effect-of-graphics--3/>

Heer, J., Bostock, M., & Ogievetsky, V. (2010). A tour through the visualization zoo. *Communications of the ACM, 53*(6). <https://homes.cs.washington.edu/~jheer/files/zoo/>

Heer, J., & Robertson, G. G. (2007). Animated transitions in statistical data graphics. *IEEE Transactions on Visualization and Computer Graphics*. <https://homes.cs.washington.edu/~jheer/files/2007-AnimatedTrans-InfoVis.pdf>

Heiberger, R., & Robbins, N. (2014). Design of diverging stacked bar charts for Likert scales and other applications. *Journal of Statistical Software, 57*(5). <https://www.jstatsoft.org/article/view/v057i05>

Hoffberg, A. S., Huggins, J., Cobb, A., Forster, J. E., & Bahraini, N. (2020). Beyond journals: Visual abstracts promote wider suicide prevention research dissemination and engagement: A randomized crossover trial. *Frontiers in Research Metrics and Analytics, 5*, 564193. <https://www.frontiersin.org/articles/10.3389/frma.2020.564193/pdf>

Hu, L., Chen, G., Li, P., & Huang, J. (2021). Multimedia effect in problem solving: A meta-analysis. *Educational Psychology Review, 33*(4), 1717–1747. <https://repository.eduhk.hk/en/publications/multimedia-effect-in-problem-solving-a-meta-analysis-2/>

Huang, S., Liu, L., He, J., & Gilpin, L. H. (2026). *Learning to draw ASCII improves spatial reasoning in language models*. arXiv. <https://arxiv.org/html/2604.14641v1>

Hullman, J., Drucker, S., Henry Riche, N., Lee, B., Fisher, D., & Adar, E. (2013). A deeper understanding of sequence in narrative visualization. *IEEE Transactions on Visualization and Computer Graphics, 19*(12), 2406–2415. <https://mucollective.northwestern.edu/files/2013-StorySequence-InfoVis.pdf>

Isaacs, K. E., & Gamblin, T. (2019). *Preserving command line workflow for a package management system using ASCII DAG visualization*. arXiv. <https://arxiv.org/abs/1908.07544>

Kay, M., & Heer, J. (2016). Beyond Weber's law: A second look at ranking visualizations of correlation. *IEEE Transactions on Visualization and Computer Graphics*. <https://idl.uw.edu/papers/beyond-webers-law>

Kearns, C., Eathorne, A., Kearns, N., Anderson, A., Hatter, L., Semprini, A., & Beasley, R. (2022). How best to share research with study participants? A randomised crossover trial comparing a comic, lay summary, and scientific abstract. *Journal of Visual Communication in Medicine, 45*(3), 172–181. <https://researchers.westernsydney.edu.au/en/publications/how-best-to-share-research-with-study-participants-a-randomised-c/>

Kim, A. H., Vaughn, S., et al. (2004). Graphic organizers and their effects on the reading comprehension of students with LD: A synthesis of research. *Journal of Learning Disabilities, 37*(2), 105–118. Summary at ASHA Evidence Maps. <https://apps.asha.org/EvidenceMaps/Articles/ArticleSummary/2adb162a-fdaf-4f8e-8c09-9f9839b6600b>

Knaflic, C. N. (2013, June). *The slideument*. Storytelling with Data. <https://www.storytellingwithdata.com/blog/2013/06/the-slideument>

Larkin, J. H., & Simon, H. A. (1987). Why a diagram is (sometimes) worth ten thousand words. *Cognitive Science, 11*, 65–99. <https://aitopics.org/doc/classics:3E6A7CA6>

leboiko. (2026). *mermaid-text 0.9.7*. docs.rs. <https://docs.rs/crate/mermaid-text/0.9.7>

Lengler, R., & Eppler, M. J. (2007). Towards a periodic table of visualization methods for management. In *Proceedings of the IASTED Conference on Graphics and Visualization in Engineering (GVE 2007)*. <https://www.visual-literacy.org/periodic_table/periodic_table.pdf>

Lorch, R. F., Lemarié, J., & Chen, H. T. (2013). Signaling topic structure via headings or preview sentences. *Psicología Educativa, 19*(2), 59–66. <https://scholars.uky.edu/en/publications/signaling-topic-structure-via-headings-or-preview-sentences/>

Mar, R. A., Li, J., Nguyen, A. T. P., & Ta, C. P. (2021). Memory and comprehension of narrative versus expository texts: A meta-analysis. *Psychonomic Bulletin & Review, 28*(3), 732–749. <https://pmc.ncbi.nlm.nih.gov/articles/PMC8219577/>

Méndez, G. G., & Such, J. (2026). *Scrollytelling as an alternative format for privacy policies*. arXiv. <https://arxiv.org/abs/2603.04367>

Menendez, D., Rosengren, K. S., & Alibali, M. W. (2020). Do details bug you? Effects of perceptual richness in learning about biological change. *Applied Cognitive Psychology, 34*(5). <https://ecrhub.org/publications/do-details-bug-you-effects-perceptual-richness-learning-about-biological-change>

Mensink, M. C., Kendeou, P., & Rapp, D. N. (2021). Do different kinds of introductions influence comprehension and memory for scientific explanations? *Discourse Processes, 58*(5–6), 491–512. <https://experts.umn.edu/en/publications/do-different-kinds-of-introductions-influence-comprehension-and-m/>

Minto, B. (n.d.). *Barbara Minto*. <https://barbaraminto.com/>

Moulton, S. T., Turkay, S., & Kosslyn, S. M. (2017). Does a presentation's medium affect its message? PowerPoint, Prezi, and oral presentations. *PLOS ONE*. <https://pmc.ncbi.nlm.nih.gov/articles/PMC5497950/>

Nebel, C. (2017, November 2). *Are prequestions useful?* The Learning Scientists. <https://www.learningscientists.org/blog/2017/11/2-1>

Nesbit, J. C., & Adesope, O. O. (2006). Learning with concept and knowledge maps: A meta-analysis. *Review of Educational Research, 76*(3), 413–448. <https://sfu.ca/~jcnesbit/articles/nesbitadesope2006.htm>

Obie, H., Chua, C., Avazpour, I., Abdelrazek, M., Grundy, J., & Bednarz, T. (2020). A study of the effects of narration on comprehension and memorability of visualisations. *Journal of Computer Languages*. <https://conf.researchr.org/details/vlhcc2020/vlhcc2020-journal-first/1/A-Study-of-the-Effects-of-Narration-on-Comprehension-and-Memorability-of-Visualisatio>

Okoe, M., Jianu, R., & Kobourov, S. (2017). *Revisited experimental comparison of node-link and matrix representations*. arXiv. <https://ar5iv.labs.arxiv.org/html/1709.00293>

Pang, W., Lin, K. Q., Jian, X., He, X., & Torr, P. (2025). *Paper2Poster: Towards multimodal poster automation from scientific papers*. arXiv. <https://arxiv.org/html/2505.21497v2>

Peebles, D., & Ali, N. (2015). Expert interpretation of bar and line graphs: The role of graphicacy in reducing the effect of graph format. *Frontiers in Psychology*. <https://www.frontiersin.org/articles/10.3389/fpsyg.2015.01673/pdf>

Pferschy-Wenzig, E.-M., Pferschy, U., Wang, D., Mocan, A., & Atanasov, A. G. (2016). Does a graphical abstract bring more visibility to your paper? *Molecules, 21*(9), 1247. <https://pmc.ncbi.nlm.nih.gov/articles/PMC5283664>

Ponce-Arias, H., Mendez, E., et al. (2025). Learner-generated and instructor-provided graphic organizers as aids to learning from text: A meta-analysis. *Educational Psychology Review*. <https://sic.usach.cl/entities/publication/1956e0a0-00ad-48dd-ac59-23a29333d778>

Ramirez, A. D., & Gilmartin, P. (1996). Maps, text, and seventh-graders: A study of spatial learning. *Cartographic Perspectives, 24*. <https://cartographicperspectives.org/index.php/journal/article/view/cp24-ramirez-gilmartin>

Segel, E., & Heer, J. (2010). Narrative visualization: Telling stories with data. *IEEE Transactions on Visualization and Computer Graphics*. <https://homes.cs.washington.edu/~jheer/files/narrative.pdf>

Shneiderman, B. (1996). *The eyes have it: A task by data type taxonomy for information visualizations* (CS-TR-3665). University of Maryland. <https://webspace.science.uu.nl/~telea001/uploads/VACourse/Shneiderman96.pdf>

Soares, S. P., Gonçalves, M., Jerónimo, R., & Kolinsky, R. (2023). Narrating science: Can it benefit science learning, and how? A theoretical review. *Journal of Research in Science Teaching, 60*(9), 2042–2075. <https://ciencia.iscte-iul.pt/publications/narrating-science-can-it-benefit-science-learning-and-how-a-theoretical-review/94695>

Spires, H. A., Gallini, J., & Riggsbee, J. (1992). Effects of schema-based and text structure-based cues on expository prose comprehension in fourth graders. *Journal of Experimental Education, 60*(4), 307–320. <https://scholars.duke.edu/publication/909719>

Stapleton, G., Chapman, P., Rodgers, P., Touloumis, A., Blake, A., & Delaney, A. (2019). The efficacy of Euler diagrams and linear diagrams for visualizing set cardinality using proportions and numbers. *PLoS One, 14*(3), e0211234. <https://pmc.ncbi.nlm.nih.gov/articles/PMC6438608>

Thompson, C. (2003, December 14). PowerPoint makes you dumb. *The New York Times*. <https://courses.ischool.berkeley.edu/i247/s04/resources/powerpoint-nytimes.html>

Tufte, E. R. (n.d.). *The cognitive style of PowerPoint: Pitching out corrupts within*. Graphics Press. <https://www.edwardtufte.com/?p=579>

Wang, Z., Wang, S., Farinella, M., Murray-Rust, D., Henry Riche, N., & Bach, B. (2019). Comparing effectiveness and engagement of data comics and infographics. *Proceedings of CHI 2019*. ACM. <https://research.tudelft.nl/en/publications/comparing-effectiveness-and-engagement-of-data-comics-and-infogra>

Watson, A. (2020, October 13). *"Rich" or "bland": Which diagrams helps students learn deeply?* Learning & the Brain. <https://www.learningandthebrain.com/blog/rich-or-bland-which-diagrams-helps-students-learn-deeply/>

Wikipedia contributors. (n.d.). *Expertise reversal effect*. Wikipedia. Retrieved November 8, 2026, from <https://en.wikipedia.org/wiki/Expertise_reversal_effect>

Winkelman, R. (n.d.). *Photo or illustration?* Florida Center for Instructional Technology. <https://fcit.usf.edu/photo-or-illustration/>

Woodburn, L., Yang, Y., & Marriott, K. (2019). *Interactive visualisation of hierarchical quantitative data: An evaluation*. arXiv. <https://ar5iv.labs.arxiv.org/html/1908.01277>

Zaske, S. (2020, March 19). *Seductive details inhibit learning*. WSU News. <https://news.wsu.edu/2020/03/19/seductive-details-inhibit-learning/>

Zhao, Y., Michal, A., Thain, N., & Subramonyam, H. (2025). *Thinking like a scientist: Can interactive simulations foster critical AI literacy?* arXiv. <https://arxiv.org/html/2507.21090v1>

Zheng, H., Guan, X., Kong, H., Zheng, J., Zhou, W., Lin, H., Lu, Y., He, B., Han, X., & Sun, L. (2025). *PPTAgent: Generating and evaluating presentations beyond text-to-slides*. arXiv. <https://arxiv.org/html/2501.03936v3>

Zhi, Q., Ottley, A., & Metoyer, R. (2019). Linking and layout: Exploring the integration of text and visualization in storytelling. *Computer Graphics Forum, 38*(3), 675–685. <https://profiles.wustl.edu/en/publications/linking-and-layout-exploring-the-integration-of-text-and-visualiz/>
