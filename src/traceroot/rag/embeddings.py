import os

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables once when this module is imported
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")

BASE_URL = os.getenv(
    "OPENAI_BASE_URL",
    "https://api.openai.com/v1",
)

EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-small",
)

# Create one OpenAI client and reuse it
client = OpenAI(
    api_key=api_key,
    base_url=BASE_URL,
)


def embed_text(text: str) -> list[float]:
    """
    Embed a single text using the configured OpenAI embedding model.
    """
    if not text.strip():
        raise ValueError("Text to embed cannot be empty")

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
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

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    return [item.embedding for item in response.data]
