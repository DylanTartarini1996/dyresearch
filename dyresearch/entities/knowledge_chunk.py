from sqlalchemy import Column, Integer, Text, String
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from dyresearch.entities import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_title = Column(String, nullable=False)
    chunk_id = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    subject = Column(String, index=True, nullable=False, default="General")
    source_type = Column(String, nullable=True)  # 'book', 'website', 'paper'
    authors = Column(String, nullable=True)
    page_or_url = Column(String, nullable=True)
    embedding = Column(Vector) # NOTE this might vary by embedding model chosen
    embedding_model = Column(String, nullable=True)
    metadatas = Column(JSONB, nullable=True)
    
    def __repr__(self):
        return f"<KnowledgeChunk(source='{self.source_title}', authors='{self.authors}'"