# Cognitive systems engineering, for a lesson on reviewing designs

Research register · Search date: 11 November 2026

**Scope.** What cognitive systems engineering (CSE) is, and which of its concepts a reader with no specific job can use to review an interface or automation design. The register covers the field's unit of analysis, the named failure patterns of automation and displays, the review questions the field offers, and published cases. It was gathered to build a static teach-better lesson for curious generalists. Cognitive task analysis is covered by a separate board (`.research/cognitive-task-analysis/`).

**Status.** 16 questions closed: 14 answered and 2 not found. One low-priority question on terms stayed open. Many primary texts were paywalled or blocked. Three were read in full, after local text extraction of their PDFs:
- Bainbridge (1983)
- Woods and Sarter (1998)
- the NTSB report on Asiana 214

62 of 104 claims were checked against their source.

The best-supported material is on automation. Bainbridge (1983) argues that automating a process leaves the operator with the tasks designers could not automate. Unused skills decay, and monitoring for rare events is a task people cannot do well. Woods and Sarter (1998) define automation surprises and say when they are most likely: when automation acts on its own, operators' mental models have gaps, and feedback is weak. They recommend observability, which is the work needed to find meaning in data, not just making data available. The Asiana 214 report shows the pattern in an accident (National Transportation Safety Board [NTSB], 2014). Material on data overload, the keyhole effect, ecological interface design results and situation awareness rests on abstracts, Wikipedia or trade articles, or was not found.

## 1. What the field is

**Evidence: one handbook, read in full; primary texts blocked.**

- "The joint cognitive system (JCS) is the basic unit of analysis in CSE, and is used to emphasise the central idea of co-agency." The human and machine are considered together, not as separate parts linked by an interface (Baxter, 2011).
- "A person is a cognitive system, but cannot be a JCS. A person using an artefact, however, is a JCS", and so is a group of two or more people. The boundary depends on "the purpose of the JCS, and the focus of the analysis" (Baxter, 2011).
- CSE "focuses on the system's behaviour: what it does, and why" (Baxter, 2011). It was developed against three problems: the growing complexity of computerised systems, new technology deployed badly (Three Mile Island is the example), and models that treated people as simple information processors (Baxter, 2011).
- Woods (1985, abstract) framed the design goal as building "an effective combination between the human and machine elements of a joint cognitive system".

## 2. Failure patterns

### 2.1. The ironies of automation

**Evidence: the primary paper, read in full (OCR).**

- "The designer who tries to eliminate the operator still leaves the operator to do the tasks which the designer cannot think how to automate" (Bainbridge, 1983).
- "Physical skills deteriorate when they are not used", so the operator who must take over is less practised exactly when the process is abnormal (Bainbridge, 1983).
- "It is impossible for even a highly motivated human being to maintain effective visual attention towards a source of information on which very little happens, for more than about half an hour." When the computer decides faster or with more information than the operator can check, "the human monitor has been given an impossible task" (Bainbridge, 1983).
- Automatic control "can 'camouflage' system failure by controlling against the variable changes", so the failure is not visible until control runs out (Bainbridge, 1983).
- Responses: alarms, with care, since "a proliferation of flashing red lights will confuse rather than help"; "automatic systems should fail obviously"; hands-on control or simulator practice, with training in "general strategies rather than specific responses"; no paging between displays to find abnormal states (Bainbridge, 1983).
- "Perhaps the final irony is that it is the most successful automated systems, with rare need for manual intervention, which may need the greatest investment in human operator training" (Bainbridge, 1983). A 2012 review found that "the ironies are still there" (Baxter et al., 2012, abstract).

### 2.2. Automation surprises, mode error and going sour

**Evidence: the primary report, read in full (OCR); one official accident report.**

