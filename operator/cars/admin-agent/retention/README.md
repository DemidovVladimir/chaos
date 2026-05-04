# `retention/` — 90-day forgetting policy

The admin-agent commits to two retention rules:

1. **Plaintext at decision time → 0.** Conversation logs,
   complaint text, evidence packages: purged the moment the
   admin-agent decides (or escalates). The only artifact that
   survives is the sanitized summary in
   `escalation_queue/resolved/<dispute-id>.json`, which contains
   no plaintext evidence.

2. **Decision-level structured data → 90 days.** After 90 days
   from `decided_at`, even the structured decision file (parties,
   decision, severity, reason_hash, timestamps) is purged.
   Hashes — `reason_hash`, `evidence_hash`, the kind 30430
   event-id — live on the relay indefinitely; the operator's
   private notes do not.

## Why hashes survive but plaintext doesn't

The kind 30430 published to the relay carries the `reason_hash`.
A court-compelled disclosure of the preimage is the only legal
path to plaintext. By keeping plaintext **off the operator's
infrastructure** within 90 days, the operator minimizes the
attack surface for compelled disclosure, hacks, and accidental
leaks.

The hash itself is a public commitment: the operator can prove
they made a specific decision based on specific notes, but cannot
later be subpoenaed for notes that no longer exist.

## What rotation does

`rotate.sh.example` is the template script. In production, copy
it to `rotate.sh`, adjust paths to your deployment, and schedule
via systemd timer or cron (daily, off-peak).

It performs:

1. Walk `escalation_queue/pending/` — purge files whose
   `decided_at` (if set) is older than 0 (i.e. all files whose
   case is decided).
2. Walk `escalation_queue/resolved/` — purge files whose
   `decided_at` is older than 90 days.
3. Vacuum any swap / temp directories the agent uses.
4. Emit a structured log line per file purged (path, action,
   timestamp). Log lines themselves carry no PII.

## Verification

After each rotation run, the operator can verify:

```bash
# No file in pending/ should be older than 7 days (the no-response window).
find operator/cars/admin-agent/escalation_queue/pending/ \
  -type f -mtime +7

# No file in resolved/ should be older than 90 days.
find operator/cars/admin-agent/escalation_queue/resolved/ \
  -type f -mtime +90
```

Both commands should return zero rows.

## Non-goals for retention

- We do **not** ship a "case archive" feature. The operator's
  legal protection comes from genuine forgetting, not from
  encrypted long-term storage.
- We do **not** retain backups of plaintext. Backup scripts
  (`../../backup.md`) cover relay event data and admin-agent
  config — never plaintext evidence.
- We do **not** retain logs that quote conversation content.
  Structured INFO logs at most.
