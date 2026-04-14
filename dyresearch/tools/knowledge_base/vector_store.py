import json
from typing import Dict, List, Optional

from google.adk.tools.tool_context import ToolContext
from sqlalchemy import select, delete, func

from .ingestion import ingest_and_chunk_file
from ...entities.knowledge_chunk import KnowledgeChunk
from ...factory.database import db_config, get_db_context
from ...factory.embeddings import BaseEmbedder, embedder_conf, get_embeddings
from ...utils.logger import get_logger


logger = get_logger(__name__)


async def ingest_source_chunks(
    content_chunks: List[str], 
    subject: str="General",
    title: str=None, 
    source_type: str=None, 
    authors: str = None, 
    metadata_json: str = "{}",
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
    - `authors`: `str`
        Author(s) name(s) if known.
    - `metadata_json`: `str`
        Optional string representation of a dictionary of metadata associated with the source
    """
    chunks_saved = 0

    try:
        metadatas = json.loads(metadata_json)
    except json.JSONDecodeError:
        metadatas = {}

    if not content_chunks:
        error_no_chunks = "❌ Error: No content chunks provided for ingestion."
        logger.error(error_no_chunks)
        return error_no_chunks
    
    embedder: BaseEmbedder = get_embeddings(embedder_conf)

    if not embedder:
        error_no_embedder = "❌ Error: No content Embeddings model available."
        logger.error(error_no_embedder)
        return error_no_embedder
    
    total_chunks = len(content_chunks)
    batch_size = 15  # Manageable size for both embeddings and DB commits
    chunks_saved = 0

    try:
        logger.info(f"🚀 Starting ingestion for '{title}' ({total_chunks} chunks)")

        # Open the session once for the entire process
        async with get_db_context(db_config) as session:
            
            for i in range(0, total_chunks, batch_size):
                batch_text = content_chunks[i : i + batch_size]
                
                # 1. Batch Embedding
                logger.info(f"📡 Embedding batch {i//batch_size + 1}...")
                batch_vectors = await embedder.embed_documents(batch_text)
                
                # 2. Prepare Objects for this batch
                for j, (text, vector) in enumerate(zip(batch_text, batch_vectors)):
                    current_idx = i + j + 1
                    new_chunk = KnowledgeChunk(
                        text=text,
                        source_title=title,
                        chunk_id=current_idx, 
                        source_type=source_type,
                        authors=authors,
                        embedding=vector,
                        subject=subject.lower(),
                        embedding_model=embedder.model,
                        metadatas=metadatas
                    )
                    session.add(new_chunk)
                
                # 3. Intermediate Commit (Flush to DB)
                logger.info(f"💾 Committing batch {i//batch_size + 1} to Postgres...")
                await session.commit() 
                chunks_saved += len(batch_text)

        success_msg = f"✅ Ingestion Complete: '{title}' - {chunks_saved}/{total_chunks} chunks indexed."
        logger.info(success_msg)    
        return success_msg
    
    except Exception as e:
        logger.error(f"❌ Ingestion failed at chunk {chunks_saved}: {e}")
        return f"Ingestion failed: {str(e)}"
    

async def ingest_source_file(
    file_path: str, 
    title: str, 
    subject: str="General",
    source_type: str=None, 
    authors: str = None, 
    metadata_json: str = "{}",
    tool_context: ToolContext = None
    ): 
    """ 
    Ingest a source file from a given filepath available in the study system into the vector store. 
    
    -------
    Params:
    -------
    `file_path`: `str`
        Path of the source file to be ingested
    `source_name`: `str`:
        Title of the file
    - `subject`: `str`
        Subject of the file. Will be used to index its chunks into common subject folder with other available chunks
    - `title`: `str`
        Title of the source (book/website).
    - `source_type`: `str` 
        Category (e.g., 'textbook', 'research_paper').
    - `authors`: `str`
        Author(s) name(s) if known.
    - `metadata_json`: `str`
        Optional string representation of a dictionary of metadata associated with the source file
    """
    logger.debug(f"Ingesting from filepath {file_path}..")

    try:
        metadatas = json.loads(metadata_json)
    except json.JSONDecodeError:
        metadatas = {}

    try:
        chunks = await ingest_and_chunk_file(file_path=file_path, source_name=title)

        file_metadata = str({
            "filename": title,
            **metadatas
        })
        
        ingestion_msg = await ingest_source_chunks(
            content_chunks=chunks, 
            subject=subject,
            title=title,
            source_type=source_type,
            authors=authors,
            metadata_json=file_metadata
        )

        return ingestion_msg

    except Exception as e:
        return f"Ingestion failed: {str(e)}"
    

async def get_documents_summary(
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    include_note_taking_agent: bool = False,
    include_notes: bool = False
    ) -> Dict:
    """ 
    Returns a summary of all documents available in the Knowledge Base, 
    organized by `source_title, `authors`, `subject` and `source_type`. 

    Supports optional case-insensitive filtering on those fields. 
    """
    try:
        async with get_db_context(db_config) as session:
            # Base query for the unique document groups
            base_stmt = select(
                KnowledgeChunk.source_title,
                KnowledgeChunk.authors,
                KnowledgeChunk.subject,
                KnowledgeChunk.source_type,
                func.count(KnowledgeChunk.chunk_id).label("chunk_count")
            ).group_by(
                KnowledgeChunk.source_title,
                KnowledgeChunk.authors,
                KnowledgeChunk.subject,
                KnowledgeChunk.source_type
            )

            # Apply filters to the base query
            if title: base_stmt = base_stmt.where(KnowledgeChunk.source_title.ilike(f"%{title}%"))
            if author: base_stmt = base_stmt.where(KnowledgeChunk.authors.ilike(f"%{author}%"))
            if not include_note_taking_agent: 
                base_stmt = base_stmt.where(KnowledgeChunk.authors != "note_taking_agent")
            if subject: base_stmt = base_stmt.where(KnowledgeChunk.subject.ilike(f"%{subject}%"))
            if source_type: base_stmt = base_stmt.where(KnowledgeChunk.source_type.ilike(f"%{source_type}%"))
            if not include_notes:
                base_stmt = base_stmt.where(KnowledgeChunk.source_type != "obsidian_note")

            # Get TOTAL COUNT of unique documents (for UI pagination math)
            count_stmt = select(func.count()).select_from(base_stmt.subquery())
            total_count_res = await session.execute(count_stmt)
            total_count = total_count_res.scalar() or 0

            #  Apply Pagination and Sorting to the base query
            paged_stmt = base_stmt.order_by(KnowledgeChunk.source_title).limit(limit).offset(offset)
            
            result = await session.execute(paged_stmt)
            documents = result.all()
            
            return {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "documents": [
                    {
                        "title": doc.source_title or "Untitled Document",
                        "authors": doc.authors or "Unknown Author",
                        "subject": doc.subject or "general",
                        "type": doc.source_type or "document",
                        "chunks": doc.chunk_count
                    }
                    for doc in documents
                ]
            }
    except Exception as e:
        logger.error(f"❌ Failed to fetch library: {e}")
        return {"total": 0, "documents": []}


async def list_available_sources(tool_context: ToolContext = None) -> str:
    """
    Returns a formatted list of all unique sources (books, websites, papers) 
    currently indexed in the vector database, divided by subject. 
    """
    #TODO might rename this
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

            logger.info(f"Retrieved {len(chunks)} Chunks")

            # Format the response with clear citations 
            formatted_results = [f"### Relevant Passages (Index: {subject_filter or 'All'}):"]
            for i, chunk in enumerate(chunks, 1):
                citation = f"Source: {chunk.source_title} | Authors: {chunk.authors}"
                formatted_results.append(f"{i}. > {chunk.text}\n   *({citation})*")

            return "\n\n".join(formatted_results)

    except Exception as e:
        logger.warning(f"An error occured: {e}")
        return f"An error occurred during the search: {str(e)}"
