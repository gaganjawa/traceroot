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
        embed_texts(
            [
                "valid text",
                "",
            ]
        )


def test_embed_texts_rejects_whitespace_only_text():
    with pytest.raises(ValueError):
        embed_texts(
            [
                "checkout latency",
                "   ",
                "payment failure",
            ]
        )


@pytest.fixture(autouse=True)
def isolated_embeddings(monkeypatch):
    from traceroot.rag import embeddings

    embeddings._get_embedding_client.cache_clear()
    monkeypatch.setattr(embeddings, "load_dotenv", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)
    yield
    embeddings._get_embedding_client.cache_clear()


def test_imports_without_credentials():
    import subprocess
    import sys

    code = """
import os
from unittest.mock import patch
os.environ.pop('OPENAI_API_KEY', None)
with patch('dotenv.load_dotenv'), patch('openai.OpenAI') as client:
    import traceroot.rag.embeddings
    import traceroot.rag.index
    import traceroot.rag.retriever
    import traceroot.evaluation.comparison
    client.assert_not_called()
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "function, value",
    [
        (embed_text, ""),
        (embed_text, "  "),
        (embed_texts, ["ok", " "]),
        (embed_texts, []),
    ],
)
def test_invalid_or_empty_input_does_not_initialize_client(function, value):
    from unittest.mock import patch

    with patch("traceroot.rag.embeddings._get_embedding_client") as initialize:
        if value == []:
            assert function(value) == []
        else:
            with pytest.raises(ValueError):
                function(value)
    initialize.assert_not_called()


def test_valid_input_requires_credentials_at_call_time():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        embed_text("valid input")


@pytest.mark.parametrize("custom", [False, True])
def test_embedding_requests_preserve_configuration_and_reuse_client(
    monkeypatch, custom
):
    from types import SimpleNamespace
    from unittest.mock import patch

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    if custom:
        monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
        monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "custom-model")
    with patch("traceroot.rag.embeddings.OpenAI") as constructor:
        create = constructor.return_value.embeddings.create
        create.return_value = SimpleNamespace(data=[SimpleNamespace(embedding=[1.0])])
        assert embed_text("single") == [1.0]
        create.assert_called_once_with(
            model="custom-model" if custom else "text-embedding-3-small", input="single"
        )
        create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[2.0]), SimpleNamespace(embedding=[3.0])]
        )
        assert embed_texts(["first", "second"]) == [[2.0], [3.0]]
        create.assert_called_with(
            model="custom-model" if custom else "text-embedding-3-small",
            input=["first", "second"],
        )
        constructor.assert_called_once_with(
            api_key="test-key",
            base_url="https://example.test/v1"
            if custom
            else "https://api.openai.com/v1",
        )
