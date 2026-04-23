from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all entities here so they are registered with Base.metadata
from .knowledge_chunk import KnowledgeChunk
