# Incident report: duplicate card charges after payments release 4.13

On Monday 16 November at 10:40 CET we deployed version 4.13 of the payments service. The release added Apple Pay to web
checkout and changed how the service retries a card payment when the bank does not answer within 8 seconds.

At 13:15 the first support ticket arrived from a customer who had been charged twice for one order. Support received two
more by 15:00 and opened an incident. Mateus Costa, on call for payments, found in the logs that when a bank answered
after the 8-second timeout, the service had already sent a retry, and both the original payment and the retry went
through.

On Tuesday 17 November we shipped 4.13.1, which raised the timeout to 15 seconds. This reduced the duplicates but did not
stop them: banks in two countries regularly take longer than 15 seconds during their evening peak. Since then we have
still seen about 40 duplicate charges a day.

On Wednesday 18 November Leila Haddad from finance pulled the full list of duplicate charges since the release. As of
Thursday 19 November, 312 customers have been charged twice, for a total of €8,400. None of them has been refunded yet.
Finance can refund them in one batch, but only once no new duplicates are being created, so that they do not have to run
the batch twice.

The proper fix is to send an idempotency key with each payment, so that the bank rejects the second attempt. The team
estimates this at two weeks of work, including tests with our three acquiring banks, so it would ship around 4 December
at the earliest.

We also looked at rolling back to 4.12. The retry logic in 4.12 does not create duplicates, and the rollback takes about
an hour with no downtime. The cost is that Apple Pay on web checkout goes away until the idempotency fix ships; since
Monday, 2.1% of web payments have used it.

Conclusion: we should roll back the payments service to 4.12 by Friday 20 November. Every day we wait adds about 40
duplicate charges. Refunds of €8,400 to the 312 customers are pending, and finance will run them once the rollback is
done. We need your approval to take Apple Pay off web checkout until the idempotency fix ships, around 4 December.
