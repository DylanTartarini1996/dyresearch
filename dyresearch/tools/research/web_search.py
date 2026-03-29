import httpx
import os

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.adk.tools.tool_context import ToolContext
from google.genai import types


load_dotenv("config.env")


async def perform_web_search(query: str, domains: list[str] = None, num_results: int = 5, tool_context: ToolContext = None) -> str:
    """
    Searches the Web for the given query and returns a summary with sources.  
    Useful for finding current events, news, or factual information.  
    Optionally restrict the search to specific domains (e.g., ['medium.com', 'arxiv.org']).
    """
    # TODO limit number of results
    search_query = query
    if domains:
        site_filters = " OR ".join([f"site:{domain}" for domain in domains])
        search_query = f"{query} ({site_filters})"

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
            contents=search_query,
            config=types.GenerateContentConfig(
                tools=[search_tool],
            )
        )

        return "\n".join(response.candidates)
        
    except Exception as e:
        return f"Error performing search: {str(e)}"


async def download_document(url: str, filename: str, tool_context: ToolContext = None) -> str:
    """
    Downloads a file (like a PDF) from a URL and saves it to a local 'downloads' folder.
    Returns the absolute path to the saved file.
    """
    # Ensure a local downloads directory exists
    download_dir = os.path.join(os.getcwd(), "research_downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    # Clean the filename
    safe_filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '.', '-', '_')]).rstrip()
    if not safe_filename.endswith('.pdf'):
        safe_filename += '.pdf' # Defaulting to PDF for this example
        
    file_path = os.path.join(download_dir, safe_filename)
    
    try:
        # Fetch the file asynchronously
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
                
        return f"✅ File successfully downloaded to: {file_path}"
    except Exception as e:
        return f"❌ Failed to download file from {url}. Error: {str(e)}"
    

async def scrape_website(url: str) -> str:
    """
    Scrapes a webpage and extracts the main text content, stripping away HTML, ads, and menus.
    Use this to read articles, blogs, and documentation pages.
    """
    try:
        # Using a standard browser user-agent to avoid being blocked by simple bot-protection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, follow_redirects=True, timeout=10.0)
            response.raise_for_status()
            
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'lxml') # 'html.parser' works too, but lxml is faster
        
        # Kill all script and style elements
        for script_or_style in soup(["script", "style", "header", "footer", "nav", "aside"]):
            script_or_style.extract()
            
        # Get the clean text
        text = soup.get_text(separator='\n')
        
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each, and drop blank lines
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if not clean_text:
            return f"❌ Successfully accessed {url}, but could not find readable text content."
            
        return clean_text

    except Exception as e:
        return f"❌ Failed to scrape website at {url}. Error: {str(e)}"
    
