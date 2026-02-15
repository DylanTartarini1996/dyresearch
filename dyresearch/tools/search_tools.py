import os
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv("config.env")


def perform_google_search(query: str) -> str:
    """
    Searches Google for the given query and returns a summary with sources.
    Useful for finding current events, news, or factual information.
    """
    # Initialize a temporary client just for this tool execution
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Configure the Search Tool Natively
    search_tool = types.Tool(
        google_search=types.GoogleSearch()
    )
    
    try:
        # We make a direct call to Gemini to perform the search
        response = client.models.generate_content(
            model=os.getenv("GOOGLE_MODEL_NAME"),
            contents=query,
            config=types.GenerateContentConfig(
                tools=[search_tool],
                # We do NOT enable function calling here, just search
            )
        )
        
        # Return the grounded response text to the Agent
        return response
        
    except Exception as e:
        return f"Error performing search: {str(e)}"