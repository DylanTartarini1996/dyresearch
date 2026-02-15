import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from ..config import LLMConf
from ..factory.llm_providers import get_litellm_model
from ..tools.notes import NoteTakingToolset

note_toolset = NoteTakingToolset()

load_dotenv("config.env")

conf = LLMConf(
    type="groq",
    model=os.getenv("GROQ_MODEL_NAME"),
    api_key=os.getenv("GROQ_API_KEY")
)

model = get_litellm_model(conf)

note_taker = Agent(
    model=model,
    name='note_taking_agent',
    description='Answers to specific questions on AI',
    instruction="You are the Lead NoteTaker. Your mission is to create 'Evergreen' notes that feel deeply integrated into the user's Obsidian Vault.\n\n"
        
        "### COMPOSITION RULES\n"
        "1. YAML Frontmatter: Always include tags, date, and a 'status' field (e.g., #seed, #branch, #evergreen).\n"
        "2. Semantic Linking: Weave [[Backlinks]] into sentences naturally.\n"
        "3. Visual Cues: Use Mermaid.js for processes and Obsidian callouts (> [!ABSTRACT]) for summaries.\n"
        "4. Atomic Notes: Use the 'create_note' tool to save your work. If content is long, split it into multiple files.",
    tools=[note_toolset]
)