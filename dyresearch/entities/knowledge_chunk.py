from sqlalchemy import Column, Integer, Text, String, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector

from dyresearch.entities import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    source_title = Column(String, nullable=True)
    subject = Column(String, index=True, nullable=False, default="General")
    source_type = Column(String, nullable=True)  # 'book', 'website', 'paper'
    authors = Column(String, nullable=True)
    page_or_url = Column(String, nullable=True)
    embedding = Column(Vector(dim=768)) # NOTE this might vary by embedding model chosen
    embedding_model = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<KnowledgeChunk(source='{self.source_title}', authors='{self.authors}')>"