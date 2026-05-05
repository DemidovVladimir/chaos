# Adding the cars-pack admin-agent to your trust list

The admin-agent's decisions are **opt-in**. Until you explicitly
add its pubkey to your trust list, your reputation-mcp will not
weight any of its kind 30430 events when scoring sellers or
buyers. This is by design (Rule 16) — admin trust is a choice, not
a default.

## Why opt-in matters

The admin-agent is the highest-value prompt-injection target in
the system (see `reputation/admin_threat_model.md`). Forcing trust
on every user would mean a single compromised admin-agent could
poison the protocol's reputation graph for everyone. Opt-in
limits the blast radius:

- Users who never add the admin-pubkey see no admin decisions.
- Users who later distrust the admin remove the pubkey from their
  list and immediately stop weighting its events.
- The operator must earn trust by acting predictably; users vote
  with their config, not their feet.

## How to add

1. Verify the admin-pubkey through **two independent channels**:
   - Fetch `https://<operator-domain>/.well-known/chaos-admin/cars-pack.json`
     and read `admin_pubkey` plus `operator_signature`.
   - Cross-check the same admin-pubkey from a different mirror
     controlled by the operator (mailing list, GitHub
     `operator/cars/admin-agent/pubkey.json`, etc.).
   - The announced admin-pubkey and operator signature must agree.

2. Add the pubkey to your `~/.chaos/config.yaml`:

   ```yaml
   reputation:
     trust_admins:
       "<admin-pubkey-hex>": 0.8     # weight 0..1; default 0.8
   ```

3. Reload your buyer / seller skill or restart Hermes.

## How to remove

Set the weight to `0.0` or delete the entry. Reputation-mcp will
stop weighting that admin's decisions on the next query. The
events remain on the relay; you simply stop counting them.

## Why we don't ship a default trust value

A default of `0` would silently void the admin-agent for every
new user — the admin would do work no one ever sees.

A default of `0.8` would conscript every user into trusting an
admin they never chose.

We pick neither default. The first-run wizard prompts the user
explicitly: "Do you want to trust the cars-pack admin-agent at
pubkey X? (y/N)". This is an interactive opt-in. Programmatic
installs (CI, scripts) must set the weight in config; there is no
default.

## Operator commitments

In return for trust, the operator commits to:

- Publishing the admin-pubkey out of band on launch and rotating
  it via NIP-09 + reannouncement if it's ever compromised.
- Following the published rubric (`admin-cars/SKILL.md`) and the
  threat model (`reputation/admin_threat_model.md`) on every case.
- Co-signing every `severity=high` decision before publication.
- Retaining only structured decision data past 90 days (see
  `retention/README.md`).
- Operating the appeal channel (kind 30431) honestly: an appealed
  decision freezes at 50% weight until resolved, and resolved
  appeals are reissued as fresh 30430s, not silent edits.

If any of these is violated, users should remove the pubkey from
their trust list. That removal is the enforcement mechanism.
