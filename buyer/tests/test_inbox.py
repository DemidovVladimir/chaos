"""Tests for ``chaos_buyer.inbox``."""
from __future__ import annotations


def test_inbox_jsonl_append_only() -> None:
    """Appending entries keeps prior entries unchanged byte-for-byte."""
    assert False, "TODO: implement"


def test_inbox_no_decrypted_content_after_7_days() -> None:
    """The retention sweeper drops the cleartext payload of older entries."""
    assert False, "TODO: implement"


def test_inbox_rejects_unsafe_conversation_id() -> None:
    """A conversation_id containing '/' or '..' raises ValueError."""
    assert False, "TODO: implement"


def test_inbox_read_chronological_order() -> None:
    """``read()`` returns entries in the order they were written."""
    assert False, "TODO: implement"
