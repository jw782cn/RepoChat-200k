import os
from enum import Enum
from loguru import logger
from openai import OpenAI

class ProviderType(str, Enum):
    OPENAI = "OPENAI"
    OPENROUTER = "OPENROUTER"


BASE_URL_MAP = {
    ProviderType.OPENAI: "https://api.openai.com/v1",
    ProviderType.OPENROUTER: "https://openrouter.ai/api/v1",
}
MODEL_MAP = {
    ProviderType.OPENAI: [
        "gpt-4-1106-preview",
        "gpt-3.5-turbo-16k",
    ],
    ProviderType.OPENROUTER: [
        "anthropic/claude-3-haiku",
        "anthropic/claude-3-haiku:beta",
        "anthropic/claude-3-opus",
        "anthropic/claude-3-sonnet",
        "anthropic/claude-3-sonnet:beta",
        "anthropic/claude-3-opus:beta",
    ],
}
MODELS = [*MODEL_MAP[ProviderType.OPENROUTER], *MODEL_MAP[ProviderType.OPENAI]]


def get_base_url(selected_model: str) -> str:
    """Get the base url for the selected model.
    Args:
        selected_model(str): selected model

    Returns:
        str: base url for the selected model
    """
    if selected_model in MODEL_MAP[ProviderType.OPENAI]:
        return BASE_URL_MAP[ProviderType.OPENAI]
    elif selected_model in MODEL_MAP[ProviderType.OPENROUTER]:
        return BASE_URL_MAP[ProviderType.OPENROUTER]
    else:
        raise ValueError(f"Model {selected_model} not found.")


def get_api_key(selected_model: str) -> str:
    """Get the api key for the selected model.
    Args:
        selected_model(str): selected model

    Returns:
        str: api key for the selected model
    """
    if selected_model in MODEL_MAP[ProviderType.OPENAI]:
        return os.getenv("OPENAI_API_KEY")
    elif selected_model in MODEL_MAP[ProviderType.OPENROUTER]:
        return os.getenv("OPENROUTER_API_KEY")
    else:
        raise ValueError(f"Model {selected_model} not found.")


class ChatClient:
    def __init__(self, base_url: str, api_key: str):
        logger.info(
            f"Initializing ChatClient, base_url: {base_url} and api_key: {api_key[:5]}..."
        )
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def chat(
        self, messages, model="anthropic/claude-3-opus", temperature=0.7, stream=True
    ):
        return self.client.chat.completions.create(
            model=model, messages=messages, stream=stream, temperature=temperature
        )


def create_client_for_model(selected_model: str):
    """Create a client for the selected model.
    Args:
        selected_model(str): selected model

    Returns:
        ChatClient: ChatClient for the selected model
    """
    base_url = get_base_url(selected_model)
    api_key = get_api_key(selected_model)

    if api_key is None:
        raise ValueError(f"API Key not found for model: {selected_model}")

    return ChatClient(base_url, api_key)