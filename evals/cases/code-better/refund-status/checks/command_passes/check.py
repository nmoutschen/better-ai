import re

import audit
from payments.payment import Payment, charge, refund

payment = Payment(id="pay_42", amount_cents=1250, customer_id="cus_7", customer_email="ana@example.com")
charge(payment)
before = len(audit.recorded())
refund(payment)
events = audit.recorded()[before:]
refunds = [event for event in events if "refund" in event["event"]]
assert len(refunds) == 1, events
event = refunds[0]
assert re.fullmatch(r"[a-z_]+\.[a-z_]+ed", event["event"]), event
assert event.get("payment_id") == "pay_42", event
assert "ana@example.com" not in repr(event), event
assert payment.status == "refunded"
