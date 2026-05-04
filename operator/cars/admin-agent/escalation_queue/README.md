# `escalation_queue/` — encrypted human-review queue

When the admin-agent's rubric fires "escalate" (ambiguous case,
high-value transaction, cross-jurisdiction, novel pattern,
contradictory evidence, or `severity=high` requiring human
co-sign), the case is parked here for the human operator to
process.

## Contents (at runtime, never committed)

```
escalation_queue/
├── README.md                          this file (committed)
├── pending/
│   └── <dispute-id>.json              encrypted at rest with operator pubkey
├── awaiting_co_sign/
│   └── <dispute-id>.json              ready to publish once a human co-signs
└── resolved/
    └── <dispute-id>.json              decision data only, plaintext purged
```

The `pending/`, `awaiting_co_sign/`, and `resolved/` subdirs are
in `.gitignore` and never committed.

## File contents

Each `<dispute-id>.json` is encrypted at rest with the operator's
pubkey (NIP-44) and contains:

- `dispute_id`
- `parties` (the two pubkeys)
- `pack`
- `rubric_outcome` — what the rubric returned ("escalate",
  "high_severity", "ambiguous", etc.)
- `sanitized_summary` — output of `input_safety` on both parties'
  evidence, ≤ 4 KB total
- `proposed_decision` (if the agent has one to offer the human)
- `injection_signals` — list of patterns the agent detected and
  flagged
- `created_at`, `due_by`

**Plaintext evidence is never written here.** Only the sanitized
summary and structured signals.

## Matrix bot integration (recommended)

In production, wire a Matrix bot that:

1. Watches `pending/` and posts a notification (with dispute-id +
   rubric_outcome) to the operator's ops room.
2. Decrypts on the operator's terminal only — never in the bot's
   memory.
3. Provides a `!cosign <dispute-id>` command that drops a
   co-signature file in `awaiting_co_sign/`.
4. After co-sign, the admin-agent picks it up on its next loop
   and publishes the 30430.

The bot itself is allowed to see the dispute-id, rubric_outcome,
and parties. The actual sanitized summary should only be opened
on the operator's machine, which holds the decryption key.

## Email fallback

If Matrix is unavailable, the operator's email (`info.contact` in
strfry config) receives a daily digest of pending dispute-ids.
The operator then SSHes into the admin-agent host, decrypts the
relevant file, and writes a co-signature.

## What goes in `resolved/`

After the admin-agent publishes the 30430 (or after the case is
closed without publication), the corresponding pending file moves
to `resolved/` with all plaintext fields purged. Only:

- `dispute_id`
- `parties`
- `decision`, `severity`
- `reason_hash`
- `decided_at`
- `appeal_until`
- `human_co_signed`

remain. This file is what the 90-day retention policy applies to;
see `../retention/README.md`.

## Never log PII to disk

- No party names beyond pubkeys.
- No conversation log content.
- No complaint text plaintext.
- No phone numbers, addresses, VINs, license plates.

The escalation queue is for triage, not archive. The reason_hash
is what binds a public 30430 to the operator's internal case
notes; the notes themselves never live here.
