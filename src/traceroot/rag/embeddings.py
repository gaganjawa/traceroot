import os
from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI


@lru_cache(maxsize=1)
def _get_embedding_client() -> tuple[OpenAI, str]:
    """Resolve configuration and reuse a client only when embeddings are needed."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    return client, os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def embed_text(text: str) -> list[float]:
    """
    Embed a single text using the configured OpenAI embedding model.
    """
    if not text.strip():
        raise ValueError("Text to embed cannot be empty")

    client, model = _get_embedding_client()
    response = client.embeddings.create(
        model=model,
        input=text,
    )

    return response.data[0].embedding


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple texts in a single API request.
    """
    if not texts:
        return []

    if any(not text.strip() for text in texts):
        raise ValueError("Texts to embed cannot contain empty text")

    client, model = _get_embedding_client()
    response = client.embeddings.create(
        model=model,
        input=texts,
    )

    return [item.embedding for item in response.data]
