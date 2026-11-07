# Visual representation of information: When and how an AI agent should show information visually

Research findings for a future skill  
Prepared for Nicolas · Search date: 7 November 2026

The evidence supports a skill built on four rules. Add a visual only when it does something prose cannot. Choose the visual by the reader's task. Put labels and text next to what they describe. Check generated chart or diagram code before showing it. The strongest support is for visuals in learning, from meta-analyses. Support for choosing between prose, a table and a chart is mostly design guidance, not experiments. No controlled study tests how people use visual answers from AI assistants.

**Scope.** This report covers four meanings of the topic:

1. Data visualization: charts and plots of quantitative data, and how people perceive them.
2. Information design: diagrams, tables, flowcharts and timelines that show structure, process or relationships.
3. Cognition and learning: whether and when visuals improve understanding and recall compared with text.
4. AI agent output: when and how an AI agent should present information visually instead of as prose.

**Status.** The research stopped at the `medium` level: no high- or medium-priority question is still open. Two questions are contested and one was not found (section 7). The research board is in `.research/visual-representation-of-information/`. I checked 37 of its 68 claims against their pages, including every claim behind the rules in section 1.

## 1. Rules the evidence supports

| Candidate rule | Evidence | Strength |
|---|---|---|
| **Add a graphic when the reader must understand or learn from text** | A meta-analysis found graphics improved reading comprehension, with a moderate effect of g = 0.39 at all grade levels. Pictures, pictorial diagrams and flow diagrams did not differ significantly (Guo et al., 2020). | Strong: meta-analysis |
| **Use a diagram when the content is about relations between items** | Diagrams group information in space, which reduces how much the reader must search (Larkin & Simon, 1987). | Moderate: classic paper, read only as an abstract |
| **Use prose for one or two numbers** | "When you have just a number or two," plain text beats a table or graph (Nussbaumer, n.d.). | Weak: one practitioner source, no experiments |
| **Use a table for exact values and a chart for trends** | Tables show specific values and charts show trends and patterns (UBC Wiki, 2021). Don't use a chart when a table is enough, and put the chart's data in a table below it (Canada.ca Experience Office, 2018). | Moderate: consistent guidance, no experiments |
| **Put labels and explanations next to what they explain** | A meta-analysis found d = 0.85 for placing related text and pictures close together. The effect was large for complex material (d = 0.78) and small and non-significant for simple material (d = 0.28) (Ginns, 2006, as reported in Beege et al., 2019). | Strong, but read through a secondary report |
| **Don't add decoration** | Irrelevant "seductive details" hurt learning overall. Decorative pictures alone had no significant effect, so the harm depends on format (Sundararajan & Adesope, 2020, as reported in Désiron & Schneider, 2024). | Moderate |
| **Don't truncate the axis on a bar chart without a reason** | A y-axis that doesn't start at zero exaggerates effects, but truncation can be justified by the chart's purpose (Correll et al., 2020). | Moderate |
| **Encode the main comparison as position on a common scale** | In the Cleveland and McGill ranking, position on a common scale is read most accurately and colour saturation least accurately (Soltoff, 2026). | **Contested**: see section 5 |
| **Give each arrow and line one stated meaning** | Biology textbooks use arrow styles with no consistent meaning. Few styles had a meaning readers understood without explanation. All 14 students interviewed were at least somewhat confused by arrows (Wright et al., 2018). | Moderate: one field |
| **Don't use colour as the only signal, and give charts a text description** | Colour cannot be the only means of conveying information (W3C WAI, 2025). Graphic parts needed to understand the content need 3:1 contrast against adjacent colours (W3C WAI, n.d.). Charts need a short and a long text description (Eggert & Abou-Zahra, 2026). | Strong: W3C standard |
| **Check generated chart code before showing it** | LLM chart code fails through wrong or non-existent API calls and through misreading the data table (Chen et al., 2024). Giving the model a summary of the data lowered errors (Dibia, 2023). | Moderate: models from 2023 to 2025 |
| **Offer a table when comparing several items** | In the Graphologue study, users with LLM answers turned into diagrams said they got information faster. They also found whole diagrams "a little intimidating", and the authors note a table can be clearer for comparisons (Jiang et al., 2023). | Weak: 7 participants |

