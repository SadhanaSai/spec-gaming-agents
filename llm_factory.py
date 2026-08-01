import os

import requests
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

load_dotenv()


def _ollama_available(base_url: str) -> bool:
    """Return True if Ollama responds at base_url, False on any failure."""
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def get_llm():
    """
    Return a working chat model: Ollama if reachable, else Groq.

    Raises RuntimeError if Ollama is unreachable and GROQ_API_KEY is unset.
    A GROQ_API_KEY that is set but invalid is not caught here — ChatGroq
    does not validate credentials until the model is actually invoked, so
    that failure surfaces from the caller's first real LLM call instead.
    """
    ollama_base_url = os.getenv("OLLAMA_BASE_URL")
    ollama_model = os.getenv("OLLAMA_MODEL")
    groq_api_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL")

    if _ollama_available(ollama_base_url):
        return ChatOllama(model=ollama_model, base_url=ollama_base_url)

    if groq_api_key:
        return ChatGroq(model=groq_model, api_key=groq_api_key)

    raise RuntimeError(
        f"No LLM available: Ollama unreachable at {ollama_base_url}, "
        f"and GROQ_API_KEY is not set."
    )


if __name__ == "__main__":
    llm = get_llm()
    model_id = getattr(llm, "model", None) or getattr(llm, "model_name", None)
    print(f"Selected provider: {type(llm).__name__} (model={model_id})")
