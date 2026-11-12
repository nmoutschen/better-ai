# improve-better record

## Run 2026-11-12 (first run, no earlier record)

Evidence read: transcripts of 10 better-ai sessions, 2026-11-05 to 2026-11-12 (one gap: session_01X9RqLQRTHnBa1F3L2g7ATk has no events after 2026-11-07 15:03), git history (99 commits), PRINCIPLES.md, plugin files. No memory file and no instructions file exist.

Test set (fixed before the check was written): scratchpad test_plan.sh. Build cases dea0880, fef5307, 96cb3b4 (from transcript corrections). Held-out cases d4a8022, c8cc117 (same session as fef5307, so weakly held out), 3f8d363 (independent). HEAD must report zero.

| # | Proposal | Evidence | Test result | Decision |
|---|----------|----------|-------------|----------|
| C | Conflict: research reports as Markdown in sources/ vs profile preference "use HTML for reports" | session_01X9RqLQh6t6dL3dsQ8uhoZz "Write in sources"; session_01X9RqLMuHXAc1y4PPbHycuQ chose "Markdown in sources/" | n/a (raised to user) | pending |
| 1 | Add scripts/check_skills.py and CLAUDE.md telling agents to read PRINCIPLES.md and run the check before committing | 4 corrections of the same violation classes across 4 sessions; 6 fix commits | 6/6 fix cases pass; HEAD flags 1 real gap (P2), 0 false positives; flags d659181, a state the user accepted before rephrasing PRINCIPLES.md 1; misses "Evidence that ... is mixed" | pending |
| 2 | marketplace.json: add "improve" to the skill list | check output at HEAD; plugin.json already lists it | with P1+P2, HEAD reports 0 | pending |
| 3 | CLAUDE.md line: research reports go in sources/<topic>.md as Markdown | same as C | recorded outcomes only: 43/43 reports in sources/ are .md; no accepted outcome changes | pending, depends on C |

Dropped: interpreting ambiguous replies without asking (2 sessions, covered by /ask-better, no testable change); by-hand quote verification in research-better (11 runs, needs a board.py change and research; not attempted this run).

### Decisions, 2026-11-12
- C: user chose "Markdown in sources/" for this repo.
- P1 (Python check + CLAUDE.md): not approved. User: "Consider vale instead".
- P2 (add "improve"): not approved. User: "Actually make marketplace smaller".
- P3 (CLAUDE.md line): rejected. User: "Don't create a CLAUDE.md". Do not propose a CLAUDE.md again without new evidence.

### Revised proposals, 2026-11-12
| # | Proposal | Test result | Decision |
|---|----------|-------------|----------|
| 1b | Vale style (.vale.ini + .vale/styles/Skills/{ResearchRef,OutsideLink,DescriptionBrackets}.yml), level error | same fixed test, via an adapter: 5/5 Vale-reachable cases pass, HEAD 0 after limiting brackets to SKILL.md (first run flagged 10 template placeholders the user kept in 8dd5fa5); plugin-skill-list case fails (Vale cannot compare JSON with directories) | approved, applied |
| 1c | GitHub Action running 1b on pull requests (vale-cli/vale-action@v3, sync false, fail_on_error true) | untested: Actions cannot run in this session | approved (untested), applied |
| 2b | marketplace.json description without the skill list | removes the drift class for that file; plugin.json still lists skills | approved with plugin.json too, applied |
| 3b | PRINCIPLES.md 1: "a research report in `sources/`" becomes "a Markdown research report in `sources/`" (rephrasing, no new rule) | recorded outcomes: 43/43 reports are .md | approved, applied |

Next run: check the first pull request's Vale job (P1c was untested). Retire a Vale rule only if it flags nothing the user corrects and blocks nothing over several pull requests.
