# Reference scoring algorithm

This document defines how `shared-mcp/reputation-mcp` collapses
the layered signals into a single `score_aggregate` ∈ [0, 1] per
counterparty pubkey. The algorithm is **reference**, not
mandated — every weight in this doc is a default, and every weight
is overridable per user.

## Inputs

For a query `(viewer_pubkey, target_pubkey, vertical_pack)`:

1. **NIP-58 badges** issued to `target_pubkey` by trusted issuers
   (operator pubkey + any pubkey on `viewer.config.trust_issuers`).
2. **Bilateral attestations** (30410+30411 pairs) where
   `target_pubkey` is one side of the pair.
3. **Unilateral attestations** (30412) naming `target_pubkey`.
4. **Admin-agent decisions** (30430) where `target_pubkey` ∈ the
   `p` tags, signed by a pubkey in `viewer.config.trust_admins`.
5. **Mute lists** (NIP-51) the viewer has chosen to follow.
6. **Web of trust graph** — NIP-02 contact lists, walked from
   `viewer_pubkey`, capped at 2 hops by default.
7. **(Future) onchain stake** — read from `STAKE.md` placeholder
   bindings. Always `null` in MVP.

## Per-user configurable weights

Defaults shown; user may override in `~/.chaos/config.yaml`.

```yaml
reputation:
  layer_weights:
    badges:           0.20
    attestations:     0.40
    admin_decisions:  0.20
    mute_signal:      0.10
    onchain_stake:    0.10   # 0 in MVP, redistributed to others
  trust_admins:
    "<admin-cars-pubkey>": 0.8
    "<other-pack-admin>": 0.6
  trust_issuers:
    "<operator-pubkey>": 1.0
  wot_distance:
    direct:                   1.0   # NIP-02 contact
    two_hop_shared_contact:   0.4
    verified_badge_unknown:   0.2   # holds a badge but unknown to me
    unknown:                  0.05
  attestation_decay_days:     365
```

## Web-of-trust weight `wot(viewer, signer)`

```
def wot(viewer, signer, contacts):
    if signer == viewer:
        return 1.0
    if signer in contacts(viewer):
        return cfg.wot_distance.direct                # 1.0
    if any(c in contacts(viewer) for c in contacts(signer)):
        return cfg.wot_distance.two_hop_shared_contact # 0.4
    if has_verified_badge(signer):
        return cfg.wot_distance.verified_badge_unknown # 0.2
    return cfg.wot_distance.unknown                    # 0.05
```

WoT is recomputed locally on each query; reputation-mcp does not
cache cross-user WoT scores.

## Layer scores

### Badges layer

```
badge_score = 0.0
for badge in badges_held_by_target:
    if not signature_ok(badge): continue
    if badge.issuer in trust_issuers and not is_revoked(badge):
        badge_score = max(badge_score, trust_issuers[badge.issuer])
    if is_revoked(badge):
        badge_score -= 0.5      # strong negative
badge_score = clamp(badge_score, -1.0, 1.0)
```

A revoked badge (NIP-09 deletion + `badge-revoked` event per
`operator_revocation.md`) is a strong negative signal — it implies
the issuer once trusted and then withdrew trust.

### Attestation layer

```
att_score = 0.0
for pair in valid_pairs(target):
    age_days = (now - pair.sale_closed_at) / 86400
    decay = max(0.0, 1.0 - age_days / cfg.attestation_decay_days)
    counterparty = pair.other(target)
    w = wot(viewer, counterparty)
    if pair.status == "completed-clean":
        att_score += min(0.05, 0.05 * w * decay)
    elif pair.status == "disputed":
        att_score -= 0.15 * w
        # dispute negative is amplified by admin_decision_severity
        # if a matching 30430 exists (see admin layer)
for unilateral in unilateral_dispute_attestations(target):
    w = wot(viewer, unilateral.signer)
    att_score -= 0.07 * w        # half the weight of a paired one
att_score = clamp(att_score, -1.0, 1.0)
```

The single-sale cap of 0.05 prevents a small clique from
manufacturing a high score. Decay is linear over 365 days by
default.

### Admin-decisions layer

```
admin_score = 0.0
for d in admin_decisions_about(target):
    if d.signer not in trust_admins: continue
    weight = trust_admins[d.signer]
    if has_open_appeal(d): weight *= 0.5     # frozen pending appeal
    severity_mult = {"low": 0.3, "moderate": 0.6, "high": 1.0}[d.severity]
    if d.decision == "clear":      admin_score += 0.10 * weight
    elif d.decision == "warning":  admin_score -= 0.20 * weight * severity_mult
    elif d.decision == "flag":     admin_score -= 0.50 * weight * severity_mult
    elif d.decision == "escalated":pass        # neutral; awaiting human
admin_score = clamp(admin_score, -1.0, 1.0)
```

When a 30430 dispute decision is paired with a matching 30410+30411
disputed pair, the attestation-layer dispute negative is amplified
by `severity_mult` for that specific pair.

### Mute-signal layer

```
mute_score = 0.0
if target in viewer.mute_list:                   mute_score = -1.0
elif target in any(operator_public_mute_lists):  mute_score = -0.5
```

### Onchain-stake layer

```
stake_score = 0.0   # Phase 1 placeholder; always 0 in MVP
```

## Aggregation

```
raw = (
    cfg.layer_weights.badges          * badge_score   +
    cfg.layer_weights.attestations    * att_score     +
    cfg.layer_weights.admin_decisions * admin_score   +
    cfg.layer_weights.mute_signal     * mute_score    +
    cfg.layer_weights.onchain_stake   * stake_score
)
score_aggregate = clamp((raw + 1.0) / 2.0, 0.0, 1.0)
# raw ∈ [-1, 1] → score_aggregate ∈ [0, 1]
```

## Thresholds (advisory, not enforced)

- `score_aggregate < 0.2` → **hard red flag**. Seeking agent/offering agent skill
  surfaces a "consider not engaging" warning.
- `0.2 ≤ score < 0.5` → **caution**. Skill suggests asking for
  extra evidence or a small first step.
- `0.5 ≤ score < 0.7` → **neutral/typical**.
- `score ≥ 0.7` → **boosted**. Skill may auto-prioritize this
  counterparty's listings in search.

These thresholds never gate the wire. The protocol always
delivers; the user decides.

## Returned breakdown

`get_reputation` returns:

```json
{
  "badges": [...],
  "attestations": {"completed_clean": 12, "disputed": 1, "vanished": 0},
  "admin_decisions": [...],
  "wot_score": 0.42,
  "onchain_stake": null,
  "score_aggregate": 0.71,
  "components": {
    "badge_score":  0.6,
    "att_score":    0.42,
    "admin_score":  0.0,
    "mute_score":   0.0,
    "stake_score":  0.0
  }
}
```

The `components` block is what the seeking agent's skill renders as a
"why" panel — never just the aggregate number.
