# VPN outage 10 Nov: who did what (from the incident channel)

Notes taken by Mei Lin during the incident review on Thursday 12 November.

## During the incident

- 08:52 Kwame Asante made the firewall rule change on the edge gateway, as part of the planned maintenance window.
- 09:40 Service desk got the first reports (several callers; not tracked by name).
- 09:48 Mei Lin declared the incident and took incident lead.
- 10:20 Mei Lin found the rule change in the gateway log and reverted it, with Kwame on the call.
- 11:07 Kwame confirmed all VPN sessions back.

## Owners for the action items

- Runbook for edge gateway changes (rollback step + VPN connection test): Ayşe Demir, due 24 Nov.
- Packet-loss alert threshold 50% → 10%, page on-call: Tomás Herrera, due 17 Nov.
- Peer review step for edge gateway firewall changes: Mei Lin, due 1 Dec.
- Change calendar to the wiki: no owner yet, to be picked at the next team meeting.