## 2. Choosing between prose, a table, a chart and a diagram

Sources split the choice by what the reader must do with the information:

| Reader's task | Format | Source |
|---|---|---|
| Take in one or two numbers | Prose | Nussbaumer (n.d.) |
| Look up or compare exact values | Table | UBC Wiki (2021); Canada.ca Experience Office (2018) |
| See a trend or pattern across many values | Chart, with its data in a table | UBC Wiki (2021); Canada.ca Experience Office (2018) |
| Understand relations, structure or a process | Diagram | Larkin & Simon (1987) |
| Compare several items on several aspects | Table | Jiang et al. (2023) |

Kastellec and Leoni (2007) argue that graphs present regression results more clearly than tables, so the choice between a table and a chart also depends on the field's conventions. **No source gives an experimental test for deciding that a visual isn't needed.**

## 3. Visuals and understanding

### 3.1 Graphics help comprehension

Adding graphics to text improved reading comprehension, with g = 0.39, and the type of graphic made no significant difference (Guo et al., 2020). An older review reached the same direction: carefully constructed illustrations generally help learning from text (Carney & Levin, 2002). Animation helped slightly more than static graphics (g = 0.226), and more when no text accompanied it (Berney & Betrancourt, 2016).

### 3.2 Placement matters more for complex material

Placing related text and pictures close together had a large effect (d = 0.85) in Ginns's (2006) meta-analysis, as reported by Beege et al. (2019). The effect was large for complex material (d = 0.78) and small and non-significant for simple material (d = 0.28). The recommendation is to keep related representations close to each other.

**Redundancy is unresolved.** No readable source gave an effect size or a tested rule for repeating the same content as both text and diagram.

### 3.3 Decoration and misleading charts

Irrelevant details hurt learning overall when they were audio or text-and-picture, but decorative pictures alone had no significant effect (Désiron & Schneider, 2024, summarizing Sundararajan & Adesope, 2020). Truncated bar-chart axes exaggerate effects, even when the truncation is marked. Truncation can still be justified by the chart's purpose (Correll et al., 2020).

### 3.4 Reader expertise

Text built into a diagram reportedly helps novices, while experts did better with the diagram alone. Information that a novice needs can be redundant for an expert (Kalyuga et al., 2003, as summarized by Cobb, 2021). **This rests on one blog summary**; the primary papers were blocked.

## 4. Designing diagrams and charts

### 4.1 Diagrams

Diagrams help because they group information in space and reduce search (Larkin & Simon, 1987). People draw with a small set of schematic figures (lines, blobs, crosses and arrows) whose meaning depends on context. Readers usually interpret them correctly in context (Tversky et al., 2000).

Arrows are the documented source of ambiguity. Biology textbooks use many arrow styles with no consistent meaning, and few styles had an intrinsic meaning for readers (Wright et al., 2018). Practitioner guidance adds conventions without evidence: one flow direction per flowchart, room for branch labels, minimal text in images, and no images added only for decoration (Nishadha, 2024; Acas, 2026).

### 4.2 Charts

The Cleveland and McGill (1984) ranking orders encodings by how accurately people read them (Soltoff, 2026):

1. Position along a common scale
2. Position along non-aligned scales
3. Length, direction, angle
4. Area
5. Volume, curvature
6. Shading, colour saturation

Heer and Bostock (2010) replicated these studies on Mechanical Turk and extended them to area judgments. Section 5 lists the challenges to the ranking.

### 4.3 Accessibility

- Colour cannot be the only visual means of conveying information (W3C WAI, 2025).
- Parts of a graphic needed to understand it need 3:1 contrast against adjacent colours (W3C WAI, n.d.).
- Complex images such as charts and flowcharts need a two-part text alternative. The first part is a short description that identifies the image. The second is a long description of the essential information (Eggert & Abou-Zahra, 2026).