- Automation surprises are "situations where crews are surprised by actions taken (or not taken) by the autoflight system". Their potential "is greatest when three factors converge": automation acts on its own, crews' mental models have gaps, and feedback about the automation's behaviour is weak (Woods & Sarter, 1998).
- Crews generally do not notice the mismatch from displays of data. They notice it from the aircraft's behaviour (Woods & Sarter, 1998).
- "Automation can compensate for trouble silently", so crews can stay unaware of a growing problem (Woods & Sarter, 1998).
- In going-sour accidents, minor events add up "through a series of commissions and omissions, misassessments and miscommunications" (Woods & Sarter, 1998).
- **Clumsy automation** puts burdens on users at the busiest times. In heart-surgery operating rooms, users tailored both a new computerised monitor and their own tasks to cope (Cook et al., 1991, abstract; Woods & Sarter, 1998).
- **Asiana 214 (NTSB, 2014).** Moving the thrust levers to idle put the autothrottle into HOLD, "a mode in which the A/T does not control airspeed". Neither of the two pilots nor the observer "noted the change in A/T mode to HOLD". In HOLD, the autothrottle "will not wake up even during large deviations from target speed". Training had shown the pilot flying the wake-up feature, which "astonished" him. A certification debrief had flagged the exception as "an inconsistency in the automation behavior of the airplane". The probable cause names the crew's mismanagement of the descent. The first contributing factor is that autothrottle and flight director complexities, "inadequately described in Boeing's documentation and Asiana's pilot training", "increased the likelihood of mode error".

### 2.3. Displays and alarms

**Evidence: primary report for observability; secondary for cases and alarm floods.**

- "Observability is the technical term that refers to the cognitive work needed to extract meaning from available data" (Woods & Sarter, 1998). The critical test is whether displays help people "notice more than what they were specifically looking for or expecting". Better feedback is transition-oriented, future-oriented and pattern-based. One cannot increase observability "by adding a new indication or alarm" piece by piece (Woods & Sarter, 1998).
- Alarm floods are defined in standards: "10 or more annunciated alarms in any 10-minute period per operator" (ANSI/ISA 18.2, via Beebe et al., 2012). EEMUA's review of loss incidents found that they "frequently involved the operator being overloaded with alarm floods" (Beebe et al., 2012). EEMUA 191 sets the start of a flood at more than 10 new alarms in 10 minutes (VanCamp, 2016).
- Air Inter 148: the autopilot display showed a vertical speed of 3,300 ft/min as "33", which could be read as a flight path angle. After the accident, vertical speed was shown as four digits (Wikipedia contributors, n.d.-a; secondary).
- Therac-25: an unexplained "Malfunction 54" message was not understood, and treatment continued. Leveson and Turner (1993) call the interface "really a side issue in the accidents", yet recommend training in interface design or "more input ... from human factors engineers". Sources differ on how much weight the interface carries.

## 3. Review questions the field offers

**Evidence: a magazine article read in part; abstracts.**

- Klein et al. (2004) list ten challenges for automation as a "team player": a basic compact, adequate models, predictability, directability, revealing status and intentions, interpreting signals, goal negotiation, collaboration, attention management, and cost control. They offer them, among other uses, "as a blueprint for designing and evaluating intelligent systems".
- Christoffersen and Woods (2002, abstract) name two characteristics "which need to be designed in from the beginning": observability and directability.
- No source gave a scored checklist. The MITRE human-machine teaming guide has a heuristic evaluation appendix, but it could not be read.

## 4. Other concepts, with weak evidence

- **Cognitive work analysis** has five phases, each analysing a different kind of constraint: work domain, control tasks, strategies, social organisation, and worker competencies (Ashoori et al., 2014). Practitioners report "no typical means of using the outputs of CWA within design processes" (Read et al., 2015, abstract).
- **Ecological interface design** aims to support skill-, rule- and knowledge-based control "without forcing control to a higher level than the task requires" (Rasmussen & Vicente, 1988, abstract). No study of its effect on performance could be read.
- **Situation awareness** is defined by Endsley as perceiving elements, understanding their meaning, and projecting their near-future status. Critics call it circular (Wikipedia contributors, n.d.-b; low trust).
- **Resilience engineering** treats failure as "the result of the adaptations necessary to cope with the complexity of the real world" (Hollnagel et al., 2006, publisher page). No source stated how it relates to CSE.

## 5. Open questions and gaps

- Primary texts not read: Norman (1986), Hollnagel and Woods (1983), Woods, Patterson and Roth on data overload, Woods on the keyhole effect, the DURESS experiments, Dekker and Woods (2024), and the BEA report on AF447.
- What terms sources use for the field and its neighbours (low priority, not researched).

## References

