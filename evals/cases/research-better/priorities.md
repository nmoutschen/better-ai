# research-better priorities

The categories that eval results for research-better are grouped by, highest first. A change may lose in a lower category where it gains in a higher one. See section 10 of `evals/PRINCIPLES.md`.

1. **Keeps the evidence on the board**: keeps the board on disk in its format, copies each quote word for word, and marks a source that repeats another.
   - Rules: `keep-board-on-disk`, `quote-verbatim`, `mark-repeats`.
   - Cases: `board-on-disk`, `claims-quote-verbatim`, `repeat-source-marked`.
2. **Fails closed and reports honestly**: asks before the research runs when a collection is missing, cites only the board's sources, and states disputes and gaps.
   - Rules: `fail-closed-missing-collection`, `cite-from-board`, `report-what-is-open`.
   - Cases: `missing-collection-asks`, `findings-cite-from-board`, `findings-report-gaps`.
3. **Splits the work between agents**: the coordinator leaves the research to workers, verifiers check claims they did not record, and each high-priority answer gets a challenge question.
   - Rules: `coordinator-delegates-research`, `verify-claims-separately`, `challenge-high-priority-answers`.
   - Cases: `coordinator-starts-workers`, `verifiers-check-claims`, `challenge-for-answered-high`.

Each category has 3 cases, too few to show a clear change: each needs at least 6.
