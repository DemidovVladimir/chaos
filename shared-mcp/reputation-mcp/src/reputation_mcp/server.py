"""reputation-mcp — layered trust-signal aggregation MCP server.

Implements the four tools documented in `manifest.yaml`:

- `get_reputation` — aggregates badges (NIP-58), peer attestations
  (custom kinds 30410+30411+30412), admin decisions (kind 30430),
  and an NIP-02 web-of-trust walk into a `ScoringReport`. Reads
  only — no relay-side writes.
- `submit_peer_attestation` — publishes a kind 30410 sale-attestation.
- `submit_counter_attestation` — publishes a kind 30411 counter
  to a prior 30410.
- `submit_dispute_attestation` — publishes a kind 30412 unilateral
  dispute when the counterparty refuses to acknowledge a sale.

Honors AGENTS.md rules:

  - Rule 1 (Nostr-only discovery)   — relays only, no central DB.
  - Rule 2 (MCP-only binary)        — no binary content here at all.
  - Rule 3 (sovereign identity)     — `signing_key_hex` parameter
                                      is required for every submit;
                                      keys never leave the calling
                                      agent's local keystore.
  - Rule 4 (layered trust)          — multiple signals composed,
                                      none gatekept.
  - Rule 5 (no data custody)        — query results live only in
                                      the in-flight request.
  - Rule 7 (input safety)           — every untrusted string field
                                      passes through `_sanitize`
                                      before use.

See `reputation/scoring.md` for the algorithm and
`reputation/kinds.md` for the kind-number registry.
"""

from __future__ import annotations

# --- macOS / generic SSL preamble ---------------------------------------
import os

try:
    import certifi as _certifi

    _ca = _certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", _ca)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _ca)
    os.environ.setdefault("WEBSOCKET_CLIENT_CA_BUNDLE", _ca)
except ImportError:
    pass

import logging
import re
import sys
import time
import unicodedata
from typing import Any

from mcp.server.fastmcp import FastMCP

from .relay_client import (
    ReputationRelayClient,
    filter_for_authors,
    filter_for_event_tag,
    filter_for_pubkey_tag,
)
from .scoring import (
    AdminDecisionRecord,
    AttestationRecord,
    BadgeRecord,
    ScoringReport,
    aggregate_score,
)

# ------------------------------------------------------------------
# Module setup
# ------------------------------------------------------------------

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[reputation-mcp] %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("reputation-mcp")

NAME = "reputation-mcp"
HOST = os.environ.get("REPUTATION_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("REPUTATION_MCP_PORT", "7612"))

mcp = FastMCP(NAME, host=HOST, port=PORT)

DEFAULT_RELAYS: list[str] = [
    r.strip()
    for r in os.environ.get(
        "REPUTATION_MCP_RELAYS",
        "wss://relay.damus.io,wss://nos.lol,wss://relay.nostr.band",
    ).split(",")
    if r.strip()
]

# ------------------------------------------------------------------
# Input safety — replicated locally per AGENTS.md guidance to keep
# this MCP component installable independent of the rest of the
# repo. Mirrors `shared/input_safety.py` shape.
# ------------------------------------------------------------------

_RESERVED_TAGS = (
    "system",
    "assistant",
    "untrusted",
    "memory",
    "context",
    "tool",
    "policy",
    "secret",
)
_RESERVED_TAG_RE = re.compile(
    r"</?(?:" + "|".join(_RESERVED_TAGS) + r")\b[^>]*>",
    flags=re.IGNORECASE,
)
_INVISIBLE_RE = re.compile(r"[​-‏‪-‮⁠-⁤﻿]")
_INJECTION_PHRASES = (
    "ignore previous instructions",
    "disregard all prior",
    "you are now",
    "system prompt",
)


def _sanitize(text: str, *, max_bytes: int = 1024) -> str:
    """NFKC-normalize, strip invisible Unicode + reserved tags, length-cap."""
    if not isinstance(text, str):
        text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE_RE.sub("", text)
    text = _RESERVED_TAG_RE.sub("", text)
    encoded = text.encode("utf-8")[:max_bytes]
    text = encoded.decode("utf-8", errors="ignore")
    lower = text.lower()
    for phrase in _INJECTION_PHRASES:
        if phrase in lower:
            log.warning("input_safety: injection phrase scrubbed: %r", phrase)
            text = text.replace(phrase, "[redacted]")
            text = text.replace(phrase.upper(), "[redacted]")
    return text


# ------------------------------------------------------------------
# Allowlists — refuse unknown enum values rather than passing through
# ------------------------------------------------------------------

ALLOWED_30410_STATUS = frozenset(
    {
        "completed-clean",
        "disputed-by-me",
        "counterparty-vanished",
    }
)
ALLOWED_30411_STATUS = frozenset({"confirmed", "disputed"})
ALLOWED_DECISION = frozenset({"clear", "warning", "flag", "escalated"})
ALLOWED_SEVERITY = frozenset({"low", "moderate", "high"})
PACK_RE = re.compile(r"^[a-z][a-z0-9-]+@[0-9]+$")
PUBKEY_RE = re.compile(r"^[0-9a-f]{64}$")
EVENT_ID_RE = re.compile(r"^[0-9a-f]{64}$")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    flags=re.IGNORECASE,
)
DIGIT_RUN_RE = re.compile(r"\d{4,}")


