import streamlit as st
from os import getenv
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional
import pandas as pd
import logging
from utils import get_filtered_files
from token_count import num_messages, num_tokens_from_string

load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ChatClient:
    def __init__(self, base_url, api_key):
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def chat(self, messages, model="anthropic/claude-3-opus", temperature=0.7, stream=True):
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream,
            temperature=temperature
        )
        return completion


class StreamHandler:
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def process_token(self, token: str):
        self.text += token
        self.container.markdown(self.text)


st.title("Claude 3 opus Chat")
st.write("200k long context, strongest model")


# sidebar
with st.sidebar:
    base_url = st.text_input("Base URL", value="https://openrouter.ai/api/v1")
    api_key = st.text_input("API Key", value=getenv(
        "OPENROUTER_API_KEY"), type="password")
    model = st.selectbox(
        "Model", options=["anthropic/claude-3-haiku", "anthropic/claude-3-opus"])
    temperature = st.slider("Temperature", min_value=0.0,
                            max_value=1.0, value=0.7, step=0.1)
    system_prompt = st.text_area(
        "System Prompt", value="You are a helpful assistant.")

    csv_path = st.text_input(
        "CSV Path", value="repos/langgraph/repo_stats.csv")
    filter_folder = st.text_input("Filter Folder", value="examples/")

    try:
        df = pd.read_csv(csv_path)
        file_options = df["file_path"].tolist()
        selected_files = st.multiselect(
            "Select Files", options=file_options, default="README.md")
    except FileNotFoundError:
        st.error(f"File not found: {csv_path}")
        selected_files = []
    # when change the csv path, click change csv
    if st.button("Change CSV"):
        # update selected files
        try:
            df = pd.read_csv(csv_path)
            file_options = df["file_path"].tolist()
            selected_files = st.multiselect(
                "Select Files", options=file_options)
        except FileNotFoundError:
            st.error(f"File not found: {csv_path}")
            selected_files = []

    language = st.selectbox("Language", options=["Jupyter Notebook"])
    limit = st.number_input("Limit", value=160000, step=10000)
    if st.button("Clear Chat"):
        st.session_state["messages"] = []

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "client" not in st.session_state:
    st.session_state["client"] = ChatClient(base_url, api_key)

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    file_content_prefix = ""
    if selected_files or filter_folder:
        repo_path = csv_path.rsplit("/", 1)[0]
        file_paths_list = [filter_folder.strip(), *selected_files]
        logger.info(f"File Information: {repo_path}, {file_paths_list}, {language}, {limit}")
        file_content_prefix = get_filtered_files(
            repo_path, file_paths_list, language=language, limit=limit)
        file_content_prefix = f"[File Content]\n{file_content_prefix}\n\nQuestion:\n"

    st.session_state.messages.append({"role": "user", "content": prompt})
    # TODO: display attached files in one line
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        stream_handler = StreamHandler(st.empty())

        messages = [{"role": "system", "content": system_prompt}
                    ] + st.session_state.messages
        messages[-1]["content"] = file_content_prefix + messages[-1]["content"]
        client = st.session_state["client"]
        logger.info(f"Using settings: {model}, {temperature}")
        logger.info(
            f"Sending selected files {selected_files} and filter folder: {filter_folder} to the assistant.")
        logger.info(f"Total Messages Token: {num_messages(messages)}")
        logger.info(f"File token: {num_tokens_from_string(file_content_prefix)}")
        completion = client.chat(
            messages, stream=True, temperature=temperature, model=model)

        for chunk in completion:
            content = chunk.choices[0].delta.content
            stream_handler.process_token(content)

        st.session_state.messages.append(
            {"role": "assistant", "content": stream_handler.text})
