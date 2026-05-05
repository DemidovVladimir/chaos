"""Tests for ``chaos_buyer.inbox``."""

from __future__ import annotations

import pytest


def test_inbox_jsonl_append_only() -> None:
    """Appending entries keeps prior entries unchanged byte-for-byte."""
    pytest.skip("not yet implemented")
def test_inbox_no_decrypted_content_after_7_days() -> None:
    """The retention sweeper drops the cleartext payload of older entries."""
    pytest.skip("not yet implemented")
def test_inbox_rejects_unsafe_conversation_id() -> None:
    """A conversation_id containing '/' or '..' raises ValueError."""
    pytest.skip("not yet implemented")
def test_inbox_read_chronological_order() -> None:
    """``read()`` returns entries in the order they were written."""
    pytest.skip("not yet implemented")