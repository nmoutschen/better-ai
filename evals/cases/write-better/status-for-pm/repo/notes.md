# billing dupes: working notes (Kofi)

9 Nov: found duplicate credits after the October tariff change. ORPHAN-check says 140 accounts. Root cause:
`reconcile_ledger` applies the tariff-change credit once per billing period it touches, so a mid-cycle change credits
twice.

10 Nov: talked with Priya. Plan A (hotfix `reconcile_ledger` in place) is out: it touches every invoice path and we
can't test it properly before the 1 Dec run. Going with plan B: fix-7 to stop new dupes, plus corrections for the
existing ones. The v2 path (move reconcile onto the new ledger schema) stays the real fix, but not before January.

13 Nov: fix-7 in review. Tariff changes frozen in admin until it ships (Priya told ops).

16 Nov: fix-7 merged and deployed. No new dupes since. Freeze lifted.

17 Nov: ran the credit-note batch, then ORPHAN-check again: 128 accounts corrected, 12 left. Those 12 had a second
tariff change in November, so the batch can't compute them; they need manual corrections. I'll do them by 27 Nov.

18 Nov: open question for product: do we email the 12 customers before the 1 Dec invoices go out, or let the invoice
show a correction line and explain only if they ask? Lucía (support) prefers emailing before. Need an answer by 24 Nov
to get the email through review in time.

Total over-credit for the 12: €2,316 (largest single account €410).
