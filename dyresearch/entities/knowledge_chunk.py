import os
from sqlalchemy import Column, Integer, String, Text, JSON

from app.settings.config_manager import config_manager
from . import Base

# Add this check at the top of your entities file
# IS_POSTGRES = os.getenv("DB_HOST") is not None

current_config = config_manager.load()
IS_POSTGRES = current_config.db.is_postgres

# Swap Vector for a dummy type and JSONB for standard JSON if on SQLite
if IS_POSTGRES:
    from pgvector.sqlalchemy import Vector
    from sqlalchemy.dialects.postgresql import JSONB
    EmbeddingType = Vector # Match model's dimensions
    MetadataType = JSONB
else:
    EmbeddingType = JSON # SQLite handles vectors as JSON/Blobs
    MetadataType = JSON  # Standard JSON for SQLite

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_title = Column(String, nullable=False)
    chunk_id = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    subject = Column(String, index=True, nullable=False, default="general")
    source_type = Column(String, nullable=True) 
    authors = Column(String, nullable=True)
    page_or_url = Column(String, nullable=True)
    embedding = Column(EmbeddingType) 
    metadatas = Column(MetadataType, nullable=True)
    
    embedding_model = Column(String, nullable=True)

    def __repr__(self):
        return f"<KnowledgeChunk(source='{self.source_title}', authors='{self.authors}')>"