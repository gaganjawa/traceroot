import pytest

from traceroot.rag.embeddings import embed_text, embed_texts


def test_embed_text_rejects_empty_text():
    with pytest.raises(ValueError):
        embed_text("")


def test_embed_text_rejects_whitespace_only_text():
    with pytest.raises(ValueError):
        embed_text("   ")


def test_embed_texts_returns_empty_list_for_empty_input():
    assert embed_texts([]) == []


def test_embed_texts_rejects_empty_text():
    with pytest.raises(ValueError):
        embed_texts([
            "valid text",
            "",
        ])


def test_embed_texts_rejects_whitespace_only_text():
    with pytest.raises(ValueError):
        embed_texts([
            "checkout latency",
            "   ",
            "payment failure",
        ])