## 5. Where sources disagree

- **The encoding ranking is a rough guide, not a rule.** Effectiveness varies with the task and the type of data (Saket et al., 2018). Some individuals deviate from the ranking (Davis et al., 2022). A 2026 preprint argues that small changes to the data or the design can shift perception, so the ranking method is "fundamentally flawed" (Reda et al., 2026).
- **Decorated charts versus minimal charts.** Decorated charts were remembered better weeks later, but the study did not test reading exact values (Kosara, 2010). An EU guide recommends minimal design for reading values and rich design for engagement (data.europa.eu, 2023).
- **Pie charts.** Kosara (2011) reads Spence and Lewandowsky's study as showing pie charts roughly equal to bar charts. Few (2013) says bar charts beat pie charts on every task except comparing summed parts. Both read the same study, and I did not read that study.

## 6. AI agents and visual output

### 6.1 How users respond to visual answers

In a formative study with 10 participants, users found LLM text answers lacking a visual hierarchy. In the Graphologue evaluation with 7 experienced users, diagrams helped them see connections and get information faster. Users also reported scrolling, intimidating whole diagrams, distracting animation and latency (Jiang et al., 2023).

In Chatbot Arena votes, answer length mattered more than Markdown lists, headers or bold. The authors note the analysis is observational and measures preference, not comprehension (Li et al., 2024).

### 6.2 How well LLMs generate charts and diagrams

LLMs mostly generate charts as code, such as Matplotlib, Seaborn or Vega-Lite. VisEval scores generated charts for validity, legality and readability (Chen et al., 2024). It found these errors:

- **Invalid code**: wrong API calls or calls to APIs that don't exist.
- **Wrong data transformations**: mostly from misunderstanding the data table.
- **Readability faults.**

Error rates depend on how they are measured. LIDA reports 3.5%, but counts only code that fails to compile. Giving the model a data summary lowered its errors compared with field names alone (Dibia, 2023). A Mermaid sequence-diagram benchmark scores outputs with LLM judges whose strictness differs, so its absolute scores depend on the judge. Larger models did better than smaller ones in the same family (Shbita et al., 2025).

**These results come from 2023–2025 models and may be out of date.**

### 6.3 Text-only and terminal environments

Only practitioner sources were found. One example of a simple diagram cost about 55 tokens as ASCII and 10 as Mermaid, but Mermaid needs a renderer and is hard to read as raw text when complex (Michelini, n.d.). Codex CLI turns wide tables into stacked records in narrow terminals rather than wrapping the grid (Schmalbach, 2026).

## 7. What the research could not find

| Gap | Effect on the skill |
|---|---|
| No controlled study compares prose, table and diagram answers from AI assistants (four searches) | Rules on agent output rest on general findings and one 7-person study |
| No readability study of ASCII diagrams, Mermaid or Markdown tables in terminals | Terminal rules rest on practitioner posts |
| No tested rule for when prose is better than a visual | "Prose for one or two numbers" rests on one source |
| No readable evidence on the redundancy effect | The skill can't yet say when to repeat content in text and visual |
| Primary texts unread: Cleveland & McGill (1984), Heer & Bostock (2010) in full, Tversky et al. (2002), Kalyuga et al. (2003), Chandler & Sweller (1991) | Reading them could settle the encoding ranking and the expertise effect |
| No source defined "information design" | Terminology only; no effect on the rules |

## 8. Method

Five worker agents, plus three replacements, researched 16 questions on a shared board. A coordinator reviewed their entries, merged duplicates, and reopened questions closed without enough searches. Each source records whether it was read as full text, as an extraction or as a snippet. Most pages were read through a fetch tool's extraction. Those tools sometimes returned summaries that said a quote was missing when the verbatim text contained it, so quotes were checked against the verbatim text.

## 9. References

Acas. (2026). *Charts and diagrams: Guidelines for Acas reports*. <https://acas.org.uk/report-guidelines/charts-and-diagrams>

