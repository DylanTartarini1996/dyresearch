from enum import Enum
from pydantic import BaseModel, ConfigDict
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
    HF = "hugging-face"


class DBType(str, Enum):
    SQL_LITE = "sql_lite" 
    POSTGRE = "postgre"


class LLMConf(BaseModel):
    """
    Configuration for an LLM
    -----------
    attributes:
    -----------
    `type`: LLM `ModelType` 
    `temperature`: LLM temperature param
    `model`: represents the name of the model
    `api_key`: reference to the OpenAI (or Groq, or Azure OpenAI) API key, if any
    `endpoint`: reference to the endpoint of the model, if any
    """
    model_config = ConfigDict(use_enum_values=True)
    model: str
    temperature: float = 0.0
    type: ModelType="google"
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
    model_config = ConfigDict(use_enum_values=True)
    type: ModelType = "google"
    model: Optional[str] = "gemini-embedding-001"
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
    model_config = ConfigDict(use_enum_values=True)
    db_type: DBType = "sql_lite"
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    database: Optional[str] = None
    timeout: int=5000
    url: Optional[str] = None

    @property
    def is_postgres(self) -> bool:
        """Determines if we are in Postgres mode based on the URL or Host."""
        if self.url and self.url.startswith("postgresql"):
            return True
        if self.host and not self.url:
            return True
        return False

    def get_connection_url(self) -> str:
        if self.url:
            return self.url
        if self.db_type == "postgres":
            return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        return "sqlite+aiosqlite:///./adk_history.db"