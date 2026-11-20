# Postmortem: office VPN outage, Tuesday 10 November 2026

Status: draft for the infrastructure team

## Summary

The office VPN was unavailable for 2 hours 15 minutes on Tuesday 10 November, from 08:52 to 11:07. About 180 staff
working from home could not reach internal tools during that time. No data was lost.

## Timeline

- 08:52: A firewall rule on the edge gateway was changed during planned maintenance. The change blocked UDP port 1194,
  which the VPN uses.
- 09:05: Packet loss on the VPN reached 38%. No alert was raised, because the alert threshold is set at 50% packet loss.
- 09:40: The first user reports were received by the service desk. The incident was declared at 09:48.
- 10:20: The firewall change was identified as the cause and the rule was reverted.
- 11:07: All VPN sessions were confirmed as restored.

## Causes

The maintenance change had been reviewed for the web proxy, but its effect on the VPN port was not checked, because the
change ticket did not list the VPN as an affected service. The runbook for edge gateway changes has no rollback step, so
time was spent working out how to restore the previous rule. The packet-loss alert was configured when the VPN served 20
people, and its threshold was never revisited.

## Action items

1. The runbook for edge gateway changes will be updated to include a rollback step and a VPN connection test. Due 24
   November.
2. The alert threshold will be lowered from 50% to 10% packet loss, with a page to the on-call engineer. Due 17 November.
3. A peer review step will be added for every firewall change that touches the edge gateway. Due 1 December.
4. The change calendar will be moved from the old spreadsheet to the team wiki. No date yet.

## Lessons

Changes to shared network equipment need to list every service that depends on them. Alerts need to be checked when the
number of users grows.
