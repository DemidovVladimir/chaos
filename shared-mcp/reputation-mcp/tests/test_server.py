"""Unit tests for reputation-mcp.

Covers the pure scoring algorithm (no relay round-trips), the
WoT-distance helper, and the input-validation layer of the submit
tools. Relay I/O is mocked end-to-end — we never open a socket.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from reputation_mcp.scoring import (
    AdminDecisionRecord,
    AttestationRecord,
    BadgeRecord,
    aggregate_score,
    wot_distance,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# 64-hex pubkeys for fixture readability.
ALICE = "a" * 64
BOB   = "b" * 64
CAROL = "c" * 64
DAVE  = "d" * 64

# For tests that talk about an "admin" or "issuer" we use distinct
# constants to keep the role obvious in failure output.
ADMIN1   = "f" * 64
ADMIN2   = "e" * 64
ISSUER1  = "1" * 64

NOW_TS = 1_714_800_000  # fixed clock for deterministic decay


def _attestation(
    *,
    signer: str,
    subject: str,
    paired: bool = True,
    status: str = "completed-clean",
    cp_status: str | None = "confirmed",
    sale_closed_at: int = NOW_TS - 86400 * 30,
    sale_id: str | None = None,
    kind: int = 30410,
) -> AttestationRecord:
    return AttestationRecord(
        kind=kind,
        sale_id=sale_id or f"sale-{signer[:4]}-{subject[:4]}",
        signer_pubkey=signer,
        subject_pubkey=subject,
        listing_event_id="0" * 64,
        pack="cars-pack@1",
        status=status,
        sale_closed_at=sale_closed_at,
        paired=paired,
        counterparty_status=cp_status,
    )


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------


def test_scoring_with_no_signals_returns_neutral() -> None:
    """Empty inputs collapse to the neutral 0.5 anchor per scoring.md."""
    report = aggregate_score(
        badges=[],
        attestations=[],
        admin_decisions=[],
        wot_graph={},
        user_pubkey=ALICE,
        counterparty_pubkey=BOB,
        admin_trust={},
        now=NOW_TS,
    )
    assert report.score == pytest.approx(0.5, abs=1e-9)
    assert report.red_flags == []
    assert report.green_flags == []
    # all layer scores zero
    for layer, val in report.layer_scores.items():
        assert val == 0.0, f"{layer} should be 0, got {val}"


def test_scoring_revoked_badge_red_flag() -> None:
    """A revoked badge from a trusted issuer is a hard red flag."""
    revoked_badge = BadgeRecord(
        issuer_pubkey=ISSUER1,
        badge_id="verified-private-seller",
        award_event_id="0" * 64,
        revoked=True,
        revoked_at=NOW_TS - 30 * 86400,
    )
    report = aggregate_score(
        badges=[revoked_badge],
        attestations=[],
        admin_decisions=[],
        wot_graph={},
        user_pubkey=ALICE,
        counterparty_pubkey=BOB,
        admin_trust={},
        trust_issuers={ISSUER1: 1.0},
        now=NOW_TS,
    )
    assert report.score < 0.5
    assert any("revoked" in f.lower() for f in report.red_flags)
    # Layer raw score should be the strong negative -0.5
    assert report.layer_scores["badge_score"] == pytest.approx(-0.5, abs=1e-9)


def test_scoring_completed_clean_boosts() -> None:
    """5 completed-clean paired attestations from direct contacts boost above 0.5.

    With the 0.05-cap-per-attestation defined in scoring.md, the
    attestation layer maxes out at +0.25 across 5 sales. The
    aggregate weight of the attestation layer is 0.4, so the
    contribution to `raw` is +0.10, which pushes the aggregate
    from 0.5 to 0.55. We assert > 0.5 (strict improvement) and
    > 0.54 (close to the analytical max).
    """
    user = ALICE
    contacts = {CAROL, DAVE, BOB, "9" * 64, "8" * 64}
    graph = {user: contacts}
    attestations = [
        _attestation(
            signer=signer,
            subject=BOB,
            paired=True,
            status="completed-clean",
            cp_status="confirmed",
            sale_id=f"sale-{i}",
            sale_closed_at=NOW_TS - 86400 * 7,  # very fresh
        )
        for i, signer in enumerate(contacts - {BOB})
    ]
    # Need 5 attestations from direct contacts (excluding BOB the subject).
    extra_signer = "7" * 64
    contacts.add(extra_signer)
    graph = {user: contacts}
    attestations.append(
        _attestation(
            signer=extra_signer,
            subject=BOB,
            paired=True,
            status="completed-clean",
            cp_status="confirmed",
            sale_id="sale-extra",
            sale_closed_at=NOW_TS - 86400 * 7,
        )
    )
    report = aggregate_score(
        badges=[],
        attestations=attestations,
        admin_decisions=[],
        wot_graph=graph,
        user_pubkey=user,
        counterparty_pubkey=BOB,
        admin_trust={},
        now=NOW_TS,
    )
    assert report.score > 0.5
    assert report.score > 0.54
    assert report.attestation_summary["completed_clean"] == 5


def test_wot_distance_computation() -> None:
    """alice -> bob -> carol => distance(alice, carol) == 2."""
    graph = {
        ALICE: {BOB},
        BOB:   {CAROL},
        CAROL: set(),
    }
    assert wot_distance(ALICE, BOB, graph) == 1
    assert wot_distance(ALICE, CAROL, graph) == 2
    assert wot_distance(ALICE, DAVE, graph) is None
    assert wot_distance(ALICE, ALICE, graph) == 0


def test_admin_decision_weight_respects_trust() -> None:
    """admin_trust=0 zeroes the decision; admin_trust=1 amplifies it."""
    decision = AdminDecisionRecord(
        dispute_id="11111111-1111-4111-8111-111111111111",
        admin_pubkey=ADMIN1,
        affected_pubkey=BOB,
        related_event_id="0" * 64,
        pack="cars-pack@1",
        decision="warning",
        severity="moderate",
        reason_hash="0" * 64,
        appeal_until=NOW_TS + 30 * 86400,
        has_open_appeal=False,
    )

    untrusted = aggregate_score(
        badges=[],
        attestations=[],
        admin_decisions=[decision],
        wot_graph={},
        user_pubkey=ALICE,
        counterparty_pubkey=BOB,
        admin_trust={},  # admin not trusted at all
        now=NOW_TS,
    )
    full_trust = aggregate_score(
        badges=[],
        attestations=[],
        admin_decisions=[decision],
        wot_graph={},
        user_pubkey=ALICE,
        counterparty_pubkey=BOB,
        admin_trust={ADMIN1: 1.0},
        now=NOW_TS,
    )
    half_trust = aggregate_score(
        badges=[],
        attestations=[],
        admin_decisions=[decision],
        wot_graph={},
        user_pubkey=ALICE,
        counterparty_pubkey=BOB,
        admin_trust={ADMIN1: 0.5},
        now=NOW_TS,
    )
    # untrusted admin == no signal
    assert untrusted.layer_scores["admin_score"] == pytest.approx(0.0, abs=1e-9)
    assert untrusted.score == pytest.approx(0.5, abs=1e-9)
    # full trust pulls the score down
    assert full_trust.score < untrusted.score
    # half trust pulls the score down half as much
    delta_full = untrusted.score - full_trust.score
    delta_half = untrusted.score - half_trust.score
    assert delta_half < delta_full
    assert delta_half == pytest.approx(delta_full / 2, abs=1e-9)


# ---------------------------------------------------------------------------
# Input-validation tests on submit_* tools (relay client mocked out)
# ---------------------------------------------------------------------------


VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"
VALID_PUBKEY = BOB
VALID_EVENT_ID = "0" * 64
# 64-hex secret key (test fixture only — never shared, never logged).
TEST_SK = "1" * 64


@pytest.fixture()
def fake_relay_publish():
    """Patch the relay_client + Event signing surface used by server.py.

    We avoid actual TLS handshakes / signing by stubbing out:
      - ReputationRelayClient context manager
      - pynostr.event.Event signing path

    The patched Event ends up with a deterministic id we can assert on.
    """
    from reputation_mcp import server as srv

    class _FakeClient:
        def __init__(self, relays):
            self.relays = relays
            self.published: list[object] = []

        def publish_event(self, ev):
            self.published.append(ev)

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    holder: dict[str, object] = {}

    def _factory(relays):
        c = _FakeClient(relays)
        holder["client"] = c
        return c

    # Patch the Event so we don't actually need secp256k1 signing.
    class _FakeEvent:
        def __init__(self, kind, pubkey, content, tags, created_at):
            self.kind = kind
            self.pubkey = pubkey
            self.content = content
            self.tags = tags
            self.created_at = created_at
            self.id = "deadbeef" * 8
            self.sig = "ab" * 32

        def sign(self, sk_hex):
            self.sig = "ab" * 32

    class _FakePrivateKey:
        def __init__(self, hexv):
            self._hex = hexv
            self.public_key = type(
                "_PK", (), {"hex": lambda self_: ALICE}
            )()

        @classmethod
        def from_hex(cls, h):
            return cls(h)

    with (
        patch.object(srv, "ReputationRelayClient", _factory),
        patch("pynostr.event.Event", _FakeEvent),
        patch("pynostr.key.PrivateKey", _FakePrivateKey),
    ):
        yield holder


def _unwrap(tool_obj):
    """FastMCP's `@mcp.tool()` returns the original function on this
    version, but older / newer wrappers expose the callable as `.fn`.
    Tolerate both."""
    return getattr(tool_obj, "fn", tool_obj)


def test_submit_peer_attestation_requires_signing_key(fake_relay_publish) -> None:
    from reputation_mcp.server import submit_peer_attestation

    fn = _unwrap(submit_peer_attestation)
    with pytest.raises(ValueError, match="signing_key_hex"):
        fn(
            sale_id=VALID_UUID,
            counterparty_pubkey=VALID_PUBKEY,
            listing_event_id=VALID_EVENT_ID,
            status="completed-clean",
            signing_key_hex=None,
        )


def test_submit_peer_attestation_rejects_unknown_status(fake_relay_publish) -> None:
    from reputation_mcp.server import submit_peer_attestation

    fn = _unwrap(submit_peer_attestation)
    with pytest.raises(ValueError, match="status"):
        fn(
            sale_id=VALID_UUID,
            counterparty_pubkey=VALID_PUBKEY,
            listing_event_id=VALID_EVENT_ID,
            status="totally-fine-trust-me",
            signing_key_hex=TEST_SK,
        )


def test_submit_peer_attestation_publishes(fake_relay_publish) -> None:
    from reputation_mcp.server import submit_peer_attestation

    fn = _unwrap(submit_peer_attestation)
    event_id = fn(
        sale_id=VALID_UUID,
        counterparty_pubkey=VALID_PUBKEY,
        listing_event_id=VALID_EVENT_ID,
        status="completed-clean",
        currency_band="15k-50k",
        pack="cars-pack@1",
        relays=["wss://test.example"],
        signing_key_hex=TEST_SK,
        note="clean sale",
    )
    assert event_id == "deadbeef" * 8
    fake_client = fake_relay_publish["client"]
    assert len(fake_client.published) == 1
    ev = fake_client.published[0]
    assert ev.kind == 30410
    assert ["d", VALID_UUID] in ev.tags
    assert ["status", "completed-clean"] in ev.tags
    assert ["pack", "cars-pack@1"] in ev.tags
    assert ev.content == "clean sale"


def test_submit_counter_attestation_rejects_self_sign(fake_relay_publish) -> None:
    from reputation_mcp.server import submit_counter_attestation

    fn = _unwrap(submit_counter_attestation)
    # PrivateKey fake returns ALICE; if we pass ALICE as seller_pubkey the
    # server should refuse (counter-att must be from the OTHER party).
    with pytest.raises(ValueError, match="OTHER party"):
        fn(
            sale_id=VALID_UUID,
            seller_attestation_event_id=VALID_EVENT_ID,
            seller_pubkey=ALICE,
            status="confirmed",
            signing_key_hex=TEST_SK,
        )


def test_submit_dispute_attestation_requires_reason(fake_relay_publish) -> None:
    from reputation_mcp.server import submit_dispute_attestation

    fn = _unwrap(submit_dispute_attestation)
    with pytest.raises(ValueError, match="reason_short"):
        fn(
            sale_id=VALID_UUID,
            counterparty_pubkey=VALID_PUBKEY,
            listing_event_id=VALID_EVENT_ID,
            reason_short="",
            signing_key_hex=TEST_SK,
        )


def test_submit_peer_attestation_rejects_exact_price_in_band(fake_relay_publish) -> None:
    from reputation_mcp.server import submit_peer_attestation

    fn = _unwrap(submit_peer_attestation)
    with pytest.raises(ValueError, match="band"):
        fn(
            sale_id=VALID_UUID,
            counterparty_pubkey=VALID_PUBKEY,
            listing_event_id=VALID_EVENT_ID,
            status="completed-clean",
            currency_band="32500",  # 4-digit run = exact price, refused
            signing_key_hex=TEST_SK,
        )


# ---------------------------------------------------------------------------
# get_reputation smoke test (relay queries mocked)
# ---------------------------------------------------------------------------


def test_get_reputation_returns_neutral_on_empty_relay() -> None:
    """If no events come back, score should be neutral 0.5."""
    from reputation_mcp import server as srv

    class _EmptyClient:
        def __init__(self, relays):
            self.relays = relays

        def query_events(self, filters, timeout_seconds=None):
            return []

        def publish_event(self, ev):
            pass

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    with patch.object(srv, "ReputationRelayClient", _EmptyClient):
        get_rep = _unwrap(srv.get_reputation)
        report = get_rep(
            pubkey=BOB,
            vertical_pack="cars-pack@1",
            relays=["wss://test.example"],
        )
    assert report["score_aggregate"] == pytest.approx(0.5, abs=1e-9)
    assert report["onchain_stake"] is None
    # When no user_pubkey is supplied, the score is computed against
    # the target itself as the WoT anchor — distance == 0.
    assert report["wot_distance"] == 0
    assert report["attestations"]["completed_clean"] == 0
