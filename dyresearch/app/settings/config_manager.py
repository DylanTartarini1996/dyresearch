import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from platformdirs import user_config_dir
from pydantic import BaseModel, Field

from .. import APP_NAME
from ...core.config import DBConfig, EmbedderConf, LLMConf, ModelType
from ...core.utils.logger import get_logger

# Load environment variables once at the start of config management
load_dotenv()

logger = get_logger(__name__)


def get_default_llm() -> LLMConf:
    return LLMConf(
        model=os.getenv("GOOGLE_MODEL_NAME", "gemini-3.5-flash"),
        type=ModelType.GOOGLE,
        api_key=os.getenv("GOOGLE_API_KEY")
    )


def get_default_db() -> DBConfig:
    return DBConfig(
        url=os.getenv("SESSION_SERVICE_URI", "sqlite+aiosqlite:///./adk_history.db")
    )


def get_default_embedder() -> EmbedderConf: 
    return EmbedderConf(
        type=os.getenv("EMBEDDINGS_TYPE", "google"),
        model=os.getenv("EMBEDDINGS_MODEL_NAME", "gemini-embedding-001"),
        api_key=os.getenv("EMBEDDINGS_API_KEY") 
    )


class FullConfiguration(BaseModel):
    # The default config to use if a specific agent isn't configured
    default_llm: LLMConf = Field(default_factory=get_default_llm)
    embedder: EmbedderConf = Field(default_factory=get_default_embedder)
    db: DBConfig = Field(default_factory=get_default_db)

    # Specific configurations for each agent
    agent_configs: Dict[str, LLMConf] = Field(default_factory=lambda: {
        "coordinator": get_default_llm(),
        "professor": get_default_llm(),
        "librarian": get_default_llm(),
        "notetaker": get_default_llm(),
        "researcher": get_default_llm()
    })

    def get_llm_conf_for_agent(self, agent_name: str) -> LLMConf:
        """Helper to get an agent's config or fall back to default"""
        return self.agent_configs.get(agent_name, self.default_llm)
    

class ConfigManager:
    def __init__(self):
        self.config_dir = Path(user_config_dir(APP_NAME))
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> FullConfiguration:
        if not self.config_file.exists():
            return FullConfiguration()
        try:
            with open(self.config_file, "r") as f:
                return FullConfiguration.model_validate_json(f.read())
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return FullConfiguration()

    def save(self, config: FullConfiguration):
        with open(self.config_file, "w") as f:
            f.write(config.model_dump_json(indent=4))
        self.apply_to_env(config)

    def apply_to_env(self, config: FullConfiguration):
        """Sets environment variables based on the configuration."""
        if config.default_llm.api_key:
            os.environ["GOOGLE_API_KEY"] = config.default_llm.api_key
        
        if config.db.url:
            os.environ["SESSION_SERVICE_URI"] = config.db.url

        if config.embedder.api_key:
            os.environ["EMBEDDINGS_API_KEY"] = config.embedder.api_key

        logger.info("Configuration applied to environment")


config_manager = ConfigManager()
# Apply initial config to env
config_manager.apply_to_env(config_manager.load())

def get_db_mode() -> bool:
    """Helper to get the current DB mode without importing the whole app."""
    try:
        return config_manager.load().db.is_postgres
    except Exception:
        return False