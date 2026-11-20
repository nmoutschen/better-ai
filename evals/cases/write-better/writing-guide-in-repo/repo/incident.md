# INC-2291: mobile login outage

Status: resolved. Written by Hana Sato (on call), Thu 19 Nov.

## Timeline (UTC)

- 09:12 - alerts: mobile app logins failing with "connection not secure". Web app logins fine.
- 09:20 - Hana paged; confirmed iOS and Android both affected.
- 10:05 - cause found: the TLS certificate on auth-mobile.lumenbox.example expired at 09:11. The auto-renewal job had
  been failing silently since October after a DNS permission change.
- 11:31 - new certificate issued and deployed.
- 11:47 - mobile logins confirmed working; error rate back to normal.

## Impact

- About 18,400 users tried to log in on mobile during the outage and could not.
- Users who were already logged in on mobile stayed logged in and could use the app normally.
- No data lost or exposed. The certificate expired; it was not compromised.
- Scheduled exports not affected (they run server-side).

## Follow-up

- Renewal job fixed (DNS permission restored). Done.
- Alert 21 days before any certificate expires. Owner: Hana, by Fri 4 Dec.
- Customer comms: Support emails all customers today. Paid plans get 1 day of service credit, applied automatically to
  the next invoice (1 Dec). Nothing for customers to do.
- Questions: reply to the email or write to support@lumenbox.example.
