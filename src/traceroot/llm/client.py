import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv(
    "OPENAI_BASE_URL",
    "https://api.openai.com/v1",
)
LLM_MODEL = os.getenv(
    "OPENAI_LLM_MODEL",
    "gpt-5.4-mini",
)

if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")

llm_client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)
