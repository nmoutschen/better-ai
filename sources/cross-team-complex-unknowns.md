# Resolving and building knowledge around complex unknowns across multiple teams

Research register · Search date: 11 November 2026

**Scope.** Two meanings, combined: (1) how several human teams in an organization make sense of a problem that no single team understands, and build shared knowledge about it; (2) the engineering practices used for cross-team unknowns (spikes, RFCs and design docs, architecture decision records, post-incident reviews, large-scale agile coordination) and the evidence on their effects. Exhaustive review: questions of every priority were researched.

**Status.** 25 questions closed: 22 answered, 3 contested. 64 sources in English, French and German. Of 116 quoted claims, 113 were confirmed on the source page; three could not be checked because their sites block downloads, and the text marks each one. Many sources could only be read as abstracts, and the text says so for each one.

**Main result.** The research agrees that **the work between teams is the weak point, and strength inside each team does not carry across** (Mathieu et al., 2018; Shuffler & Carter, 2018; Bienefeld & Grote, 2014). It does not show which practices fix this. **No study found measures how RFCs, decision records or post-incident reviews affect knowledge across teams.** Most evidence describes practices, comes from student lab tasks, or comes from practitioner write-ups.

## 1. Terms

| Term | What it names | Source |
|---|---|---|
| Multiteam system (MTS) | Two or more teams that depend on each other and share a distant goal | Mathieu et al. (2018) |
| Wicked problem | A problem that cannot be stated once and for all. Each team's framing of it differs. | Rittel & Webber (1973) |
| Sensemaking | The process by which people turn confusing circumstances into a situation they understand | Weick et al. (2005) |
| Knowledge boundaries | What blocks knowledge between specialties, at three levels: shared syntax (vocabulary), meaning, and conflicting interests ("pragmatic") | Carlile (2002); Kotlarsky et al. (n.d.) |
| Transactive memory | A shared map of "who knows what" | Lewis & Herndon (2011) |

## 2. Findings from organizational and team research

### 2.1. Coordination between teams predicts multiteam system performance

- Processes between teams predict system performance beyond processes inside each team (Mathieu et al., 2018; DeChurch & Marks, 2006). These processes are coordination, boundary spanning (members who link their team to others), leadership, and knowing who knows what.
- Inside-team strengths can backfire. "Empowering component teams and developing cohesion may help teams but hurt MTS performance." Training aimed only at skills inside each team "will not necessarily improve overall system performance" (Shuffler & Carter, 2018).
- Limits: most causal evidence comes from lab simulations with students. Findings on coordination vary in strength and sometimes in direction (Mathieu et al., 2018). Shuffler et al. (2018) argue that the research wrongly treats component teams as all alike.
- A 2025 meta-analysis dissertation (Wentworth, 2025; abstract only) separates findings by level. Feelings and behaviours inside teams relate most to each team's effectiveness. Shared thinking inside teams relates most to the effectiveness of the whole system.

### 2.2. Shared sensemaking fails when teams judge success by different criteria

- In the Columbia shuttle case, safety and schedule criteria split the organization into competing groups, each with its own reading of the foam-strike anomaly. The result was no action (Dunbar & Garud, 2009).
- An interview study of the Utrecht attack response names hierarchy, team identity, and too little doubt or too few viewpoints as causes of failure (Wolbers, 2021; abstract only).
- Fixes proposed in the sources:
  - A standing cross-unit pilot team, set up before the work starts (NUMMI; Adler et al., 1999, as discussed by Dunbar & Garud, 2009).
  - An independent technical authority (Columbia Accident Investigation Board, 2003). The quote could not be checked on the page.
- Nobody has measured whether either fix reduces deadlock. After Columbia, the oversight task group reported that NASA had completed 12 of 15 safety improvements. Seven of its members dissented: "more people were talking, but not many more were listening" (Kestenbaum, 2005). GAO (2017) found that NASA's technical authorities were subject to cost and schedule pressures that potentially impaired their independence. That quote could not be checked either.

