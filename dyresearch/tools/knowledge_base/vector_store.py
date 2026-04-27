import json
import os
import lancedb

from typing import Dict, List, Optional
from google.adk.tools.tool_context import ToolContext
from sqlalchemy import select, delete, func

from app.settings.config_manager import config_manager
from .ingestion import ingest_and_chunk_file
from ...entities.knowledge_chunk import KnowledgeChunk
from ...factory.database import db_config, get_db_context
from ...factory.embeddings import BaseEmbedder, embedder_conf, get_embeddings
from ...utils.logger import get_logger


logger = get_logger(__name__)
current_config = config_manager.load()


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
                        embedding=vector if current_config.db.is_postgres else None,
                        subject=subject.lower(),
                        embedding_model=embedder.model,
                        metadatas=metadatas
                    )
                    session.add(new_chunk)
                
                # 3. Intermediate Commit (Flush to DB)
                logger.info(f"💾 Committing batch {i//batch_size + 1} to Postgres...")
                await session.commit() 

                # LOCAL MODE EXTRA STEP: Sync to LanceDB
                if not current_config.db.is_postgres:
                    db = lancedb.connect("./.dyresearch_vectors")
                    table_name = "knowledge_chunks"
                    
                    # Prepare data for LanceDB
                    data = [{
                        "vector": vector, 
                        "text": text, 
                        "source_title": title,
                        "subject": subject.lower()
                    } for text, vector in zip(batch_text, batch_vectors)]
                    
                    if table_name not in db.table_names():
                        db.create_table(table_name, data=data)
                    else:
                        db.open_table(table_name).add(data)

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
            # 1. Relational Deletion (Handles Postgres or SQLite)
            stmt = delete(KnowledgeChunk).where(KnowledgeChunk.source_title == title)
            result = await session.execute(stmt)
            deleted_count = result.rowcount
            
            if deleted_count == 0:
                return f"Could not find any source named '{title}' in the library."

            # 2. Vector Store Deletion (LanceDB specific)
            if not current_config.db.is_postgres:
                try:
                    db = lancedb.connect("./.dyresearch_vectors")
                    if "knowledge_chunks" in db.table_names():
                        table = db.open_table("knowledge_chunks")
                        # Sanitize single quotes for the LanceDB filter string
                        safe_title = title.replace("'", "''")
                        table.delete(f"source_title = '{safe_title}'")
                        logger.info(f"LanceDB synced: deleted vectors for {title}")
                except Exception as ve:
                    logger.warning(f"Metadata deleted but LanceDB sync failed: {ve}")

            await session.commit()
            return f"✅ Successfully removed '{title}' from the library. ({deleted_count} chunks deleted)."

    except Exception as e:
        logger.error(f"Failed to delete source '{title}': {str(e)}")
        return f"Failed to delete source '{title}': {str(e)}"
    

async def delete_by_subject(subject: str) -> str:
    """
    Deletes ALL knowledge chunks associated with a specific subject index.  

    Use this to clear an entire category (e.g., 'physics', 'temp_research') from the library.
    """
    if not subject:
        return "Error: Please provide a valid subject name."
    
    target_subject = subject.lower()

    try:
        async with get_db_context(db_config) as session:
            # 1. Relational Deletion
            stmt = delete(KnowledgeChunk).where(KnowledgeChunk.subject == target_subject)
            result = await session.execute(stmt)
            deleted_count = result.rowcount
            
            if deleted_count == 0:
                return f"No records found for subject '{subject}'."

            # 2. Vector Store Deletion (LanceDB specific)
            if not current_config.db.is_postgres:
                try:
                    db = lancedb.connect("./.dyresearch_vectors")
                    if "knowledge_chunks" in db.table_names():
                        table = db.open_table("knowledge_chunks")
                        table.delete(f"subject = '{target_subject}'")
                        logger.info(f"LanceDB synced: purged subject index '{target_subject}'")
                except Exception as ve:
                    logger.warning(f"Metadata deleted but LanceDB sync failed: {ve}")

            await session.commit()
            return f"🗑️ Bulk Delete Successful! Removed the '{subject}' index ({deleted_count} chunks)."
        
    except Exception as e:
        return f"Failed to perform bulk delete on subject '{subject}': {str(e)}"

    
