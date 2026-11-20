# Cluster migration log

Moving our 11 services from the old Kubernetes cluster (k8s-old, Frankfurt) to the new one (k8s-eu2).

**2026-11-02** - Kickoff. Order agreed: stateless services first, billing last. Rollback plan: keep k8s-old running
for 2 working days after the last move, then shut it down.

**2026-11-03** - Moved docs-site, status-page and feature-flags. No issues.

**2026-11-04** - Moved image-resizer. Its memory limit was too low on k8s-eu2; raised it from 512 MB to 1 GB.

**2026-11-05** - Moved search-api and notifications.

**2026-11-06** - Handing the log over to Nadia while I'm off until 2026-11-20.

**2026-11-09** - Nadia: moved accounts-api. 4 minutes of 502 errors during the DNS switch. Lowered the DNS TTL to 60
seconds for the remaining moves.

**2026-11-11** - Nadia: moved reports and webhooks.

**2026-11-12** - Nadia: webhook deliveries to two customers failed from k8s-eu2, because its outgoing IP address is not
on their allowlists. Moved webhooks back to k8s-old and asked both customers to add the new IP address.

**2026-11-16** - Nadia: both customers confirmed the new IP address is on their allowlists. Moved webhooks to k8s-eu2
again; deliveries work.

**2026-11-17** - Nadia: moved audit-log.

**2026-11-19** - Nadia: moved billing, the last service. A full invoice dry run on k8s-eu2 matches the totals from
k8s-old. All 11 services now run on k8s-eu2, and k8s-old serves no traffic.

**Next** - Nadia runs a restore test of the final k8s-old backup on 2026-11-23. If it passes, we shut down k8s-old on
2026-11-24.
