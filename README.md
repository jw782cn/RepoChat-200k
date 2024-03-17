# Chat-With-Repo

Chat-With-Repo is a Streamlit-based application that allows users to interact with a large language model (LLM) to answer questions or generate code based on the contents of a GitHub repository.

## Features

1. **Repository Download**: Users can provide a GitHub repository URL, and the application will automatically download and analyze the repository.
2. **File and Folder Selection**: Users can select specific files or folders from the repository to include in the LLM's input.
3. **Language Filtering**: Users can filter the files by programming language to focus the LLM's understanding on specific parts of the codebase.
4. **Token Limit**: Users can set a token limit to control the amount of information sent to the LLM, which can be useful for performance or cost considerations.
5. **Chat Interface**: Users can interact with the LLM through a chat-style interface, allowing them to ask questions or request code generation based on the repository contents.
6. **Streaming Output**: The LLM's responses are displayed in a streaming fashion, providing a more engaging and real-time user experience.

## Get Started

1. **Environment Settings**: Run `pip install -r requirements.txt` to set up environment.

2. **Create a .env file**: Create a `.env` file in the root directory of the project and add your OpenAI API key:
```bash
OPENROUTER_API_KEY=your_openai_api_key_here
```
3. **Run the application**: Run the `app.py` script using Streamlit:
```bash
streamlit run app.py
```
4. **Use the application**: Follow the instructions in the application to download a GitHub repository, select files and folders, and chat with the LLM.

## Configuration

The application's behavior can be customized through the following configuration options:

- **Model**: The specific LLM model to use (e.g., "anthropic/claude-3-haiku", "anthropic/claude-3-opus").
- **Temperature**: The temperature parameter that controls the "creativity" of the LLM's responses.
- **System Prompt**: The initial prompt given to the LLM to set the desired behavior.

These settings can be adjusted in the sidebar of the Streamlit application.

## Contributing

If you'd like to contribute to the Chat-With-Repo project, please feel free to submit issues or pull requests on the [GitHub repository](https://github.com/jw782cn/Chat-With-Repo).

## License

This project is licensed under the [MIT License](LICENSE).