async def search_knowledge_base(
    query: str, 
    subject_filter: Optional[str] = "",
    limit: int = 5, 
    retrieve_adjacent_chunks: bool = False,
    tool_context: ToolContext = None
    ) -> str:
    """
    Performs a semantic search across the research library and returns relevant text passages.
    
    This tool uses vector similarity to find the most relevant information. To provide 
    better context for complex reasoning, it can optionally reconstruct the surrounding 
    narrative of a hit.

    -------
    Params:
    -------
    `query`: `str` 
        The specific question or topic to search for in the vector store.
    `subject_filter`: `Optional[str]`
        Filters results to a specific research area (e.g., 'machine_learning' or 'physics'). 
        Defaults to searching the entire library.
    `limit`: `int`
        The number of top-k similar chunks to retrieve. Defaults to 5.
    `retrieve_adjacent_chunks`: bool 
        If `True`, fetches the immediate preceding (n-1) and succeeding (n+1) chunks for every similarity hit. 
        Useful when a hit is a partial sentence or needs broader context. 
        **Note:** This significantly increases the returned text volume.

    --------
    Returns:
    --------
    `str`: A formatted Markdown string containing the retrieved passages, 
    grouped by source document with full citations (Source Title and Authors). 
    Returns a "No results found" message if the search yields no hits.
    """
    embedder = get_embeddings(embedder_conf)
    if not embedder:
        return "Error: Embedder not configured."

    try:
        query_vector = await embedder.embed_query(query)
        chunks = []

        # ---- DOCKER / CLOUD MODE: pgvector ----
        if current_config.db.is_postgres: 
            async with get_db_context(db_config) as session:
                stmt = select(KnowledgeChunk)
                if subject_filter:
                    stmt = stmt.where(KnowledgeChunk.subject == subject_filter.lower())
                stmt = stmt.order_by(KnowledgeChunk.embedding.cosine_distance(query_vector)).limit(limit)
                result = await session.execute(stmt)
                chunks = result.scalars().all()
                
                if retrieve_adjacent_chunks and chunks:
                    final_chunks = list(chunks)
                    for chunk in chunks:
                        neighbor_stmt = select(KnowledgeChunk).where(
                            KnowledgeChunk.source_title == chunk.source_title,
                            KnowledgeChunk.chunk_id.in_([chunk.chunk_id - 1, chunk.chunk_id + 1])
                        )
                        neighbor_result = await session.execute(neighbor_stmt)
                        final_chunks.extend(neighbor_result.scalars().all())
                    chunks = final_chunks

        # ---- LOCAL MODE: LanceDB ---- 
        else:
            db = lancedb.connect("./.dyresearch_vectors")
            table = db.open_table("knowledge_chunks")
            
            search_query = table.search(query_vector).limit(limit)
            if subject_filter:
                search_query = search_query.where(f"subject = '{subject_filter.lower()}'")
            
            results = search_query.to_list()
            # FIX: Ensure chunk_id and id are captured for neighbors/dedup
            chunks = [
                KnowledgeChunk(
                    id=r.get("id"),
                    text=r["text"], 
                    source_title=r["source_title"],
                    chunk_id=r.get("chunk_id") 
                ) for r in results
            ]

            if retrieve_adjacent_chunks and chunks:
                final_chunks = list(chunks)
                for chunk in chunks:
                    if chunk.chunk_id is not None:
                        # Query LanceDB for the neighbors
                        neighbors = table.search().where(
                            f"source_title = '{chunk.source_title}' AND chunk_id IN ({chunk.chunk_id - 1}, {chunk.chunk_id + 1})"
                        ).to_list()
                        final_chunks.extend([KnowledgeChunk(**n) for n in neighbors])
                chunks = final_chunks

        if not chunks:
            return f"I searched the library but found no relevant documents."
        
        logger.info(f"Retrieved {len(chunks)} Chunks")

        # ---- DEDUPLICATION & SORTING ----
        # Use ID if available, otherwise fallback to text hash
        unique_chunks = {getattr(c, 'id', hash(c.text)): c for c in chunks}.values()
        sorted_chunks = sorted(unique_chunks, key=lambda x: (x.source_title, x.chunk_id or 0))

        # ---- FORMATTING ----
        logger.info(f"Returning {len(sorted_chunks)} Chunks to Agent")
        formatted_results = [f"### Knowledge Base Results (Adjacent Context: {'On' if retrieve_adjacent_chunks else 'Off'}):"]
        
        current_source = ""
        for chunk in sorted_chunks:
            if chunk.source_title != current_source:
                formatted_results.append(f"\n--- From: **{chunk.source_title}** ---")
                current_source = chunk.source_title
            formatted_results.append(f"> ... {chunk.text.strip()} ...")

        return "\n".join(formatted_results)

    except Exception as e:
        logger.error(f"Search Error: {e}", exc_info=True)
        return f"An error occurred during the search: {str(e)}"