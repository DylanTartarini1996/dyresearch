from google.adk.agents.llm_agent import Agent
from google.adk.tools import google_search

root_agent = Agent(
    model='gemini-2.5-flash',
    name='ai_news_agent',
    description='A helpful assistant for user questions regarding the news on AI.',
    instruction='You are an AI News assistant. Use Google Search to answer the user about his AI-related queries based on recent news. Avoid any other topic',
    tools=[google_search]
)