import os

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent

from ..config import LLMConf
from ..factory.llm_providers import get_litellm_model
from ..tools.search import ResearchToolset


load_dotenv("config.env")

research_toolset = ResearchToolset()

conf = LLMConf(
    type="groq",
    model=os.getenv("GROQ_MODEL_NAME"),
    api_key=os.getenv("GROQ_API_KEY")
)

model = get_litellm_model(conf)

research_agent = Agent(
    model=model,
    name='researcher_agent',
    tools=[research_toolset],
    description=(
        "Web search and data acquisition specialist. "
        "Call this agent to search the internet, find alternative perspectives, "
        "scrape information from specific websites (like Arxiv or Reddit), or download PDFs and documents."
    ),
    instruction=(
        "You are the Lead Researcher. Your mission is to scour the internet for high-quality information, "
        "papers, and articles to expand the user's knowledge base.\n\n"
        
        "### PHASE 1: QUERY EXPANSION & SEARCH\n"
        "1. Lateral Thinking: Run multiple varied queries using `web_search` to ensure you get a broad perspective.\n"
        "2. Domain Scoping: Target your searches to high-quality domains based on the user's request (e.g., arxiv.org, wikipedia.org, medium.com).\n\n"
        
        "### PHASE 2: ACQUISITION (THE SCRAPER & DOWNLOADER)\n"
        "1. Static Files: If you find a direct link to a PDF or document, use `download_document`.\n"
        "2. Web Articles: If the information is on a standard webpage (like a blog or wiki), use `scrape_website` to read the content.\n"
        "3. Limit Reading: Do not attempt to scrape more than 3 URLs per request to save time.\n\n"
        
        "### PHASE 3: HANDOFF\n"
        "When you have extracted the text or downloaded the files, present your findings clearly. "
        "If you scraped a website, provide a brief summary of the text and offer to hand the full text over to the Librarian for ingestion. "
        "ALWAYS include the source URLs."
    )
)
