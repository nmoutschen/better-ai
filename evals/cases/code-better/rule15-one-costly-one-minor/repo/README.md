# library nightly job

`nightly.py` runs every night. It reads `data/loans.json` and prints a reminder email for each overdue loan.

- A loan is overdue from the day after its `due` date.
- The library is closed on the days in `data/closed_days.txt`. When a loan is made, its due date is moved to the next open day.
- Late fee policy (approved by the board): 0.25 EUR per day overdue, no cap; staff waive fees by hand.
- The job recomputes each loan's `fee_cents` from scratch every night; members pay at the desk.