### 2.3. Shaping the problem together comes before solving it

- Diverse teams tend to narrow how they formulate a problem too early. Baer et al. (2013; abstract only) propose a structured process that keeps the formulation broad.
- In one experiment with student teams, working on the problem statement first raised originality and lowered conflict (Reiter-Palmon & Murugavel, 2018).
- External experts help teams reframe a problem by reshaping what the team already knows. This comes from an ethnography of four innovation projects (Bellis et al., 2026), read only via a summary page.
- French management research treats the problem itself as something built together. In one action-research case, participants held different and shifting views of the problem (Allard-Poesi & Perret, 2004; abstract only). A study of Airbus concurrent-engineering meetings found that specialists used the same constraints with different meanings and weights (Martin et al., 2002).

### 2.4. Integrating knowledge when it is novel

- Each of Carlile's boundary levels needs a more involved process to cross it (Carlile, 2002). In a survey of 174 members of cross-functional teams, syntax and conflicting-interest boundaries held back "who knows what" knowledge (Kotlarsky et al., n.d.).
- For novel problems, Majchrzak et al. (2012; abstract only) observed teams that quickly built shared intermediate "scaffolds". They contrast this with slower deep dialogue between specialties. Bechky (2003; abstract only) shows shared understanding built from concrete shared objects on a production floor.
- "Who knows what" knowledge above the team level is thin. One firm had it inside its business groups but not between them (Houtman et al., n.d.). Meta-analyses at team level find that its link to performance varies by context (Bachrach et al., 2019; Zhou & Pazos, 2020).

### 2.5. Uncertainty changes which coordination works

In a study of 64 software projects, formal top-down coordination reduced risk, while informal mutual adjustment raised performance directly. The two worked best together (Nidumolu, 1995; abstract only). A program of 12 agile teams relied on feedback-based coordination under uncertainty, but the study measured no effects (Dingsøyr et al., 2018).

### 2.6. Psychological safety works inside teams, but not clearly across them

- Psychological safety is a shared belief that it is safe to take interpersonal risks. Inside teams it predicts learning behaviour: asking questions, seeking feedback, and discussing errors (Edmondson, 1999).
- One study of 1,490 aircrew members tested safety across teams. It explained speaking up inside crews, but not across crews (Bienefeld & Grote, 2014). No such cross-team test was found in software or healthcare.

### 2.7. Contested findings: structured dissent and collective intelligence

- **Structured dissent.** Structured dissent methods beat consensus in strategic-decision experiments. These methods are dialectical inquiry (arguing a plan against a counter-plan) and devil's advocacy (one member attacks the plan) (Schweiger & Sandberg, 1989). Which of the two works better is disputed (Schweiger & Finger, 1984). Both sources are abstracts of lab studies.
- **Collective intelligence.** Woolley et al. (2010) report a general group factor that predicts performance across tasks, and Riedl et al. (2021) report the same. A reanalysis found weak support for that factor (Credé & Howardson, 2017). A meta-analysis found r = .26, with most studies underpowered (Rowe et al., 2021). The evidence on collective metacognition (a group monitoring its own thinking) comes only from student learning tasks (Qiao et al., 2024).

### 2.8. Knowledge is lost between temporary projects

Temporary project teams lose knowledge between projects, and lessons-learned databases go unused when projects are novel (Bredell & Tshuma, 2025; Brady et al., 2002). A dataset covering 64 years of Olympic Games showed no lasting cost learning across host committees (Ansar et al., 2026). A German survey of 27 interviews and 495 questionnaires linked culture and knowledge-management infrastructure to project knowledge effectiveness (Frey et al., 2009).

### 2.9. Interdisciplinary research teams

Team-science sources propose phase models for transdisciplinary research (development, conceptualization, implementation, translation) but do not test them (Hall et al., 2012). A 2025 perspective names boundary spanners, epistemic inclusivity and shared mental models as candidate keys, and says it is not known how they work for translational teams (Laursen et al., 2025).

## 3. Findings from engineering practice

