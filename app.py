import os
from enum import Enum

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

from token_count import num_messages, num_tokens_from_string
from utils import get_filtered_files, find_repos

load_dotenv()


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


def get_api_key(selected_model: str) -> str | None:
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


class StreamHandler:
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def process_token(self, token: str):
        self.text += token
        self.container.markdown(self.text)


def create_app():
    st.set_page_config(page_title="ChatWithRepo", page_icon="🤖")

    with st.sidebar:
        st.title("Settings for LLM")
        st.write(
            "Chat with LLM using the repository information and files. You can change model settings anytime during the chat."
        )

        selected_model = st.selectbox("Model", options=MODELS)
        temperature = st.slider(
            "Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.1
        )
        system_prompt = st.text_area(
            "System Prompt",
            value="You are a helpful assistant. You are provided with a repo information and files from the repo. Answer the user's questions based on the information and files provided.",
        )

        st.title("Settings for Repo")
        repos = find_repos()
        repo_options = [repo["repo_url"] for repo in repos]

        custom_repo_url = st.text_input("Custom Repository URL")
        if st.button("Add Custom Repository"):
            repo_options.append(custom_repo_url)
            repo_url = custom_repo_url
            os.system(f"python repo.py {repo_url}")
            st.rerun()

        repo_url = st.selectbox("Repository URL", options=repo_options, index=0)
        repo_url = repo_url if repo_url else "/"
        repo_name = repo_url.split("/")[-1]
        local_path = "./repos"
        repo_path = os.path.join(local_path, repo_name)
        if not os.path.exists(repo_path):
            if st.button("Download Repository"):
                os.system(f"python repo.py {repo_url}")
                st.rerun()  # rerun the script to get the updated repo_path
        else:
            st.write(f"Repository already downloaded to: {repo_path}")

            csv_path = os.path.join(repo_path, "repo_stats.csv")
            try:
                df = pd.read_csv(csv_path)
                file_options = df["file_path"].tolist()
                # get folder from file_path
                folder_options = list(
                    set([os.path.dirname(file_path) for file_path in file_options])
                )
                language_options = df["language"].unique().tolist()
                selected_folder = st.multiselect(
                    "Select Folder", options=folder_options
                )
                selected_files = st.multiselect(
                    "Select Files", options=file_options, default="README.md"
                )
                selected_languages = st.multiselect(
                    "Language", options=language_options
                )
            except FileNotFoundError:
                st.error(f"File not found: {csv_path}")
                selected_files = []
                selected_folder = []
                selected_languages = []
            limit = st.number_input("Limit", value=200000, step=10000)

            if st.button("Clear Chat"):
                st.session_state["messages"] = []
            if st.button("Count Tokens"):
                file_content_prefix = get_filtered_files(
                    repo_path,
                    selected_folders=selected_folder,
                    selected_files=selected_files,
                    selected_languages=selected_languages,
                    limit=limit,
                )
                st.write(f"Total Tokens: {num_tokens_from_string(file_content_prefix)}")

    if repo_name:
        st.title(f"Repo: {repo_name}")
    else:
        st.title(f"{selected_model}")

    if not os.path.exists(repo_path):
        st.info("Copy the repository URL and click the download button.")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "client" not in st.session_state:
        st.session_state["client"] = create_client_for_model(selected_model)

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    st.info(
        f"""
    Files : {selected_files}
    Folder: {selected_folder}
    Languages: {selected_languages}
    Limit: {limit}
    """
    )

    if prompt := st.chat_input():
        # Check if the selected model has changed
        if "selected_model" not in st.session_state:
            st.session_state.selected_model = None

        if st.session_state.selected_model != selected_model:
            st.session_state.client = create_client_for_model(selected_model)
            st.session_state.selected_model = selected_model

        if not os.path.exists(repo_path):
            st.error("Please download the repository first.")
            st.stop()
        file_content_prefix = get_filtered_files(
            repo_path,
            selected_folders=selected_folder,
            selected_files=selected_files,
            selected_languages=selected_languages,
            limit=limit,
        )

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            stream_handler = StreamHandler(st.empty())
            # only add file content to the system prompt
            messages = (
                [{"role": "system", "content": system_prompt}]
                + [{"role": "user", "content": file_content_prefix}]
                + st.session_state.messages
            )
            client = st.session_state["client"]

            # log the information
            logger.info(
                f"Information: {repo_path}, {selected_files}, {selected_folder}, {selected_languages}, {limit}"
            )
            st.sidebar.write(
                f"Sending file content: {selected_files} and filter folder: {selected_folder} to the assistant."
            )
            st.sidebar.write(f"total messages token: {num_messages(messages)}")
            logger.info(f"Using settings: {selected_model}, {temperature}")
            logger.info(
                f"Sending selected files {selected_files} and filter folder: {selected_folder} to the assistant."
            )
            logger.info(f"File token: {num_tokens_from_string(file_content_prefix)}")
            logger.info(f"Total Messages Token: {num_messages(messages)}")

            # send to llm
            completion = client.chat(
                messages, stream=True, temperature=temperature, model=selected_model
            )

            for chunk in completion:
                content = chunk.choices[0].delta.content
                stream_handler.process_token(content)

            st.session_state.messages.append(
                {"role": "assistant", "content": stream_handler.text}
            )


if __name__ == "__main__":
    create_app()
