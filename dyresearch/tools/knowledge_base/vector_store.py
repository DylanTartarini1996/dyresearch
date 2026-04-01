from typing import List, Optional

from google.adk.tools.tool_context import ToolContext
from sqlalchemy import select, delete

from ...entities.knowledge_chunk import KnowledgeChunk
from ...factory.database import db_config, get_db_context
from ...factory.embeddings import BaseEmbedder, embedder_conf, get_embeddings
from ...utils.logger import get_logger


logger = get_logger(__name__)


async def ingest_source(
    content_chunks: List[str], 
    subject: str="General",
    title: str=None, 
    source_type: str=None, 
    authors: str = None, 
    tool_context: ToolContext = None
    ) -> str:
    """
    Ingests multiple text chunks into the pgvector database using batch embedding.

    -------
    Params:
    -------
    - `content_chunks`: `List[str]``
        List of strings to be vectorized and stored.
    - `subject`: `str`
        Subject of the chunks. Will be use to index them in a common subject folder with other available chunks
    - `title`: `str`
        Title of the source (book/website).
    - `source_type`: `str` 
        Category (e.g., 'textbook', 'research_paper').
    - `author`: `str`
        Author name if known.
    """
    chunks_saved = 0

    if not content_chunks:
        return "Error: No content chunks provided for ingestion."
    
    embedder: BaseEmbedder = get_embeddings(embedder_conf)

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
                    authors=authors,
                    embedding=vector,
                    subject=subject.lower(),
                    embedding_model=embedder.model
                )
                
                session.add(new_chunk)
                chunks_saved += 1
                
            await session.commit()
            
        return f"Successfully ingested '{title}' - ({chunks_saved} chunks indexed) into the {subject} index."
    
    except Exception as e:
        return f"Ingestion failed: {str(e)}"
    

async def list_available_sources(tool_context: ToolContext = None) -> str:
    """
    Returns a formatted list of all unique sources (books, websites, papers) 
    currently indexed in the vector database, divided by subject. 
    """
    try:
        async with get_db_context(db_config) as session:
            # SQLAlchemy: SELECT DISTINCT source_title, source_type, author
            stmt = (
                select(
                    KnowledgeChunk.source_title, 
                    KnowledgeChunk.source_type, 
                    KnowledgeChunk.authors,
                    KnowledgeChunk.subject
                )
                .distinct()
                .order_by(KnowledgeChunk.subject)
            )
            
            result = await session.execute(stmt)
            rows = result.all()
            
            if not rows:
                return "The library is currently empty. No sources have been ingested yet."
            
            # Group the output by Subject
            inventory = {}
            for subject, title, source_type in rows:
                if subject not in inventory:
                    inventory[subject] = []
                doc_type = str(source_type).upper() if source_type else "DOC"
                inventory[subject].append(f"  - [{doc_type}] {title}")

            # Format for the LLM
            formatted_list = ["### 📚 Library Inventory by Subject:"]
            for subject, items in inventory.items():
                formatted_list.append(f"\n**🗂️ Index: {subject.capitalize()}**")
                formatted_list.extend(items)

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
    

async def delete_by_subject(subject: str) -> str:
    """
    Deletes ALL knowledge chunks associated with a specific subject index.
    Use this to clear an entire category (e.g., 'physics', 'temp_research') from the library.
    """
    if not subject:
        return "Error: Please provide a valid subject name to delete."
    
    target_subject = subject.lower()

    try:
        async with get_db_context(db_config) as session:
            stmt = delete(KnowledgeChunk).where(KnowledgeChunk.subject == target_subject)
            result = await session.execute(stmt)
            deleted_count = result.rowcount
            
            if deleted_count == 0:
                return f"No records found for subject '{subject}'. Nothing was deleted."
            
            # Finalize the transaction
            await session.commit()
            
            return (
                f"🗑️ Bulk Delete Successful!\n"
                f"Removed the entire '{subject}' index.\n"
                f"Total chunks purged: {deleted_count}."
            )
        
    except Exception as e:
        return f"Failed to perform bulk delete on subject '{subject}': {str(e)}"

    
async def search_knowledge_base(
    query: str, 
    subject_filter: Optional[str] = "",
    limit: int = 5, 
    tool_context: ToolContext = None
    ) -> str:
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
            stmt = select(KnowledgeChunk)
            if subject_filter != "":
                stmt = stmt.where(KnowledgeChunk.subject == subject_filter.lower())
            stmt = stmt.order_by(KnowledgeChunk.embedding.cosine_distance(query_vector)).limit(limit)
            
            result = await session.execute(stmt)
            chunks = result.scalars().all()

            if not chunks:
                folder_info = f" in the '{subject_filter}' index" if subject_filter != "" else ""
                return f"I searched the library but found no relevant documents{folder_info}."

            # Format the response with clear citations 
            formatted_results = [f"### Relevant Passages (Index: {subject_filter or 'All'}):"]
            for i, chunk in enumerate(chunks, 1):
                citation = f"Source: {chunk.source_title} | Authors: {chunk.authors}"
                formatted_results.append(f"{i}. > {chunk.content}\n   *({citation})*")

            return "\n\n".join(formatted_results)

    except Exception as e:
        return f"An error occurred during the search: {str(e)}"
