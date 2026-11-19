from decimal import Decimal

from invoicing.invoice import invoice_total, line_amount
from payroll.payslip import gross_pay, overtime_pay

# Invoices round a half cent up.
assert line_amount("3", "0.555") == Decimal("1.67"), line_amount("3", "0.555")
assert line_amount("1", "2.665") == Decimal("2.67"), line_amount("1", "2.665")
assert line_amount("2", "1.10") == Decimal("2.20"), line_amount("2", "1.10")
assert invoice_total([("3", "0.555"), ("1", "2.665")]) == Decimal("4.34")

# Payroll keeps rounding half to even.
assert gross_pay("1.5", "1.11") == Decimal("1.66"), gross_pay("1.5", "1.11")
assert gross_pay("0.5", "5.33") == Decimal("2.66"), gross_pay("0.5", "5.33")
assert gross_pay("8", "12.50") == Decimal("100.00")
assert overtime_pay("1", "1.11") == Decimal("1.66"), overtime_pay("1", "1.11")
