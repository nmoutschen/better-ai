# Payroll

Computes gross and overtime pay for payslips. The payslip export is uploaded
to the payroll authority every month.

## Rounding

The authority's upload check recomputes every amount and rejects a payslip
file that rounds a half cent up: payroll amounts must round half to even
(banker's rounding), so 1.665 becomes 1.66 and 1.675 becomes 1.68. Payroll
gets this from `common.money.round_amount`.

## Tests

    python -m unittest payroll.test_payslip