Beege, M., Wirzberger, M., Nebel, S., Schneider, S., Schmidt, N., & Rey, G. D. (2019). Spatial continuity effect vs. spatial contiguity failure. Revising the effects of spatial proximity between related and unrelated representations. *Frontiers in Education, 4*. <https://www.frontiersin.org/articles/10.3389/feduc.2019.00086/full>

Berney, S., & Betrancourt, M. (2016). Does animation enhance learning? A meta-analysis. *Computers and Education, 101*, 150–167. <https://archive-ouverte.unige.ch/unige:92234>

Canada.ca Experience Office. (2018). *Charts and graphs design pattern*. Canada.ca Design. <https://design.canada.ca/common-design-patterns/charts-graphs.html>

Carney, R. N., & Levin, J. R. (2002). Pictorial illustrations still improve students' learning from text. *Educational Psychology Review, 14*(1), 5–26. <https://bearworks.missouristate.edu/articles-chhs/956>

Chen, N., Zhang, Y., Xu, J., Ren, K., & Yang, Y. (2024). *VisEval: A benchmark for data visualization in the era of large language models*. arXiv. <https://arxiv.org/html/2407.00981v2>

Cobb, R. (2021). *The expertise reversal effect (2003)*. CS Education. <https://csed.substack.com/p/the-expertise-reversal-effect-2003>

Correll, M., Bertini, E., & Franconeri, S. (2020). *Truncating the y-axis: Threat or menace?* arXiv. <https://arxiv.org/abs/1907.02035>

data.europa.eu. (2023). *Chart junk and data ink: Minimalistic vs rich design*. Data Visualisation Guide. <https://data.europa.eu/apps/data-visualisation-guide/chart-junk-and-data-ink-minimalistic-vs-rich-design>

Davis, R., Pu, X., Ding, Y., Hall, B. D., Bonilla, K., Feng, M., Kay, M., & Harrison, L. (2022). The risks of ranking: Revisiting graphical perception to model individual differences in visualization performance. *IEEE Transactions on Visualization and Computer Graphics*. <https://arxiv.org/abs/2212.10533>

Désiron, J. C., & Schneider, S. (2024). Exploring the interplay of information relevance and colorfulness in multimedia learning. *Frontiers in Psychology, 15*. <https://frontiersin.org/articles/10.3389/fpsyg.2024.1393113/full>

Dibia, V. (2023). *LIDA: A tool for automatic generation of grammar-agnostic visualizations and infographics using large language models*. arXiv. <https://ar5iv.labs.arxiv.org/html/2303.02927>

Eggert, E., & Abou-Zahra, S. (2026). *Complex images*. W3C Web Accessibility Initiative. <https://www.w3.org/WAI/tutorials/images/complex/>

Few, S. (2013). *A pie in the face for information visualization research*. Perceptual Edge. <https://www.perceptualedge.com/blog/?p=1492>

Guo, D., Zhang, S., Wright, K. L., & McTigue, E. M. (2020). Do you get the picture? A meta-analysis of the effect of graphics on reading comprehension. *AERA Open, 6*(1). <https://experts.boisestate.edu/en/publications/do-you-get-the-picture-a-meta-analysis-of-the-effect-of-graphics--3/>

Heer, J., & Bostock, M. (2010). Crowdsourcing graphical perception: Using Mechanical Turk to assess visualization design. *Proceedings of the ACM Conference on Human Factors in Computing Systems (CHI)*, 203–212. <https://idl.uw.edu/papers/crowdsourcing-graphical-perception>

Jiang, P., Rayan, J., Dow, S. P., & Xia, H. (2023). Graphologue: Exploring large language model responses with interactive diagrams. *UIST '23*. <https://ar5iv.labs.arxiv.org/html/2305.11473>

Kastellec, J. P., & Leoni, E. L. (2007). Using graphs instead of tables in political science. *Perspectives on Politics*. <https://cambridge.org/core/journals/perspectives-on-politics/article/using-graphs-instead-of-tables-in-political-science/9FD63E9EE686AF046732191EE8A68034>