def _require_pubkey(value: str, *, field: str) -> str:
    if not PUBKEY_RE.match(value or ""):
        raise ValueError(f"{field} must be 64-hex secp256k1 pubkey")
    return value.lower()


def _require_event_id(value: str, *, field: str) -> str:
    if not EVENT_ID_RE.match(value or ""):
        raise ValueError(f"{field} must be 64-hex event-id")
    return value.lower()


def _require_uuid(value: str, *, field: str) -> str:
    if not UUID_RE.match(value or ""):
        raise ValueError(f"{field} must be UUID v4")
    return value.lower()


def _require_pack(value: str) -> str:
    if not PACK_RE.match(value or ""):
        raise ValueError("pack must match '<name>@<version>'")
    return value


def _require_currency_band(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("currency_band must be a string")
    if DIGIT_RUN_RE.search(value):
        raise ValueError("currency_band must be a band, not an exact number")
    return value


def _allowed(value: str, allowed: frozenset[str], *, field: str) -> str:
    if value not in allowed:
        raise ValueError(f"{field}={value!r} not in {sorted(allowed)}")
    return value


# ------------------------------------------------------------------
# Event-tag helpers
# ------------------------------------------------------------------


def _tag_value(event: Any, name: str) -> str | None:
    for tag in getattr(event, "tags", []) or []:
        if tag and len(tag) >= 2 and tag[0] == name:
            return tag[1]
    return None


def _tag_values(event: Any, name: str) -> list[str]:
    out: list[str] = []
    for tag in getattr(event, "tags", []) or []:
        if tag and len(tag) >= 2 and tag[0] == name:
            out.append(tag[1])
    return out


# ------------------------------------------------------------------
# Relay -> domain dataclasses
# ------------------------------------------------------------------


def _build_badge_records(
    award_events: list[Any],
    deletion_events: list[Any],
    flag_events: list[Any],
) -> list[BadgeRecord]:
    """Per `operator_revocation.md` a revocation is the *pair*
    (NIP-09 deletion + kind-30430 flag). Either alone is insufficient.
    """
    deleted_event_ids: set[str] = set()
    for de in deletion_events:
        for eid in _tag_values(de, "e"):
            deleted_event_ids.add(eid.lower())
    flagged_event_ids: set[str] = set()
    flag_at_by_event: dict[str, int] = {}
    for fe in flag_events:
        decision = _tag_value(fe, "decision")
        if decision != "flag":
            continue
        for eid in _tag_values(fe, "e"):
            flagged_event_ids.add(eid.lower())
            flag_at_by_event[eid.lower()] = int(getattr(fe, "created_at", 0) or 0)

    records: list[BadgeRecord] = []
    for ev in award_events:
        award_id = (getattr(ev, "id", "") or "").lower()
        if not award_id:
            continue
        a_tag = _tag_value(ev, "a") or ""
        # NIP-58 award `a` tag shape: "30009:<issuer>:<badge_id>"
        parts = a_tag.split(":", 2)
        if len(parts) >= 3 and parts[0] == "30009":
            issuer = parts[1].lower()
            badge_id = parts[2]
        else:
            issuer = (getattr(ev, "pubkey", "") or "").lower()
            badge_id = a_tag or "unknown"
        revoked = award_id in deleted_event_ids and award_id in flagged_event_ids
        records.append(
            BadgeRecord(
                issuer_pubkey=issuer,
                badge_id=badge_id,
                award_event_id=award_id,
                revoked=revoked,
                revoked_at=flag_at_by_event.get(award_id) if revoked else None,
            )
        )
    return records


def _build_attestation_records(
    raw: list[Any],
    target: str,
) -> list[AttestationRecord]:
    """Pair 30410+30411 events on shared `d` tag within 14 days."""
    by_kind: dict[int, list[Any]] = {30410: [], 30411: [], 30412: []}
    for ev in raw:
        k = int(getattr(ev, "kind", 0) or 0)
        if k in by_kind:
            by_kind[k].append(ev)

    # Index 30411s by (counterparty d, e-tag-pointing-at-30410-id)
    by_d_30411: dict[str, list[Any]] = {}
    for ev in by_kind[30411]:
        d = _tag_value(ev, "d") or ""
        by_d_30411.setdefault(d, []).append(ev)

    records: list[AttestationRecord] = []

    for ev in by_kind[30410]:
        d = _tag_value(ev, "d") or ""
        signer = (getattr(ev, "pubkey", "") or "").lower()
        cp_p = (_tag_value(ev, "p") or "").lower()
        listing_e = (_tag_value(ev, "e") or "").lower()
        pack = _tag_value(ev, "pack") or ""
        status = _tag_value(ev, "status") or ""
        sale_closed = int(_tag_value(ev, "sale_closed_at") or "0")
        # Subject is whichever of {signer, cp_p} matches `target`.
        subject = target.lower()

        if status not in ALLOWED_30410_STATUS:
            continue  # silently drop malformed

        paired = False
        cp_status: str | None = None
        # Look for a matching 30411 with the same d, signed by the cp.
        for cev in by_d_30411.get(d, []):
            cev_signer = (getattr(cev, "pubkey", "") or "").lower()
            if cev_signer != cp_p:
                continue
            if (_tag_value(cev, "p") or "").lower() != signer:
                continue
            ev_ts = int(getattr(ev, "created_at", 0) or 0)
            cev_ts = int(getattr(cev, "created_at", 0) or 0)
            if abs(cev_ts - ev_ts) > 14 * 86400:
                continue
            paired = True
            cp_status = _tag_value(cev, "status")
            if cp_status not in ALLOWED_30411_STATUS:
                cp_status = None
                paired = False
            break

        records.append(
            AttestationRecord(
                kind=30410,
                sale_id=d,
                signer_pubkey=signer,
                subject_pubkey=cp_p if signer == subject else subject,
                listing_event_id=listing_e,
                pack=pack,
                status=status,
                sale_closed_at=sale_closed,
                paired=paired,
                counterparty_status=cp_status,
            )
        )

    for ev in by_kind[30412]:
        signer = (getattr(ev, "pubkey", "") or "").lower()
        cp_p = (_tag_value(ev, "p") or "").lower()
        records.append(
            AttestationRecord(
                kind=30412,
                sale_id=_tag_value(ev, "d") or "",
                signer_pubkey=signer,
                subject_pubkey=cp_p,
                listing_event_id=(_tag_value(ev, "e") or "").lower(),
                pack=_tag_value(ev, "pack") or "",
                status=_tag_value(ev, "status") or "counterparty-vanished",
                sale_closed_at=int(_tag_value(ev, "sale_closed_at") or "0"),
                paired=False,
                counterparty_status=None,
            )
        )

    return records


def _build_admin_records(
    decisions: list[Any],
    appeals: list[Any],
    target: str,
) -> list[AdminDecisionRecord]:
    """Match each 30430 to any 30431 referencing it for has_open_appeal."""
    open_appeal_for: set[str] = set()
    now_ts = int(time.time())
    for ap in appeals:
        e_tag = (_tag_value(ap, "e") or "").lower()
        if e_tag:
            open_appeal_for.add(e_tag)

    records: list[AdminDecisionRecord] = []
    target_lc = target.lower()
    for d in decisions:
        decision_value = _tag_value(d, "decision") or ""
        severity = _tag_value(d, "severity") or "low"
        if decision_value not in ALLOWED_DECISION:
            continue
        if severity not in ALLOWED_SEVERITY:
            severity = "low"
        affected = [p.lower() for p in _tag_values(d, "p")]
        if target_lc not in affected:
            continue
        decision_event_id = (getattr(d, "id", "") or "").lower()
        appeal_until = int(_tag_value(d, "appeal_until") or "0")
        has_appeal = decision_event_id in open_appeal_for and (
            appeal_until == 0 or appeal_until > now_ts
        )
        records.append(
            AdminDecisionRecord(
                dispute_id=_tag_value(d, "d") or "",
                admin_pubkey=(getattr(d, "pubkey", "") or "").lower(),
                affected_pubkey=target_lc,
                related_event_id=(_tag_value(d, "e") or "").lower(),
                pack=_tag_value(d, "pack") or "",
                decision=decision_value,
                severity=severity,
                reason_hash=_tag_value(d, "reason_hash") or "",
                appeal_until=appeal_until,
                has_open_appeal=has_appeal,
            )
        )
    return records


def _build_wot_graph(
    contact_events: list[Any],
) -> dict[str, set[str]]:
    """Convert kind-3 contact-list events into an adjacency map."""
    graph: dict[str, set[str]] = {}
    # If multiple kind-3 events arrive for the same author, keep the
    # newest only (kind 3 is replaceable per NIP-01).
    newest_by_author: dict[str, Any] = {}
    for ev in contact_events:
        if int(getattr(ev, "kind", 0) or 0) != 3:
            continue
        author = (getattr(ev, "pubkey", "") or "").lower()
        ts = int(getattr(ev, "created_at", 0) or 0)
        if author not in newest_by_author or ts > int(
            getattr(newest_by_author[author], "created_at", 0) or 0
        ):
            newest_by_author[author] = ev
    for author, ev in newest_by_author.items():
        contacts = {p.lower() for p in _tag_values(ev, "p") if PUBKEY_RE.match(p)}
        graph[author] = contacts
    return graph


# ------------------------------------------------------------------
# Phase 1 stake hook (placeholder; never reads in MVP)
# ------------------------------------------------------------------


def _check_onchain_stake() -> None:  # pragma: no cover — placeholder
    """Phase 1 staking is roadmap, not MVP. Always returns None.

    See `reputation/STAKE.md`.
    """
    return None


# ------------------------------------------------------------------
# Tools
# ------------------------------------------------------------------


@mcp.tool()
def get_reputation(
    pubkey: str,
    vertical_pack: str = "cars-pack@1",
    relays: list[str] | None = None,
    user_pubkey: str | None = None,
    admin_trust: dict[str, float] | None = None,
    trust_issuers: dict[str, float] | None = None,
) -> dict:
    """Aggregate the layered reputation signals for `pubkey`.

    Args:
        pubkey: hex-encoded secp256k1 pubkey to score.
        vertical_pack: e.g. "cars-pack@1"; informational, the score
            ranges across kinds for now.
        relays: optional override of the relay list this query
            visits. Defaults to env REPUTATION_MCP_RELAYS or the
            three public-relay defaults.
        user_pubkey: viewer's pubkey, used to anchor the WoT walk.
            If omitted, all signers fall into the "unknown" weight
            bucket per `scoring.md`.
        admin_trust: dict of admin pubkey -> trust weight in [0, 1].
            An admin pubkey absent from this dict is ignored
            entirely (opt-in trust per Rule 16).
        trust_issuers: dict of NIP-58 issuer pubkey -> trust weight.

    Returns:
        Dict matching the shape documented in
        `reputation/scoring.md` plus a `wot_distance` field.
        `onchain_stake` is always None in MVP.
    """
    target = _require_pubkey(pubkey, field="pubkey")
    pack = _require_pack(vertical_pack)
    used_relays = relays or DEFAULT_RELAYS
    user_pk = _require_pubkey(user_pubkey, field="user_pubkey") if user_pubkey else ""
    admin_trust = admin_trust or {}
    trust_issuers = trust_issuers or {}

    log.info(
        "get_reputation target=%s... pack=%s viewer=%s relays=%d",
        target[:12],
        pack,
        "yes" if user_pk else "anon",
        len(used_relays),
    )

    with ReputationRelayClient(used_relays) as client:
        # ----- 1. NIP-58 badges issued *to* target ---------------
        badge_filter = filter_for_pubkey_tag(kinds=[8], pubkey_hex=target, limit=200)
        badge_events = client.query_events([badge_filter], timeout_seconds=4.0)

        award_event_ids = [
            (getattr(b, "id", "") or "").lower() for b in badge_events if getattr(b, "id", None)
        ]

        # ----- 2. NIP-09 deletions referencing those awards -------
        deletion_events: list[Any] = []
        if award_event_ids:
            del_filter = filter_for_event_tag(kinds=[5], event_id_hex=award_event_ids[0], limit=200)
            # add the rest of the e-tags via add_arbitrary_tag
            for eid in award_event_ids[1:]:
                del_filter.add_arbitrary_tag("e", [eid])
            deletion_events = client.query_events([del_filter], timeout_seconds=3.0)

        # ----- 3. peer + admin events about target ----------------
        att_filter = filter_for_pubkey_tag(
            kinds=[30410, 30411, 30412], pubkey_hex=target, limit=500
        )
        # 30411 also references the seller's 30410 by `e`, so also
        # query 30410s where target is the *signer* (signer-side).
        att_authored = filter_for_authors(kinds=[30410, 30411, 30412], authors=[target], limit=500)
        admin_filter = filter_for_pubkey_tag(kinds=[30430], pubkey_hex=target, limit=200)
        appeal_filter = filter_for_pubkey_tag(kinds=[30431], pubkey_hex=target, limit=200)

        peer_events = client.query_events([att_filter, att_authored], timeout_seconds=4.0)
        admin_events = client.query_events([admin_filter], timeout_seconds=3.0)
        appeal_events = client.query_events([appeal_filter], timeout_seconds=2.0)

        # Flag-events for badge revocation are kind 30430 too,
        # filtered to those referencing badge-award event ids.
        flag_events: list[Any] = []
        if award_event_ids:
            flag_filter = filter_for_event_tag(
                kinds=[30430], event_id_hex=award_event_ids[0], limit=200
            )
            for eid in award_event_ids[1:]:
                flag_filter.add_arbitrary_tag("e", [eid])
            flag_events = client.query_events([flag_filter], timeout_seconds=2.0)

        # ----- 4. WoT graph (NIP-02 contact lists) -----------------
        wot_graph: dict[str, set[str]] = {}
        if user_pk:
            seed_filter = filter_for_authors(kinds=[3], authors=[user_pk], limit=5)
            seed_events = client.query_events([seed_filter], timeout_seconds=2.0)
            wot_graph = _build_wot_graph(seed_events)
            # depth-2 walk: fetch contact-of-contact lists
            second_hop = list(wot_graph.get(user_pk, set()))[:50]
            if second_hop:
                hop_filter = filter_for_authors(kinds=[3], authors=second_hop, limit=200)
                hop_events = client.query_events([hop_filter], timeout_seconds=3.0)
                hop_graph = _build_wot_graph(hop_events)
                for k, v in hop_graph.items():
                    wot_graph.setdefault(k, set()).update(v)

    badges = _build_badge_records(badge_events, deletion_events, flag_events)
    attestations = _build_attestation_records(peer_events, target)
    decisions = _build_admin_records(admin_events, appeal_events, target)

    report: ScoringReport = aggregate_score(
        badges=badges,
        attestations=attestations,
        admin_decisions=decisions,
        wot_graph=wot_graph,
        user_pubkey=user_pk or target,
        counterparty_pubkey=target,
        admin_trust=admin_trust,
        trust_issuers=trust_issuers,
        onchain_stake=_check_onchain_stake(),
    )

    return {
        "pubkey": target,
        "vertical_pack": pack,
        "score_aggregate": report.score,
        "components": report.score_components,
        "layer_scores": report.layer_scores,
        "wot_distance": report.wot_distance,
        "red_flags": report.red_flags,
        "green_flags": report.green_flags,
        "attestations": report.attestation_summary,
        "badges": [
            {
                "issuer": b.issuer_pubkey,
                "badge_id": b.badge_id,
                "revoked": b.revoked,
            }
            for b in badges
        ],
        "admin_decisions": [
            {
                "dispute_id": d.dispute_id,
                "admin": d.admin_pubkey,
                "decision": d.decision,
                "severity": d.severity,
                "has_open_appeal": d.has_open_appeal,
            }
            for d in decisions
        ],
        "onchain_stake": None,  # Phase 1; see reputation/STAKE.md
    }


# ------------------------------------------------------------------
# Submit tools — all require `signing_key_hex`
# ------------------------------------------------------------------


def _build_signed_event(
    *,
    kind: int,
    pubkey: str,
    tags: list[list[str]],
    content: str,
    signing_key_hex: str,
) -> Any:
    """Construct, sign, and return a pynostr Event."""
    from pynostr.event import Event

    event = Event(
        kind=kind,
        pubkey=pubkey,
        content=content,
        tags=tags,
        created_at=int(time.time()),
    )
    event.sign(signing_key_hex)
    return event


def _publish_or_die(
    event: Any,
    relays: list[str],
) -> str:
    """Publish a signed event to `relays` and return its id."""
    with ReputationRelayClient(relays) as client:
        client.publish_event(event)
    return getattr(event, "id", "")


def _resolve_signer(signing_key_hex: str | None) -> tuple[str, str]:
    """Return (sk_hex, pk_hex). Refuse if no signing key provided.

    The returned `sk_hex` is intentionally NOT logged anywhere in
    this module; the caller-facing log messages identify the signer
    only by the public-key prefix.
    """
    if not signing_key_hex:
        raise ValueError(
            "signing_key_hex is required — reputation-mcp refuses to publish unsigned events"
        )
    if not re.match(r"^[0-9a-f]{64}$", signing_key_hex):
        raise ValueError("signing_key_hex must be 64 hex chars")
    from pynostr.key import PrivateKey

    sk = PrivateKey.from_hex(signing_key_hex)
    return signing_key_hex, sk.public_key.hex()


@mcp.tool()
def submit_peer_attestation(
    sale_id: str,
    counterparty_pubkey: str,
    listing_event_id: str,
    status: str,
    currency_band: str = "",
    pack: str = "cars-pack@1",
    relays: list[str] | None = None,
    signing_key_hex: str | None = None,
    note: str = "",
) -> str:
    """Publish a kind-30410 sale-attestation.

    `signing_key_hex` is required; this MCP refuses to publish
    unsigned. Returns the published event id (hex).
    """
    sale_id = _require_uuid(sale_id, field="sale_id")
    counterparty = _require_pubkey(counterparty_pubkey, field="counterparty_pubkey")
    listing_e = _require_event_id(listing_event_id, field="listing_event_id")
    status = _allowed(status, ALLOWED_30410_STATUS, field="status")
    pack = _require_pack(pack)
    if currency_band:
        currency_band = _require_currency_band(currency_band)
    sk_hex, pk_hex = _resolve_signer(signing_key_hex)
    if pk_hex == counterparty:
        raise ValueError("counterparty_pubkey must differ from signer")
    used_relays = relays or DEFAULT_RELAYS

    tags: list[list[str]] = [
        ["d", sale_id],
        ["e", listing_e],
        ["p", counterparty],
        ["pack", pack],
        ["status", status],
        ["sale_closed_at", str(int(time.time()))],
    ]
    if currency_band:
        tags.append(["currency_band", currency_band])

    safe_note = _sanitize(note, max_bytes=1024)
    event = _build_signed_event(
        kind=30410,
        pubkey=pk_hex,
        tags=tags,
        content=safe_note,
        signing_key_hex=sk_hex,
    )
    event_id = _publish_or_die(event, used_relays)
    log.info(
        "submit_peer_attestation OK sale_id=%s signer=%s... cp=%s... status=%s",
        sale_id,
        pk_hex[:12],
        counterparty[:12],
        status,
    )
    return event_id


@mcp.tool()
def submit_counter_attestation(
    sale_id: str,
    seller_attestation_event_id: str,
    seller_pubkey: str,
    status: str,
    pack: str = "cars-pack@1",
    relays: list[str] | None = None,
    signing_key_hex: str | None = None,
    note: str = "",
) -> str:
    """Publish a kind-30411 counter-attestation referencing a 30410.

    Args:
        sale_id: same UUID as the parent 30410's `d` tag.
        seller_attestation_event_id: id of the 30410 being countered.
        seller_pubkey: pubkey of the original 30410's publisher.
        status: `confirmed` or `disputed`.
    """
    sale_id = _require_uuid(sale_id, field="sale_id")
    parent_id = _require_event_id(seller_attestation_event_id, field="seller_attestation_event_id")
    seller = _require_pubkey(seller_pubkey, field="seller_pubkey")
    status = _allowed(status, ALLOWED_30411_STATUS, field="status")
    pack = _require_pack(pack)
    sk_hex, pk_hex = _resolve_signer(signing_key_hex)
    if pk_hex == seller:
        raise ValueError("counter-attestation must be signed by the OTHER party")
    used_relays = relays or DEFAULT_RELAYS

    tags = [
        ["d", sale_id],
        ["e", parent_id],
        ["p", seller],
        ["pack", pack],
        ["status", status],
    ]
    safe_note = _sanitize(note, max_bytes=1024)
    event = _build_signed_event(
        kind=30411,
        pubkey=pk_hex,
        tags=tags,
        content=safe_note,
        signing_key_hex=sk_hex,
    )
    event_id = _publish_or_die(event, used_relays)
    log.info(
        "submit_counter_attestation OK sale_id=%s signer=%s... seller=%s... status=%s",
        sale_id,
        pk_hex[:12],
        seller[:12],
        status,
    )
    return event_id


@mcp.tool()
def submit_dispute_attestation(
    sale_id: str,
    counterparty_pubkey: str,
    listing_event_id: str,
    reason_short: str,
    currency_band: str = "",
    pack: str = "cars-pack@1",
    relays: list[str] | None = None,
    signing_key_hex: str | None = None,
    note: str = "",
) -> str:
    """Publish a kind-30412 unilateral dispute-attestation.

    Used when the counterparty refuses to publish a 30411 (e.g. a
    vanished seller). Carries half the weight of a paired
    attestation per `reputation/scoring.md`.
    """
    sale_id = _require_uuid(sale_id, field="sale_id")
    counterparty = _require_pubkey(counterparty_pubkey, field="counterparty_pubkey")
    listing_e = _require_event_id(listing_event_id, field="listing_event_id")
    pack = _require_pack(pack)
    safe_reason = _sanitize(reason_short, max_bytes=80)
    if not safe_reason:
        raise ValueError("reason_short is required")
    if currency_band:
        currency_band = _require_currency_band(currency_band)
    sk_hex, pk_hex = _resolve_signer(signing_key_hex)
    if pk_hex == counterparty:
        raise ValueError("counterparty_pubkey must differ from signer")
    used_relays = relays or DEFAULT_RELAYS

    tags: list[list[str]] = [
        ["d", sale_id],
        ["e", listing_e],
        ["p", counterparty],
        ["pack", pack],
        ["status", "counterparty-vanished"],
        ["sale_closed_at", str(int(time.time()))],
        ["reason_short", safe_reason],
    ]
    if currency_band:
        tags.append(["currency_band", currency_band])

    safe_note = _sanitize(note, max_bytes=1024)
    event = _build_signed_event(
        kind=30412,
        pubkey=pk_hex,
        tags=tags,
        content=safe_note,
        signing_key_hex=sk_hex,
    )
    event_id = _publish_or_die(event, used_relays)
    log.info(
        "submit_dispute_attestation OK sale_id=%s signer=%s... cp=%s...",
        sale_id,
        pk_hex[:12],
        counterparty[:12],
    )
    return event_id


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------


def main() -> None:
    log.info("starting %s on %s:%d", NAME, HOST, PORT)
    mcp.run()


if __name__ == "__main__":
    main()
