import asyncio
import multiprocessing

from concurrent.futures import ProcessPoolExecutor
from docling.document_converter import DocumentConverter
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownTextSplitter
from typing import List

from ...utils.logger import get_logger

logger = get_logger(__name__)

# Initialize these once at the module level
converter = DocumentConverter()

# TODO move this to configuration
# from docling.datamodel.pipeline_options import PdfPipelineOptions
# from docling.datamodel.base_models import InputFormat
# converter = DocumentConverter(
#      format_options={
#          InputFormat.PDF: PdfFormatOption(
#              pipeline_options=PdfPipelineOptions()
#          ),
#      }
#  )

text_splitter = MarkdownTextSplitter(chunk_size=5000, chunk_overlap=200)
# # TODO move this to configuration
# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size=5000, 
#     chunk_overlap=200,
#     separators=["\n## ", "\n### ", "\n\n", "\n", " "]
# )

# Initialize the global Process Pool
# We leave 1 core free so OS/FastAPI loop stays highly responsive
WORKER_COUNT = max(1, multiprocessing.cpu_count() - 1)
docling_executor = ProcessPoolExecutor(max_workers=WORKER_COUNT)


#  Synchronous CPU-heavy worker function
def _sync_ingest_and_chunk(file_path: str) -> List[str]:
    """
    This runs in an entirely separate process. 
    It cannot use the global logger cleanly, so we return the raw data.
    """
    conversion_result = converter.convert(file_path)
    markdown_content = conversion_result.document.export_to_markdown()

    chunks = text_splitter.split_text(markdown_content)
    return chunks


# The Async Bridge 
async def ingest_and_chunk_file(file_path: str, source_name: str) -> List[str]:
    """
    Async wrapper that sends the Docling conversion to a separate CPU core,
    keeping the FastAPI event loop completely unblocked.
    """
    loop = asyncio.get_running_loop()
    
    try:
        # Send the heavy lifting to the process pool
        chunks = await loop.run_in_executor(
            docling_executor,
            _sync_ingest_and_chunk,
            file_path
        )
        
        logger.info(f"Split document from {source_name} into {len(chunks)} chunks")
        return chunks

    except Exception as e:
        logger.error(f"Error processing {source_name}: {e}")
        raise e