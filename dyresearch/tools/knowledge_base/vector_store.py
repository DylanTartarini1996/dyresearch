from google.adk.tools.tool_context import ToolContext
from sqlalchemy import select, delete

from ...entities.knowledge_chunk import KnowledgeChunk
from ...factory.database import db_config, get_db_context
from ...factory.embeddings import embedder_conf, get_embeddings
from ...utils.logger import get_logger


logger = get_logger(__name__)


async def ingest_source(
    content_chunks: list[str], 
    title: str=None, 
    source_type: str=None, 
    author: str = None, 
    tool_context: ToolContext = None
    ) -> str:
    """
    Ingests multiple text chunks into the pgvector database using batch embedding.

    -------
    Params:
    -------
    - `content_chunks`: List of strings to be vectorized and stored.
    - `title`: Title of the source (book/website).
    - `source_type`: Category (e.g., 'textbook', 'research_paper').
    - `author`: Author name if known.
    """
    chunks_saved = 0

    if not content_chunks:
        return "Error: No content chunks provided for ingestion."
    
    embedder = get_embeddings(embedder_conf)

    if not embedder:
        return "Error: Embedder not configured correctly."
    
    try:
        all_vectors = await embedder.embed_documents(content_chunks)
        
        async with get_db_context(db_config) as session:
            for chunk_text, vector in zip(content_chunks, all_vectors):
                
                new_chunk = KnowledgeChunk(
                    text=chunk_text,
                    source_title=title,
                    source_type=source_type,
                    author=author,
                    embedding=vector
                )
                
                session.add(new_chunk)
                chunks_saved += 1
                
            await session.commit()
            
        return f"Successfully ingested '{title}' ({chunks_saved} chunks indexed)."
    
    except Exception as e:
        return f"Ingestion failed: {str(e)}"
    

async def list_available_sources(tool_context: ToolContext = None) -> str:
    """
    Returns a formatted list of all unique sources (books, websites, papers) 
    currently indexed in the vector database.
    """
    try:
        async with get_db_context(db_config) as session:
            # SQLAlchemy: SELECT DISTINCT source_title, source_type, author
            stmt = (
                select(
                    KnowledgeChunk.source_title, 
                    KnowledgeChunk.source_type, 
                    KnowledgeChunk.authors
                ).distinct()
            )
            
            result = await session.execute(stmt)
            rows = result.all()
            
            if not rows:
                return "The library is currently empty. No sources have been ingested yet."

            formatted_list = ["### 📚 Current Library Inventory:"]
            for title, source_type, author in rows:
                # E.g., "[TEXTBOOK] Advanced Physics by Smith"
                doc_type = str(source_type).upper() if source_type else "DOCUMENT"
                formatted_list.append(f"- **[{doc_type}]** {title} (Author: {author})")

            return "\n".join(formatted_list)

    except Exception as e:
        return f"Database error while retrieving sources: {str(e)}"
    

async def delete_source(title: str, tool_context: ToolContext = None) -> str:
    """
    Deletes all vectorized chunks associated with a specific source title from the database.
    Use this when the user asks to remove a book, website, or document from the library.
    """
    try:
        async with get_db_context(db_config) as session:
            stmt = delete(KnowledgeChunk).where(KnowledgeChunk.source_title == title)
            
            result = await session.execute(stmt)
            deleted_count = result.rowcount
            
            if deleted_count == 0:
                return f"Could not find any source named '{title}' in the library to delete."

            await session.commit()
            
            return f"✅ Successfully removed '{title}' from the library. ({deleted_count} chunks deleted)."

    except Exception as e:
        return f"Failed to delete source '{title}': {str(e)}"

    

async def search_knowledge_base(query: str, limit: int = 5, tool_context: ToolContext = None) -> str:
    """
    Search the vector store knowledge base for information related to a specific query.
    Returns the most relevant text chunks along with their source metadata.
    """
    embedder = get_embeddings(embedder_conf)
    if not embedder:
        return "Error: Embedder not configured."

    try:
        query_vector = await embedder.embed_query(query)

        async with get_db_context(db_config) as session:
            stmt = (
                select(KnowledgeChunk)
                .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
                .limit(limit)
            )
            
            result = await session.execute(stmt)
            chunks = result.scalars().all()

            if not chunks:
                return "I searched the library but found no relevant documents."

            # Format the response with clear citations 
            formatted_results = ["### Relevant Knowledge Chunks:"]
            for i, chunk in enumerate(chunks, 1):
                citation = f"Source: {chunk.source_title} | Author: {chunk.author}"
                formatted_results.append(
                    f"{i}. > {chunk.text}\n   *({citation})*"
                )

            return "\n\n".join(formatted_results)

    except Exception as e:
        return f"An error occurred during the search: {str(e)}"
    

    # TODO add functions to create an index (subject), list the indexes and delete files by index