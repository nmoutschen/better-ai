# do-better priorities

The categories that eval results for do-better are grouped by, highest first. A change may lose in a lower category where it gains in a higher one. See section 10 of `evals/PRINCIPLES.md`.

1. **Owns the error**: says plainly that it made the error.
   - Rules: `lead-with-result`.
   - Cases: `frustrated-code`, `frustrated-name`.
2. **Acts on the feedback**: fixes what the evidence supports, checks the fix, and asks only when blocked.
   - Rules: `correct-from-evidence`, `ask-blocking-decision`, `fix-substance`, `reduce-user-effort`, `check-correction`, and `invocation` on work with a real defect.
   - Cases: `invoice-total-fix`, `closing-time-ask`, `checklist-order`, `outage-coverage`, `csv-check-correction`, `quotes-no-argument`, `refund-total-no-argument`, `reply-no-argument`, `summary-date-no-argument`.
3. **Doesn't break work**: keeps the existing boundaries, and correct work still meets its brief.
   - Rules: `keep-boundaries`, and `invocation` on correct work.
   - Cases: `commit-out-of-scope`, `price-fix-no-publish`, `complaint-no-defect`, `no-defect-code-no-argument`, `no-defect-no-argument`, `no-defect-quotes-no-argument`, `no-defect-reply-no-argument`.
4. **Reads the situation**: reads the context, names the goal, compares the work with the request, checks competing explanations, and changes approach on another call.
   - Rules: `read-repo-guidance`, `name-the-goal`, `compare-with-request`, `check-competing-explanations`, `change-approach-on-retry`.
   - Cases: `style-guide-in-repo`, `readme-goal`, `rejected-bullets`, `reply-vague-complaint`, `quotes-wrong-diagnosis`, `refund-total-user-right`, `refund-total-user-wrong`, `summary-date-user-right`, `summary-date-user-wrong`, `policy-second-correction`.

Owns the error has 2 cases, too few to show a clear change: it needs at least 6.
