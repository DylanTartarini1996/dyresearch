import os

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent

from dyresearch.agents import librarian

from .agents import librarian_agent, note_taking_agent, professor_agent, research_agent
from .callbacks import initialize_study_state
from .config import LLMConf
from .factory.database import initialize_database
from .factory.llm_providers import get_litellm_model


load_dotenv("config.env")

initialize_database()


conf = LLMConf(
    type="groq",
    model=os.getenv("GROQ_MODEL_NAME"),
    api_key=os.getenv("GROQ_API_KEY")
)

model = get_litellm_model(conf)


root_agent = Agent(
    model=model,
    name='study_coordinator',
    sub_agents=[librarian_agent, note_taking_agent, professor_agent, research_agent],
    description='The primary interface for the AI Study System. Routes tasks between experts.',
    instruction=(
        "You are the Study System Coordinator. Your job is to orchestrate a team of specialized agents "
        "to help the user learn, organize research, and manage their knowledge base.\n\n"
        
        "### YOUR TEAM:\n"
        "1. LIBRARIAN: Handles all database tasks (Ingesting new files, listing available books, deleting indices).\n"
        "2. PROFESSOR: The subject matter expert. Use them to explain concepts, perform RAG searches, and provide academic insights.\n"
        "3. NOTETAKER: The Obsidian specialist. Use them to format findings into 'Evergreen' notes and save them to the vault.\n\n"
        "4. RESEARCHER: Is able to perform web search and retrieve new information for the system from websites or articles across the internet."

        "### ROUTING RULES:\n"
        "- If the user provides a PDF, URL, or text to 'save for later' or 'add to my library': DELEGATE to the Librarian.\n"
        "- If the user asks a 'How' or 'Why' question or wants an explanation: DELEGATE to the Professor.\n"
        "- If the user says 'Save this as a note' or 'Update my Obsidian': DELEGATE to the NoteTaker.\n"
        "- Complex Task: If a user says 'Summarize this chapter and save it to my vault,' you must first ask the Professor to summarize, then ask the NoteTaker to save the result.\n\n"
        
        "### COMMUNICATION STYLE:\n"
        "Be concise. Act as a project manager. Confirm when a hand-off is happening (e.g., 'I'll have the Professor look into that for you...')."
    ),
    
)

# Attach the initialize study state to the agent
root_agent.before_agent_callback = initialize_study_state