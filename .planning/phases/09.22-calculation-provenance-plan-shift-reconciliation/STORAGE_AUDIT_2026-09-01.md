# Production storage audit - 2026-09-01

## Mode and safety

- Source: Supabase Management API, read-only SQL.
- Project: `ghfrweapqxanahiyjwai`.
- Database changed: no.
- No row contents or PII were exported.

## Database size

- Total logical database size: 1,401,318,547 bytes (`1,336 MB`).
- Method OS tenant tables combined: 327,680 bytes (`320 kB`).
- Removing the Method OS data would not materially resolve the quota incident.

## Largest relations

| Table | Total size | Approximate rows |
|---|---:|---:|
| `automation_execution_logs` | 572 MB | 1,169,302 |
| `message_logs` | 403 MB | 661,110 |
| `in_app_notifications` | 89 MB | 265,086 |
| `checkins` | 75 MB | 106,655 |
| `tasks` | 52 MB | 54,982 |

## High-confidence cleanup candidates

- 942,568 automation execution logs older than 30 days.
- 660,924 message logs with status `skipped`; no message was delivered.
- 258,330 repeated unread notifications when retaining the newest record for
  each gym/member/user/title/category group.

The first three relations account for roughly 1,064 MB before cleanup. The
candidate-row ratios indicate a potential recovery near 900 MB, but actual disk
recovery depends on PostgreSQL compaction after deletion.

## Root cause

The daily automation engine evaluates threshold conditions as persistent state,
not as a one-time transition. The same eligible students are processed every
day. This produced repeated `skipped` WhatsApp records, repeated unread
notifications and an execution log for each repeat.

The largest sources are:

- production `academia-principal`: 439,885 skipped, 238,023 notified and
  36,161 created automation executions;
- demo `bio-v2-demo`: 428,732 skipped and 1,460 created executions;
- seeded preview `academia-preview-erica-20260314`: 25,677 executions.

## Proposed operation (not yet authorized)

1. Temporarily disable only the repeating automation rules.
2. Back up aggregate counts and the small set of non-skipped message history.
3. Delete automation logs older than 30 days.
4. Delete message logs whose status is exactly `skipped`.
5. Deduplicate unread notifications while retaining the newest copy.
6. Compact the affected PostgreSQL tables in a controlled maintenance window.
7. Deploy event/cooldown idempotency before re-enabling the rules.
8. Re-run table sizes and verify members, check-ins, assessments, body
   composition, plans, finance and consent counts were unchanged.

No Method OS, Central Cordex or Revisao Cordex product data needs to be removed
to solve this quota incident.

## Applied cleanup

Authorized by the owner with an explicit instruction to preserve all useful
customer data.

- Repeating rules temporarily disabled and audited:
  `68eae7f8-9998-47af-854a-2de228ce52a2`.
- Skipped message compaction:
  `82dea989-e7f2-4531-9311-d6762f77014e`.
  - 660,924 rows removed;
  - all 152 non-skipped messages preserved;
  - relation reduced from 403 MB to 264 kB.
- Automation history compaction:
  `b03e98f4-79e6-47e4-a2e6-f5d463763ed8`.
  - all skipped executions removed;
  - all 37,691 created-task records preserved;
  - 47,850 effective notifications from the last 30 days preserved;
  - relation reduced from 572 MB to 33 MB.
- Notification compaction:
  `b430e623-7940-4add-88b5-4b8f9855ebac`.
  - all 80 read notifications preserved;
  - 42,918 current, unique unread notifications preserved;
  - relation reduced from 89 MB to 16 MB.

Final database size: 336,981,139 bytes (`321 MB`), down from `1,336 MB`.

Post-cleanup invariants:

- members: 32,240 (unchanged);
- check-ins: 106,655 (unchanged);
- assessments: 140 (unchanged);
- body-composition evaluations: 462 (unchanged);
- useful messages: 152 (unchanged);
- read notifications: 80 (unchanged);
- leftover cleanup tables: zero.

## Post-release state

- A 1,808 kB logical rollback snapshot was added in
  `codex_backup_20260901_pre_calc` before migration `20260901_0059`.
- The approved Actuar reconciliation added 2,579 legitimate check-ins under
  batch `c436edc4-fc94-4a46-93e8-ac093d55ce4c`.
- Final database size after backup, migration and reconciliation: `328 MB`.
- Production rules were re-enabled only after the cooldown guard was deployed.
  Preview and bio-v2 demo rules remain inactive; the remaining preview lead rule
  was also disabled. Rule-state audit batch:
  `be0c226d-3b38-4327-805a-98bf2ebf582d`.
- Final retained high-volume rows: 85,541 automation executions, 152 message
  logs and 42,998 notifications.
