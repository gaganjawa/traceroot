import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LLM_MODEL_GPT_5_4_MINI = os.getenv(
    "OPENAI_LLM_MODEL",
    "gpt-5.4-mini",
)


# USD per 1M tokens, from the OpenAI GPT-5.4 Mini model pricing documentation.
# Aggregate input usage is charged at the standard input rate.
LLM_PRICING = {
    "gpt-5.4-mini": {
        "input_cost_per_million": 0.75,
        "output_cost_per_million": 4.50,
    },
}


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