Each row is one practice, with the type of evidence behind it and whether any effect was measured.

| Practice | Evidence found | Effect measured? |
|---|---|---|
| RFCs and design docs | Practitioner reports: more transparency and a lasting record. They fail without a shared rule on when to write one (Srivastava, 2026; Thoughtworks, 2023). | No |
| Spikes and proofs of concept | The only empirical study (Al Hashimi et al., 2020) was blocked. | Unknown |
| Architecture decision records (ADRs) | One three-month action study: cooperation between teams improved, and where the records are stored mattered (Ahmeti et al., 2024). Two experiments: recording decision rationale improved understanding of the architecture, with no change in task time (Shahin et al., n.d.). | Single company only |
| Post-incident reviews | Interview studies: learning is informal and shallow. Barriers are defensiveness, staff turnover and scattered documents (Patterson et al., 2024; Anandayuvaraj et al., 2026). One consultancy case: incident libraries are rarely read outside the teams involved (Adaptive Capacity Labs, n.d.). | No |
| Large-scale agile coordination mechanisms | One firm used 27 mechanisms, grouped as meetings (communities of practice included), roles, and tools or artefacts (Berntzen et al., 2023). A review of 69 studies plus interviews names documentation and formal and informal exchange as enablers (Tobisch & Matthes, 2025). Other studies: Moe et al. (2018); Bjørnson et al. (2018). A mapping study says the benefits of communities of practice are still unstudied (Uludağ et al., 2022). | No, descriptive only |
| Exploring before committing | Set-based design (developing several options in parallel and dropping weak ones early) is reviewed as weak in theory (Toche et al., 2020). Experimentation research offers models, not effect tests (Fabijan et al., 2018). | No |

Technical dependencies between teams cause linked problems in planning, information exchange and integration (Sekitoleko et al., 2014; abstract only).

## 4. Where the sources disagree

- Formal coordination versus informal adjustment: complementary in field software projects (Nidumolu, 1995), mixed in lab multiteam studies (Mathieu et al., 2018).
- Deep dialogue versus fast scaffolds for novel knowledge (Majchrzak et al., 2012).
- Collective intelligence: whether the general group factor exists at all (section 2.7).

The differences may come from method and setting: lab students versus field teams, short-lived crews versus long-lived teams, and the assumption that component teams are all alike. **This explanation is an inference. No source tests it.**

## 5. Open questions and gaps

- No study measures how RFCs, design docs, spikes, ADRs or post-incident reviews affect knowledge across teams.
- No test of "who knows what" knowledge or psychological safety across teams outside aviation.
- No evaluation of standing cross-unit teams or a technical authority as fixes for deadlock.
- No French- or German-language full text was read; only English-language papers by French and German authors, and an abstract for the French action-research study.
- Real options and product discovery were not searched (section 3, "Exploring before committing").

Blocked or unread sources that could change these answers:
- Maitlis & Christianson (2014), the standard review of sensemaking.
- The Ostrowski (2022) dissertation on problem framing and the use of expertise.
- The Schwenk (1990) meta-analysis on structured dissent.
- Marks et al. (2005).
- The Al Hashimi spike studies.
- The 2026 studies on ADR adoption and ADR templates.
- The full Carlile (2002) paper and Star & Griesemer's paper on boundary objects.

## 6. Sources