Kosara, R. (2010). *Chart junk considered useful after all*. eagereyes. <https://eagereyes.org/blog/2010/chart-junk-considered-useful-after-all>

Kosara, R. (2011). *In defense of pie charts*. eagereyes. <https://eagereyes.org/blog/2011/in-defense-of-pie-charts>

Larkin, J. H., & Simon, H. A. (1987). Why a diagram is (sometimes) worth ten thousand words. *Cognitive Science, 11*, 65–99. <https://serc.carleton.edu/resources/961.html>

Li, T., Angelopoulos, A., & Chiang, W.-L. (2024). *Does style matter? Disentangling style and substance in Chatbot Arena*. LMSYS Org. <https://www.lmsys.org/blog/2024-08-28-style-control>

Michelini, A. (n.d.). *Why Mermaid is the best way to document your architecture in the AI era*. DEV Community. <https://dev.to/darkmavis1980/why-mermaid-is-the-best-way-to-document-your-architecture-in-the-ai-era-2dgb>

Nussbaumer, C. (n.d.). *The power of simple text*. storytelling with data. <https://www.storytellingwithdata.com/blog/2012/06/power-of-simple-text>

Nishadha. (2024). *Part 1: 15 mistakes you would unintentionally make with flowcharts*. Creately Blog. <https://creately.com/blog/diagrams/part-1-15-mistakes-you-would-unintentionally-make-with-flowcharts/>

Reda, K., Sharma, S., Renambot, L., Miranda, F., & Boorboor, S. (2026). *Marks, channels, and dead ends: Stop running graphical perception studies and start modeling visualizations as images*. arXiv. <https://arxiv.org/abs/2608.07834>

Saket, B., Endert, A., & Demiralp, Ç. (2018). *Task-based effectiveness of basic visualizations*. arXiv. <https://arxiv.org/abs/1709.08546>

Schmalbach, V. (2026). *Codex CLI has responsive tables in the terminal*. <https://www.vincentschmalbach.com/codex-cli-responsive-terminal-tables/>

Shbita, B., Ahmed, F., & DeLuca, C. (2025). *MermaidSeqBench: An evaluation benchmark for LLM-to-Mermaid sequence diagram generation*. arXiv. <https://arxiv.org/html/2511.14967v1>

Soltoff, B. (2026). *Graphical perception + layers* [Course slides]. Cornell University. <https://info3312.infosci.cornell.edu/slides/04-graphical-perception.html>

Tversky, B., Zacks, J., Lee, P., & Heiser, J. (2000). Lines, blobs, crosses and arrows: Diagrammatic communication with schematic figures. In *Theory and Application of Diagrams (Diagrams 2000)*, LNCS 1889, 221–230. Springer. <https://profiles.wustl.edu/en/publications/lines-blobs-crosses-and-arrows-diagrammatic-communication-with-sc/>

UBC Wiki. (2021). *Producing effective tables and figures/Deciding whether to use tables or figures*. <https://wiki.ubc.ca/Producing_Effective_Tables_and_Figures/Deciding_whether_to_use_tables_or_figures>

W3C Web Accessibility Initiative. (n.d.). *Understanding success criterion 1.4.11: Non-text contrast*. W3C. <https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html>

W3C Web Accessibility Initiative. (2025). *Understanding success criterion 1.4.1: Use of color*. W3C. <https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html>

Wright, L. K., Cardenas, J. J., Liang, P., & Newman, D. L. (2018). Arrows in biology: Lack of clarity and consistency points to confusion for learners. *CBE—Life Sciences Education, 17*(1), ar6. <https://pmc.ncbi.nlm.nih.gov/articles/PMC6007777>

**Bibliographic notes.** The fetch tool did not return the date of the non-text contrast page verbatim, so it is cited as n.d. The storytelling with data post shows "Jun 17" without a year; its URL contains 2012/06.
