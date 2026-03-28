import os
import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional
from ..config import EmbedderConf
from ..utils.logger import get_logger

logger = get_logger(__name__)


embedder_conf = EmbedderConf()


class BaseEmbedder(ABC):
    """Universal interface for all embedding providers."""
    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of document strings."""
        pass


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, conf: EmbedderConf):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=conf.api_key)
        self.model = conf.model

    async def embed_query(self, text: str) -> List[float]:
        res = await self.client.embeddings.create(input=text, model=self.model)
        return res.data[0].embedding

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        res = await self.client.embeddings.create(input=texts, model=self.model)
        return [record.embedding for record in res.data]

class AzureOpenAIEmbedder(BaseEmbedder):
    def __init__(self, conf: EmbedderConf):
        from openai import AsyncAzureOpenAI
        self.client = AsyncAzureOpenAI(
            api_key=conf.api_key,
            api_version=conf.api_version,
            azure_endpoint=conf.endpoint,
            azure_deployment=conf.deployment
        )
        self.model = conf.model

    async def embed_query(self, text: str) -> List[float]:
        res = await self.client.embeddings.create(input=text, model=self.model)
        return res.data[0].embedding

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        res = await self.client.embeddings.create(input=texts, model=self.model)
        return [record.embedding for record in res.data]

class OllamaEmbedder(BaseEmbedder):
    def __init__(self, conf: EmbedderConf):
        import ollama
        self.client = ollama.AsyncClient(host=getattr(conf, 'host', 'http://localhost:11434'))
        self.model = conf.model

    async def embed_query(self, text: str) -> List[float]:
        res = await self.client.embeddings(model=self.model, prompt=text)
        return res['embedding']

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Ollama usually handles batches sequentially or via internal threading
        tasks = [self.embed_query(t) for t in texts]
        return await asyncio.gather(*tasks)

class HFEmbedder(BaseEmbedder):
    def __init__(self, conf: EmbedderConf):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(conf.model)

    async def embed_query(self, text: str) -> List[float]:
        # Run in executor if the library is CPU-heavy and blocking
        return self.model.encode(text).tolist()

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()


def get_embeddings(conf: EmbedderConf) -> Optional[BaseEmbedder]:
    """
    Returns the correct async embedder based on configuration.
    Dependencies are only imported when the specific type is called.
    """
    try:
        if conf.type == "ollama":
            return OllamaEmbedder(conf)
            
        elif conf.type == "openai":
            return OpenAIEmbedder(conf)
            
        elif conf.type == "azure-openai":
            return AzureOpenAIEmbedder(conf)
            
        elif conf.type == "hf":
            return HFEmbedder(conf)
            
        else:
            logger.warning(f"Embedder type '{conf.type}' not supported.")
            return None
            
    except ImportError as e:
        logger.error(f"Missing dependency for embedder '{conf.type}': {e}")
        raise ImportError(f"Please install the required library for {conf.type} (e.g., openai, sentence-transformers, etc.)")