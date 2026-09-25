import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LLM_MODEL_GPT_5_4_MINI = os.getenv(
    "OPENAI_LLM_MODEL",
    "gpt-5.4-mini",
)


def get_llm_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    base_url = os.getenv(
        "OPENAI_BASE_URL",
        "https://api.openai.com/v1",
    )

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