Ashoori, M., Burns, C. M., d'Entremont, B., & Momtahan, K. (2014). Using team cognitive work analysis to reveal healthcare team interactions in a birthing unit. *Ergonomics, 57*(7), 973–986. https://pmc.ncbi.nlm.nih.gov/articles/PMC4066876

Bainbridge, L. (1983). Ironies of automation. *Automatica, 19*(6), 775–779. https://gwern.net/doc/sociology/technology/1983-bainbridge.pdf

Baxter, G. (2011). *Cognitive systems engineering*. LSCITS Socio-Technical Systems Engineering Handbook, University of St Andrews. https://archive.cs.st-andrews.ac.uk/STSE-Handbook/CognitiveSystemsEngineering/index.html

Baxter, G., Rooksby, J., Wang, Y., & Khajeh-Hosseini, A. (2012). *The ironies of automation... still going strong at 30?* European Conference on Cognitive Ergonomics. https://research-portal.st-andrews.ac.uk/en/publications/the-ironies-of-automation-still-going-strong-at-30/

Beebe, D., Ferrer, S., & Logerot, D. (2012, July). Alarm floods and plant incidents. *Digital Refining*. https://digitalrefining.com/article/1000558/alarm-floods-and-plant-incidents

Christoffersen, K., & Woods, D. D. (2002). How to make automated systems team players. *Advances in Human Performance and Cognitive Engineering Research, 2*. Emerald. https://emerald.com/insight/content/doi/10.1016/S1479-3601(02)02003-9

Cook, R. I., Woods, D. D., McColligan, E., & Howie, M. B. (1991). *Cognitive consequences of clumsy automation on high workload, high consequence human performance*. NASA Johnson Space Center (SOAR 90). https://ntrs.nasa.gov/citations/19910011398

Hollnagel, E., Woods, D. D., & Leveson, N. (Eds.). (2006). *Resilience engineering: Concepts and precepts*. CRC Press. https://www.routledge.com/Resilience-Engineering-Concepts-and-Precepts/Hollnagel-Woods-Leveson/p/book/9780754649045

Klein, G., Woods, D. D., Bradshaw, J. M., Hoffman, R. R., & Feltovich, P. J. (2004). Ten challenges for making automation a "team player" in joint human-agent activity. *IEEE Intelligent Systems*. https://fermatslibrary.com/s/ten-challenges-for-making-automation-a-team-player-in-joint-human-agent-activity

Leveson, N. G., & Turner, C. S. (1993). An investigation of the Therac-25 accidents. *IEEE Computer, 26*(7), 18–41. https://web.mit.edu/6.033/2004/wwwdocs/papers/Therac_5.html

National Transportation Safety Board. (2014). *Descent below visual glidepath and impact with seawall, Asiana Airlines Flight 214* (NTSB/AAR-14/01). https://www.ntsb.gov/investigations/AccidentReports/Reports/AAR1401.pdf

Rasmussen, J., & Vicente, K. J. (1988). On applying the skills, rules, knowledge framework to interface design. *Proceedings of the Human Factors Society 32nd Annual Meeting*, 254–258. https://garyperlman.com/hfeshci/Abstracts/88_254-258.html

Read, G. J. M., Salmon, P. M., & Lenne, M. G. (2015). Cognitive work analysis and design: Current practice and future practitioner requirements. *Theoretical Issues in Ergonomics Science, 16*(2), 154–173. https://research.usc.edu.au/esploro/outputs/journalArticle/Cognitive-work-analysis-and-design-Current/99448731902621

VanCamp, K. (2016, March 1). Alarm management by the numbers. *Chemical Engineering*. https://www.chemengonline.com/alarm-management-numbers/

Wikipedia contributors. (n.d.-a). *Air Inter Flight 148*. Wikipedia. https://en.wikipedia.org/wiki/Air_Inter_Flight_148

Wikipedia contributors. (n.d.-b). *Situation awareness*. Wikipedia. https://en.wikipedia.org/wiki/Situation_awareness

Woods, D. D. (1985). Cognitive technologies: The design of joint human-machine cognitive systems. *AI Magazine*. https://aitopics.org/doc/journals:846C56F2

Woods, D. D., & Sarter, N. B. (1998). *Learning from automation surprises and "going sour" accidents: Progress on human-centered automation* (Final report, NASA Ames grant NCC 2-592). https://ntrs.nasa.gov/api/citations/19980016965/downloads/19980016965.pdf
