"""Reference scoring algorithm for reputation-mcp.

Implements the weighted-layer aggregation documented in
`reputation/scoring.md`. The function `aggregate_score` is pure
(no I/O); all relay reads happen in `server.py` and feed the result
in here as plain dataclasses.

The defaults below match `scoring.md` exactly. Where the prompt's
fallback table differs from `scoring.md`, this implementation
follows `scoring.md` because the doc is the spec of record per
the project rules.

The final formula collapses five layer scores in [-1, 1] into a
single aggregate in [0, 1]:

    raw = sum(layer_weight[i] * layer_score[i])
    aggregate = clamp((raw + 1.0) / 2.0, 0.0, 1.0)

The aggregate is intentionally *advisory* — buyer/seller skills
render the per-layer breakdown alongside the aggregate so the
user sees "why" rather than just a number.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Default weights (from reputation/scoring.md)
# ---------------------------------------------------------------------------

DEFAULT_LAYER_WEIGHTS: dict[str, float] = {
    "badges": 0.20,
    "attestations": 0.40,
    "admin_decisions": 0.20,
    "mute_signal": 0.10,
    "onchain_stake": 0.10,  # always 0 in MVP
}

DEFAULT_WOT_DISTANCE: dict[str, float] = {
    "direct": 1.0,
    "two_hop_shared_contact": 0.4,
    "verified_badge_unknown": 0.2,
    "unknown": 0.05,
}

DEFAULT_ATTESTATION_DECAY_DAYS: int = 365
SECONDS_PER_DAY: int = 86400

DECISION_VALUES: frozenset[str] = frozenset({"clear", "warning", "flag", "escalated"})
SEVERITY_MULT: dict[str, float] = {"low": 0.3, "moderate": 0.6, "high": 1.0}
ATTESTATION_STATUSES: frozenset[str] = frozenset(
    {"completed-clean", "disputed", "counterparty-vanished"}
)


# ---------------------------------------------------------------------------
# Value types — frozen dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BadgeRecord:
    """An NIP-58 badge held by the target.

    `revoked` is True when the operator has both emitted a NIP-09
    deletion (kind 5) targeting the badge-award AND a kind 30430
    `decision=flag` event referencing it (per
    `operator_revocation.md`). Either alone is insufficient.
    """

    issuer_pubkey: str
    badge_id: str
    award_event_id: str
    revoked: bool = False
    revoked_at: int | None = None  # unix ts of revocation


@dataclass(frozen=True)
class AttestationRecord:
    """A peer-attestation about the target.

    For a paired (30410, 30411) the `kind` is 30410 with `paired=True`
    and `counterparty_status` set; for a unilateral 30412 `kind` is
    30412. `signer_pubkey` is the publishing party (the side whose
    signature the relay verified), `subject_pubkey` is the target.
    """

    kind: int  # 30410, 30411, or 30412
    sale_id: str  # `d` tag value
    signer_pubkey: str
    subject_pubkey: str
    listing_event_id: str
    pack: str
    status: str  # "completed-clean" | "disputed" | "counterparty-vanished"
    sale_closed_at: int  # unix seconds
    paired: bool = False  # True if a matching 30411 was found within 14d
    counterparty_status: str | None = None  # status reported by the OTHER side, if paired


@dataclass(frozen=True)
class AdminDecisionRecord:
    """A kind 30430 admin-decision about the target."""

    dispute_id: str
    admin_pubkey: str
    affected_pubkey: str
    related_event_id: str
    pack: str
    decision: str  # clear|warning|flag|escalated
    severity: str  # low|moderate|high
    reason_hash: str
    appeal_until: int
    has_open_appeal: bool = False


@dataclass(frozen=True)
class ScoringReport:
    """Final aggregate plus the breakdown that produced it."""

    score: float
    score_components: dict[str, float] = field(default_factory=dict)
    wot_distance: int | None = None
    red_flags: list[str] = field(default_factory=list)
    green_flags: list[str] = field(default_factory=list)
    # raw per-layer signed scores in [-1, 1] before layer-weighting,
    # surfaced for the buyer skill's "why" panel.
    layer_scores: dict[str, float] = field(default_factory=dict)
    attestation_summary: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def wot_distance(
    user_pubkey: str,
    counterparty_pubkey: str,
    graph: dict[str, set[str]],
    *,
    max_depth: int = 4,
) -> int | None:
    """Return graph distance (NIP-02 follow hops) from user to target.

    BFS over the contact graph. Returns 0 for self, the smallest
    integer hop count if reachable within `max_depth`, or None if
    not reachable.
    """
    if user_pubkey == counterparty_pubkey:
        return 0
    if user_pubkey not in graph:
        return None
    visited: set[str] = {user_pubkey}
    queue: deque[tuple[str, int]] = deque([(user_pubkey, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for neighbour in graph.get(node, set()):
            if neighbour == counterparty_pubkey:
                return depth + 1
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append((neighbour, depth + 1))
    return None


def wot_weight(
    user_pubkey: str,
    signer_pubkey: str,
    graph: dict[str, set[str]],
    badge_holders: Iterable[str],
    *,
    distances: dict[str, float] | None = None,
) -> float:
    """The per-signer trust weight from `scoring.md`."""
    distances = distances or DEFAULT_WOT_DISTANCE
    if signer_pubkey == user_pubkey:
        return 1.0
    user_contacts = graph.get(user_pubkey, set())
    if signer_pubkey in user_contacts:
        return distances["direct"]
    signer_contacts = graph.get(signer_pubkey, set())
    if user_contacts & signer_contacts:
        return distances["two_hop_shared_contact"]
    if signer_pubkey in set(badge_holders):
        return distances["verified_badge_unknown"]
    return distances["unknown"]


# ---------------------------------------------------------------------------
# Layer scoring (each returns a value in [-1, 1])
# ---------------------------------------------------------------------------


def _badge_layer(
    badges: list[BadgeRecord],
    trust_issuers: dict[str, float],
    *,
    red_flags: list[str],
    green_flags: list[str],
) -> float:
    """`scoring.md` badges layer.

    A revoked badge issued by a trusted issuer is a hard negative
    signal. A live badge from a trusted issuer raises the score by
    that issuer's trust weight (capped at 1.0).
    """
    score = 0.0
    for b in badges:
        weight = trust_issuers.get(b.issuer_pubkey)
        if b.revoked:
            score -= 0.5
            if weight is not None:
                red_flags.append(
                    f"operator badge revoked by trusted issuer "
                    f"{b.issuer_pubkey[:12]}...{b.badge_id}"
                )
            else:
                red_flags.append(f"badge revoked by issuer {b.issuer_pubkey[:12]}...")
            continue
        if weight is not None and weight > 0:
            if weight > score:
                score = weight
            green_flags.append(f"badge {b.badge_id!r} held, issuer trust={weight:.2f}")
    return _clamp(score, -1.0, 1.0)


def _attestation_layer(
    attestations: list[AttestationRecord],
    user_pubkey: str,
    graph: dict[str, set[str]],
    badge_holders: set[str],
    *,
    decay_days: int,
    distances: dict[str, float],
    now: int,
    red_flags: list[str],
    green_flags: list[str],
    summary: dict[str, int],
) -> float:
    """`scoring.md` attestation layer.

    Paired (30410+30411) `completed-clean` adds up to +0.05 each
    weighted by counterparty's WoT-weight × time decay. Paired
    `disputed` subtracts 0.15 × WoT-weight. Unilateral 30412
    subtracts 0.07 × WoT-weight (half a paired one).
    """
    score = 0.0
    completed = 0
    disputed = 0
    vanished = 0

    for a in attestations:
        if a.signer_pubkey == a.subject_pubkey:
            continue  # self-attestation is meaningless
        age_days = max(0, (now - a.sale_closed_at) / SECONDS_PER_DAY)
        decay = max(0.0, 1.0 - age_days / decay_days)
        w = wot_weight(user_pubkey, a.signer_pubkey, graph, badge_holders, distances=distances)

        if a.kind == 30412:
            score -= 0.07 * w
            vanished += 1
            continue

        if a.kind == 30410 and a.paired:
            if a.status == "completed-clean" and a.counterparty_status == "confirmed":
                score += min(0.05, 0.05 * w * decay)
                completed += 1
            elif a.status == "disputed-by-me" or a.counterparty_status == "disputed":
                score -= 0.15 * w
                disputed += 1
                red_flags.append(f"paired-disputed attestation from {a.signer_pubkey[:12]}...")
            # mismatched pair (one says clean, the other disputed):
            # `scoring.md` flags it but contributes no positive evidence.
            elif a.status != a.counterparty_status:
                red_flags.append(f"mismatched attestation pair sale={a.sale_id[:8]}...")

    summary["completed_clean"] = completed
    summary["disputed"] = disputed
    summary["vanished"] = vanished

    if completed >= 5:
        green_flags.append(f"{completed} clean paired attestations")

    return _clamp(score, -1.0, 1.0)


def _admin_layer(
    decisions: list[AdminDecisionRecord],
    admin_trust: dict[str, float],
    *,
    red_flags: list[str],
    green_flags: list[str],
) -> float:
    """`scoring.md` admin-decisions layer."""
    score = 0.0
    for d in decisions:
        if d.admin_pubkey not in admin_trust:
            continue
        weight = admin_trust[d.admin_pubkey]
        if d.has_open_appeal:
            weight *= 0.5
        sev_mult = SEVERITY_MULT.get(d.severity, 0.0)
        match d.decision:
            case "clear":
                score += 0.10 * weight
                green_flags.append(f"admin clear by {d.admin_pubkey[:12]}... (weight {weight:.2f})")
            case "warning":
                score -= 0.20 * weight * sev_mult
                red_flags.append(f"admin warning, severity={d.severity}")
            case "flag":
                score -= 0.50 * weight * sev_mult
                red_flags.append(f"admin flag, severity={d.severity}")
            case "escalated":
                # neutral by design — awaiting human review.
                pass
    return _clamp(score, -1.0, 1.0)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def aggregate_score(
    *,
    badges: list[BadgeRecord],
    attestations: list[AttestationRecord],
    admin_decisions: list[AdminDecisionRecord],
    wot_graph: dict[str, set[str]],
    user_pubkey: str,
    counterparty_pubkey: str,
    admin_trust: dict[str, float],
    onchain_stake: object | None = None,
    layer_weights: dict[str, float] | None = None,
    trust_issuers: dict[str, float] | None = None,
    wot_distances: dict[str, float] | None = None,
    attestation_decay_days: int = DEFAULT_ATTESTATION_DECAY_DAYS,
    mute_score: float = 0.0,
    now: int | None = None,
) -> ScoringReport:
    """Collapse layered signals into a single ScoringReport.

    All inputs are pure dataclasses; this function performs no I/O.
    See `reputation/scoring.md` for the per-layer formulas.
    """
    if onchain_stake is not None:
        # Phase 1 staking is roadmap, not MVP — we still accept the
        # parameter for forward-compat but never let it influence
        # the score.
        pass
    layer_weights = layer_weights or DEFAULT_LAYER_WEIGHTS
    trust_issuers = trust_issuers or {}
    wot_distances = wot_distances or DEFAULT_WOT_DISTANCE
    now_ts = now if now is not None else int(time.time())

    red_flags: list[str] = []
    green_flags: list[str] = []
    summary: dict[str, int] = {"completed_clean": 0, "disputed": 0, "vanished": 0}

    # Pubkeys that hold any (non-revoked) badge — used by the
    # WoT-weight fallback for "verified-badge unknown" signers.
    badge_holders: set[str] = {b.issuer_pubkey for b in badges if not b.revoked}
    badge_holders.add(counterparty_pubkey) if any(
        not b.revoked for b in badges
    ) else None  # the target itself when it holds a live badge

    badge_score = _badge_layer(badges, trust_issuers, red_flags=red_flags, green_flags=green_flags)
    att_score = _attestation_layer(
        attestations,
        user_pubkey,
        wot_graph,
        badge_holders,
        decay_days=attestation_decay_days,
        distances=wot_distances,
        now=now_ts,
        red_flags=red_flags,
        green_flags=green_flags,
        summary=summary,
    )
    admin_score = _admin_layer(
        admin_decisions,
        admin_trust,
        red_flags=red_flags,
        green_flags=green_flags,
    )
    mute_layer_score = _clamp(mute_score, -1.0, 1.0)
    stake_score = 0.0  # Phase 1 — always 0 in MVP

    raw = (
        layer_weights["badges"] * badge_score
        + layer_weights["attestations"] * att_score
        + layer_weights["admin_decisions"] * admin_score
        + layer_weights["mute_signal"] * mute_layer_score
        + layer_weights["onchain_stake"] * stake_score
    )
    aggregate = _clamp((raw + 1.0) / 2.0, 0.0, 1.0)

    distance = wot_distance(user_pubkey, counterparty_pubkey, wot_graph)

    return ScoringReport(
        score=aggregate,
        score_components={
            "badge_score": layer_weights["badges"] * badge_score,
            "att_score": layer_weights["attestations"] * att_score,
            "admin_score": layer_weights["admin_decisions"] * admin_score,
            "mute_score": layer_weights["mute_signal"] * mute_layer_score,
            "stake_score": layer_weights["onchain_stake"] * stake_score,
        },
        wot_distance=distance,
        red_flags=red_flags,
        green_flags=green_flags,
        layer_scores={
            "badge_score": badge_score,
            "att_score": att_score,
            "admin_score": admin_score,
            "mute_score": mute_layer_score,
            "stake_score": stake_score,
        },
        attestation_summary=summary,
    )
