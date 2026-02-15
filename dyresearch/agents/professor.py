import os

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent

from ..config import LLMConf
from ..factory.llm_providers import get_litellm_model
from ..tools.rag_tools import rag

load_dotenv("config.env")

conf = LLMConf(
    type="groq",
    model=os.getenv("GROQ_MODEL_NAME"),
    api_key=os.getenv("GROQ_API_KEY")
)

model = get_litellm_model(conf)

professor = Agent(
    model=model,
    name='professor_agent',
    description='Answers to specific questions on AI',
    instruction="You are a professor of Artificial Intelligence and Machine Learning. "
                 "Answer the user question using the `rag` tool to look in your library of sources ",
    tools=[rag],
    output_key="answer"
)