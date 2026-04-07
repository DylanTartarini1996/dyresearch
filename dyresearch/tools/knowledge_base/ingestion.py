from typing import List
from docling.document_converter import DocumentConverter
from langchain_text_splitters import RecursiveCharacterTextSplitter

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

# TODO move this to configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000, 
    chunk_overlap=200,
    separators=["\n## ", "\n### ", "\n\n", "\n", " "]
)

# NOTE modify this to work with images, tables etc..
async def ingest_and_chunk_file(file_path: str, source_name: str) -> List[str]:
    """
    Core function to parse a file into Markdown format and split it into chunks. 
    """
    try:
        conversion_result = converter.convert(file_path)
        markdown_content = conversion_result.document.export_to_markdown()

        chunks = text_splitter.split_text(markdown_content)
        
        logger.info(f"Split document from {source_name} into {len(chunks)} chunks")
        return chunks

    except Exception as e:
        logger.error(f"Error processing {source_name}: {e}")
        raise e