- Adaptive Capacity Labs. (n.d.). *Case: Mid-size e-commerce company (assessment)*. https://www.adaptivecapacitylabs.com/case-mid-size-e-commerce-business/
- Adler, P. S., Goldoftas, B., & Levine, D. I. (1999). Flexibility versus efficiency? A case study of model changeovers in the Toyota production system. *Organization Science, 10*(1), 43–68. https://ideas.repec.org/a/inm/ororsc/v10y1999i1p43-68.html
- Ahmeti, B., Linder, M., Groner, R., & Wohlrab, R. (2024). Architecture decision records in practice: An action research study. *18th European Conference on Software Architecture (ECSA 2024)*. https://rebekkaa.github.io/files/2024_ECSA.pdf
- Al Hashimi, H., Altaleb, A., & Gravell, A. (2020). *An empirical investigation of spikes in agile software development*. ACM. https://eprints.soton.ac.uk/450760
- Allard-Poesi, F., & Perret, V. (2004). La construction collective du problème dans la recherche-action : difficultés, ressorts et enjeux. *Finance Contrôle Stratégie, 7*(4), 5–36. https://ideas.repec.org/a/dij/revfcs/v7y2004iq4p5-36.html
- Anandayuvaraj, D., Lund, A., Singla, T., Holloway, A., Hammadeh, Z. A. H., & Davis, J. C. (2026). *Learning from software failures: A case study at a national space research center* (arXiv:2509.06301v3). arXiv. https://arxiv.org/pdf/2509.06301
- Ansar, A., Flyvbjerg, B., & Budzier, A. (2026). Do projects learn across space and time? Evidence from the Olympics. *Public Management Review*. https://arxiv.org/pdf/2604.17970
- Bachrach, D. G., Lewis, K., Kim, Y., Patel, P. C., Campion, M. C., & Thatcher, S. M. B. (2019). Transactive memory systems in context: A meta-analytic examination of contextual factors in transactive memory systems development and team performance. *Journal of Applied Psychology, 104*(3), 464–493. https://pure.skku.edu/en/publications/transactive-memory-systems-in-context-a-meta-analytic-examination/
- Baer, M., Dirks, K. T., & Nickerson, J. A. (2013). Microfoundations of strategic problem formulation. *Strategic Management Journal, 34*(2), 197–214. https://profiles.wustl.edu/en/publications/microfoundations-of-strategic-problem-formulation/
- Bechky, B. A. (2003). Sharing meaning across occupational communities: The transformation of understanding on a production floor. *Organization Science, 14*(3), 312–330. https://econpapers.repec.org/RePEc:inm:ororsc:v:14:y:2003:i:3:p:312-330
- Bellis, P., Dell'Era, C., & Verganti, R. (2026, March 9). *Reframing through new minds: How external experts unlock problem reframing through reasoning logics* [Summary of article in *Journal of Product Innovation Management, 43*(4)]. PDMA Knowledge Hub. https://community.pdma.org/knowledgehub/bok/strategy/reframing-through-new-minds-how-external-experts-unlock-problem-reframing-through-reasoning-logistic
- Berntzen, M., Hoda, R., Moe, N. B., & Stray, V. (2023). A taxonomy of inter-team coordination mechanisms in large-scale agile. *IEEE Transactions on Software Engineering*. https://doi.org/10.1109/tse.2022.3160873
- Bienefeld, N., & Grote, G. (2014). Speaking up in ad hoc multiteam systems: Individual level effects of psychological safety, status, and leadership within and across teams. *European Journal of Work and Organizational Psychology*. https://cclinnovation.org/wp-content/uploads/2020/04/2014ejwopawardpaper.pdf (Author names come from the search listing; the PDF text shows none.)
- Bjørnson, F. O., Wijnmaalen, J., Stettina, C. J., & Dingsøyr, T. (2018). Inter-team coordination in large-scale agile development: A case study of three enabling mechanisms. In *Lecture Notes in Business Information Processing (XP 2018)*. Springer. https://doi.org/10.1007/978-3-319-91602-6_15
- Brady, T., Marshall, N., Prencipe, A., & Tell, F. (2002, April). *Making sense of learning landscapes in project-based organisations* [Conference paper]. Third European Conference on Organizational Knowledge, Learning and Capabilities, Athens. https://www2.warwick.ac.uk/fac/soc/wbs/conf/olkc/archive/oklc3/id314.pdf
- Bredell, C., & Tshuma, B. (2025). Improving organisational learning in project-based organisations through the translation of project lessons learnt into project risks. *South African Journal of Industrial Engineering, 36*(2), 134–148. https://www.scielo.org.za/pdf/sajie/v36n2/12.pdf
- Carlile, P. (2002). *Transferring, translating and transforming: An integrative framework* [Working paper]. MIT DSpace. https://dspace.mit.edu/handle/1721.1/3813
- Columbia Accident Investigation Board. (2003). *Report of the Columbia Accident Investigation Board, Volume I: Executive summary*. Spaceflight Now. https://spaceflightnow.com/columbia/report/009execsumm.html
- Credé, M., & Howardson, G. (2017). The structure of group task performance—A second look at "collective intelligence": Comment on Woolley et al. (2010). *Journal of Applied Psychology, 102*(10), 1483–1492. https://pubmed.ncbi.nlm.nih.gov/29016184/
- DeChurch, L. A., & Marks, M. A. (2006). Leadership in multiteam systems. *Journal of Applied Psychology, 91*(2), 311–329. https://atlas.northwestern.edu/wp-content/uploads/2017/03/DeChurch-et-al.-2006.pdf
- Dingsøyr, T., Moe, N. B., & Seim, E. A. (2018). Coordinating knowledge work in multi-team programs: Findings from a large-scale agile development program. *Project Management Journal*. https://arxiv.org/pdf/1801.08764
- Dunbar, R. L. M., & Garud, R. (2009). Distributed knowledge and indeterminate meaning: The case of the Columbia shuttle flight. *Organization Studies, 30*(4), 397–421. https://pages.stern.nyu.edu/%7Erdunbar/Articles/distributedknowledgeand.pdf
- Edmondson, A. (1999). Psychological safety and learning behavior in work teams. *Administrative Science Quarterly, 44*(2), 350–383. https://web.mit.edu/curhan/www/docs/Articles/15341_Readings/Group_Performance/Edmondson%20Psychological%20safety.pdf
- Fabijan, A., Dmitriev, P., McFarland, C., Vermeer, L., Holmström Olsson, H., & Bosch, J. (2018). Experimentation growth: Evolving trustworthy A/B testing capabilities in online software companies. *Journal of Software: Evolution and Process, 30*(12), e2113. https://research.chalmers.se/en/publication/508698
- Frey, P., Lindner, F., Müller, A., & Wald, A. (2009). Project knowledge management organizational design and success factors: An empirical study in Germany. In *Proceedings of the 42nd Hawaii International Conference on System Sciences*. https://typeset.io/pdf/project-knowledge-management-organizational-design-and-1imrwzt4i5.pdf
- Hall, K. L., Vogel, A. L., Stipelman, B. A., Stokols, D., Morgan, G., & Gehlert, S. (2012). A four-phase model of transdisciplinary team-based research: Goals, team processes, and strategies. *Translational Behavioral Medicine, 2*, 415–430. https://www.colorado.edu/researchinnovation/sites/default/files/attached-files/hall_et_al_2012_a_.pdf
- Houtman, L., van den Hooff, B., & van Baalen, P. (n.d.). *Knowledge sharing between local work contexts: A multi-method case study* [Conference paper]. OLKC 5. https://text.www2.warwick.ac.uk/fac/soc/wbs/conf/olkc/archive/olkc5/papers/172_houtman_full_paper_315_knowledge_sharing_between_local_work_contexts.pdf
- Kestenbaum, D. (2005, August 18). Report questions some NASA procedures. *Morning Edition*. NPR. https://www.npr.org/2005/08/18/4804924/report-questions-some-nasa-procedures
- Kotlarsky, J., van den Hooff, B., & Houtman, L. (n.d.). *Are we on the same page? Knowledge boundaries and transactive memory system development in cross-functional teams* [Author manuscript]. Aston University. https://publications.aston.ac.uk/id/eprint/20114/2/Knowledge_boundaries_and_transactive_memory_system_development_in_cross_functional_teams.pdf
- Laursen, B. K., AtKisson, M. S., Love, H. B., & Glauber, K. (2025). To advance translational science, remove these roadblocks to studying team knowledge integration. *Journal of Clinical and Translational Science, 9*, e210. https://resolve.cambridge.org/core/services/aop-cambridge-core/content/view/148E3020B7266704BE67907EBA1E2050/S2059866125101374a.pdf/to-advance-translational-science-remove-these-roadblocks-to-studying-team-knowledge-integration.pdf
- Lewis, K., & Herndon, B. (2011). Transactive memory systems: Current issues and future research directions. *Organization Science, 22*(5), 1254–1265. https://econpapers.repec.org/RePEc:inm:ororsc:v:22:y:2011:i:5:p:1254-1265
- Majchrzak, A., More, P. H. B., & Faraj, S. (2012). Transcending knowledge differences in cross-functional teams. *Organization Science, 23*(4), 951–970. https://econpapers.repec.org/RePEc:inm:ororsc:v:23:y:2012:i:4:p:951-970
- Martin, G., Détienne, F., & Lavigne, E. (2002). Confrontation of viewpoints in a concurrent engineering process. In P. Chedmail (Ed.), *Integrated design and manufacturing in mechanical engineering*. Kluwer Academic Press. https://arxiv.org/pdf/cs/0612017
- Mathieu, J. E., Luciano, M. M., & DeChurch, L. A. (2018). Multiteam systems: The next chapter. In *The SAGE handbook of industrial, work & organizational psychology* (pp. 333–353). SAGE Publications. https://atlas.northwestern.edu/wp-content/uploads/2018/02/Mathieu-et-al.-2018.pdf
- Moe, N. B., Dingsøyr, T., & Rolland, K. (2018). To schedule or not to schedule? An investigation of meetings as an inter-team coordination mechanism in large-scale agile software development. *International Journal of Information Systems and Project Management, 6*(3), Article 4. https://aisel.aisnet.org/ijispm/vol6/iss3/4
- Nidumolu, S. (1995). The effect of coordination and uncertainty on software project performance: Residual performance risk as an intervening variable. *Information Systems Research, 6*(3), 191–219. https://ideas.repec.org/a/inm/orisre/v6y1995i3p191-219.html
- Patterson, C. M., Nurse, J. R. C., & Franqueira, V. N. L. (2024). "I don't think we're there yet": The practices and challenges of organisational learning from cyber security incidents. *Computers & Security, 139*, 103699. https://kar.kent.ac.uk/id/document/3420816
- Qiao, L., Zhao, W., Liu, F., Xu, X., & Tao, J. (2024). Effects of multilevel metacognition on group performance and regulation in collaborative learning. *Frontiers in Psychology, 15*, 1419408. https://pubmed.ncbi.nlm.nih.gov/39679157/
- Reiter-Palmon, R., & Murugavel, V. (2018). The effect of problem construction on team process and creativity. *Frontiers in Psychology, 9*, 2098. https://pmc.ncbi.nlm.nih.gov/articles/PMC6230621
- Riedl, C., Kim, Y. J., Gupta, P., Malone, T. W., & Woolley, A. W. (2021). Quantifying collective intelligence in human groups. *Proceedings of the National Academy of Sciences, 118*(21). https://dspace.mit.edu/handle/1721.1/144213
- Rittel, H. W. J., & Webber, M. M. (1973). Dilemmas in a general theory of planning. *Policy Sciences, 4*, 155–169. https://cswp.theisrm.org/wp-content/uploads/2023/08/Rittel-Webber-1973-Dilemmas-in-a-General-Theory-of-Planning.pdf
- Rowe, L. I., Hattie, J., & Hester, R. (2021). g versus c: Comparing individual and collective intelligence across two meta-analyses. *Cognitive Research: Principles and Implications, 6*, Article 26. https://cognitiveresearchjournal.springeropen.com/articles/10.1186/s41235-021-00285-2
- Schweiger, D. M., & Finger, P. A. (1984). The comparative effectiveness of dialectical inquiry and devil's advocacy: The impact of task biases on previous research findings. *Strategic Management Journal, 5*(4), 335–350. https://ideas.repec.org/a/bla/stratm/v5y1984i4p335-350.html
- Schweiger, D. M., & Sandberg, W. R. (1989). The utilization of individual capabilities in group approaches to strategic decision-making. *Strategic Management Journal, 10*(1), 31–43. https://ideas.repec.org/a/bla/stratm/v10y1989i1p31-43.html
- Sekitoleko, N., Evbota, F., Knauss, E., Sandberg, A., Chaudron, M., & Holmström Olsson, H. (2014). Technical dependency challenges in large-scale agile software development. In *Lecture Notes in Business Information Processing* (Vol. 179, pp. 46–61). https://research.chalmers.se/en/publication/501210
- Shahin, M., Liang, P., & Li, Z. (n.d.). *Do architectural design decisions improve the understanding of software architecture? Two controlled experiments*. https://typeset.io/pdf/do-architectural-design-decisions-improve-the-understanding-zprf213xxb.pdf
- Shuffler, M. L., & Carter, D. R. (2018). Teamwork situated in multiteam systems: Key lessons learned and future opportunities. *American Psychologist, 73*(4), 390–406. https://par.nsf.gov/servlets/purl/10086890
- Shuffler, M. L., Kramer, W. S., Carter, D. R., Thayer, A. L., & Rosen, M. A. (2018). Leveraging a team-centric approach to diagnosing multiteam system functioning: The role of intrateam state profiles. *Human Resource Management Review*. https://par.nsf.gov/servlets/purl/10048992
- Srivastava, N. (2026, July 6). *How Attentive Engineering designed a pragmatic RFC process for teams*. Attentive Tech Blog. https://tech.attentive.com/articles/rfc-process-for-teams
- Thoughtworks. (2023, September 27). *Lightweight approach to RFCs*. Thoughtworks Technology Radar. https://www.thoughtworks.com/en-in/radar/techniques/lightweight-approach-to-rfcs
- Tobisch, F., & Matthes, F. (2025). Knowledge sharing and coordination in large-scale agile software development: A systematic literature review and an interview study. In *Lecture Notes in Business Information Processing (XP 2025)*. Springer. https://doi.org/10.1007/978-3-031-94544-1_6
- Toche, B., Pellerin, R., & Fortin, C. (2020). Set-based design: A review and new directions. *Design Science, 6*, e18. https://doi.org/10.1017/dsj.2020.16
- Uludağ, Ö., Philipp, P., Putta, A., Paasivaara, M., Lassenius, C., & Matthes, F. (2022). *Revealing the state of the art of large-scale agile development research: A systematic mapping study* (arXiv:2007.05578). arXiv. https://arxiv.org/pdf/2007.05578
- U.S. Government Accountability Office. (2017). *NASA human space exploration: Integration approach presents challenges to oversight and independence* (GAO-18-28). https://www.gao.gov/products/gao-18-28
- Weick, K. E., Sutcliffe, K. M., & Obstfeld, D. (2005). Organizing and the process of sensemaking. *Organization Science, 16*(4), 409–421. https://econpapers.repec.org/RePEc:inm:ororsc:v:16:y:2005:i:4:p:409-421
- Wentworth, A. N. (2025). *Meta-analytic investigations of the ABCs of teamwork and multiteam systems* [Doctoral dissertation, Clemson University]. https://open.clemson.edu/all_dissertations/4149
- Wolbers, J. J. (2021). Understanding distributed sensemaking in crisis management: The case of the Utrecht terrorist attack. *Journal of Contingencies and Crisis Management*. https://scholarlypublications.universiteitleiden.nl/access/item%3A3239230/view
- Woolley, A. W., Chabris, C. F., Pentland, A., Hashmi, N., & Malone, T. W. (2010). Evidence for a collective intelligence factor in the performance of human groups. *Science, 330*(6004), 686–688. https://pubmed.ncbi.nlm.nih.gov/20929725/
- Zhou, Z., & Pazos, P. (2020). Empirical perspectives of transactive memory systems: A meta-analysis. *Team Performance Management*. https://aquila.usm.edu/fac_pubs/18243
