import os

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent

from .agents.professor import professor 
from .agents.researcher import researcher
from .config import LLMConf
from .factory.llm_providers import get_litellm_model


load_dotenv("config.env")

conf = LLMConf(
    type="groq",
    model=os.getenv("GROQ_MODEL_NAME"),
    api_key=os.getenv("GROQ_API_KEY")
)

model = get_litellm_model(conf)

root_agent = Agent(
    model=model,
    name='coordinator',
    description='AI Coordinator that can decide how to answer to the user queries',
    instruction="You are a helpful assistant. " 
                "Decide whether the user's queries should be adressed by the Researcher Agent (that looks into the web) "
                "or the Professor Agent ",
    sub_agents=[researcher, professor],
)