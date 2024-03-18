"""
Extract metadata from a file and summarize it into xml format.
NOTE: This file is not used in the project. You can use this as a reference to create your own meta extraction.
"""

# from langchain_core.output_parsers import StrOutputParser, XMLOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
import re

class ChatOpenRouter(ChatOpenAI):
    openai_api_base: str
    openai_api_key: str
    model_name: str

    def __init__(self,
                 model_name: str,
                 openai_api_key: Optional[str] = None,
                 openai_api_base: str = "https://openrouter.ai/api/v1",
                 **kwargs):
        openai_api_key = openai_api_key or os.getenv('OPENROUTER_API_KEY')
        super().__init__(openai_api_base=openai_api_base,
                         openai_api_key=openai_api_key,
                         model_name=model_name, **kwargs)


template = """\
===
Langgraph README.md:
{readme_content}
===
File Content:
{file_content}
===
Summarzie the above file "{file_name}" into xml with attributes of description and graph abstract

description: describe the file in a few words, concisely;
graph: use langgraph syntax to describe the high level structure of the graph mentioned in the file, only output python code of the graph.

Please enclose the output in xml format. Only output xml. Donot output any prefix or suffix.

Output Format:
<description>insert_description_here</description>
<graph>insert_graph_abstract_here</graph>\
"""
prompt = ChatPromptTemplate.from_template(template)
print(prompt)


def custom_parse(ai_message: AIMessage) -> str:
    """Parse the AI message."""
    content = ai_message.content

    # create a dictionary to store the parsed data
    data = {}

    # use regular expressions to extract elements and their content
    pattern = r"<(\w+)>(.*?)</\1>"
    matches = re.findall(pattern, content, re.DOTALL)

    for match in matches:
        tag, text = match
        data[tag] = text.strip()

    return data

llm = ChatOpenRouter(
    model_name="anthropic/claude-3-haiku",
    temperature=0.7,
)

llm_chain = (
    prompt
    | llm 
    | custom_parse
)