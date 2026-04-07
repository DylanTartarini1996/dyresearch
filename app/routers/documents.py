import json
import shutil
from pathlib import Path
from fastapi import APIRouter, Form, UploadFile, File
from typing import List

from dyresearch.tools.knowledge_base.vector_store import ingest_source_chunks
from dyresearch.tools.knowledge_base.ingestion import ingest_and_chunk_file
from dyresearch.utils.logger import get_logger

logger = get_logger(__name__)

doc_router = APIRouter(tags=["documents"])

# Temporary storage for processing
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@doc_router.post("/ingest")
async def ingest_documents(
    files: List[UploadFile] = File(...),
    subject: str = Form(default="General"),
    source_type: str = Form(default="document"),
    authors: str = Form(default="Unknown"),
    metadata_json: str = Form(default="{}")
    ):

    results = []

    # Parse the metadata string back into a Python dictionary
    try:
        extra_metadata = json.loads(metadata_json)
    except json.JSONDecodeError:
        extra_metadata = {}
        
    for file in files:
        file_path = UPLOAD_DIR / file.filename
        try:
            
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            chunks = await ingest_and_chunk_file(file_path=file_path, source_name=file.filename)

            file_metadata = {
                "filename": file.filename,
                **extra_metadata
            }
            
            ingestion_msg = await ingest_source_chunks(
                content_chunks=chunks, 
                subject=subject,
                title=file.filename,
                source_type=source_type,
                authors=authors,
                metadatas=file_metadata
            )

            logger.debug(f"{ingestion_msg}")

            results.append({"filename": file.filename, "status": "success"})
        except Exception as e:
            logger.error(f"Failed to ingest {file.filename}: {e}")
            results.append({"filename": file.filename, "status": "error", "detail": str(e)})
        
        finally:
            if file_path.exists():
                file_path.unlink() 
                
    return {"results": results}