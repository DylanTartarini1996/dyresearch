import json

from enum import Enum
from pydantic import BaseModel
from typing import Optional

from .utils.logger import get_logger


logger = get_logger(__name__)


class ModelType(str, Enum):
    """
    Type of embedders available in the toolkit
    """
    AZURE_OPENAI = "azure-openai"
    GOOGLE = "google"
    GROQ = "groq"
    OPENAI = "openai"
    OLLAMA = "ollama"
    TRANSFORMERS = "trf"


class ChunkerType(str, Enum):
    """
    Type of chunkers available in the toolkit
    """
    RECURSIVE = "recursive"
    # PLAIN = "plain" # TODO implement plain chunker
    # SEMANTIC = "semantic" # TODO implement SEMANTIC chunker


class Source(BaseModel):
    folder: str
    # TODO add specific source configurations


class ChunkerConf(BaseModel):
    type: ChunkerType = "recursive"
    chunk_size: int = 1000
    chunk_overlap: int = 100


class LLMConf(BaseModel):
    """
    Configuration for an LLM
    -----------
    attributes:
    -----------
    `type`: LLM `ModelType` 
    `temperature`: LLM temperature param
    `deployment`: represents the name of the deployment.
    `model`: represents the name of the model
    `api_key`: reference to the OpenAI (or Groq, or Azure OpenAI) API key, if any
    `endpoint`: reference to the endpoint of the model, if any
    """
    model: str
    temperature: float = 0.0
    type: ModelType="openai"
    deployment: Optional[str]=None
    api_key: Optional[str]=None
    endpoint: Optional[str]=None
    api_version: Optional[str] = None


class EmbedderConf(BaseModel):
    """
    Embeddings model configuration  

    -----------
    attributes:
    -----------
    `type`: LLM `ModelType` 
    `deployment`: represents the name of the deployment.
    `model`: represents the name of the model
    `api_key`: reference to the OpenAI (or Azure OpenAI) API key, if any
    `endpoint`: reference to the endpoint of the model, if any
    """
    type: ModelType = "openai"
    model: Optional[str] = "text-embedding-ada-002"
    deployment: Optional[str] = None
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    api_version: Optional[str] = None


class DBConfig(BaseModel):
    """ 
    Configuration for the backend Database used for memory management.

    -----------
    attributes:
    -----------
    `password`: `str`
    `host`: `str`
    `port`: `int`
    `user`: `str`
    `password`: `str`
    `database`: `str`
    `timeout`: `int`
    `url`: `str`
    """
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    database: Optional[str] = None
    timeout: int=5000
    url: Optional[str] = None
