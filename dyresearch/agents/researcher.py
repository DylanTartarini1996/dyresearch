import os

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent

from ..config import LLMConf
from ..factory.llm_providers import get_litellm_model
from ..tools.search_tools import perform_google_search

load_dotenv("config.env")

conf = LLMConf(
    type="groq",
    model=os.getenv("GROQ_MODEL_NAME"),
    api_key=os.getenv("GROQ_API_KEY")
)

model = get_litellm_model(conf)

researcher = Agent(
    model=model,
    name='researcher_agent',
    description='A helpful assistant for user questions regarding the news on AI.',
    instruction='You are an AI assistant. Use Google Search to answer the user about his AI-related queries based on recent news. Avoid any other topic',
    tools=[perform_google_search],
)