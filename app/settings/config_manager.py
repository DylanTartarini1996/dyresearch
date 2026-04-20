from pathlib import Path
from typing import Dict

from platformdirs import user_config_dir
from pydantic import BaseModel, Field

from app import APP_NAME

from dyresearch.config import DBConfig, EmbedderConf, LLMConf
from dyresearch.utils.logger import get_logger

logger = get_logger(__name__)


class FullConfiguration(BaseModel):
    # The default config to use if a specific agent isn't configured
    default_llm: LLMConf = LLMConf(model="gemini-3.1-flash-lite-preview", type="google")
    
    embedder: EmbedderConf = EmbedderConf()
    db: DBConfig = DBConfig()

    # Specific configurations for each agent
    agent_configs: Dict[str, LLMConf] = Field(default_factory=lambda: {
        "coordinator": LLMConf(model="gemini-3.1-flash-lite-preview", type="google"),
        "professor": LLMConf(model="gemini-3.1-flash-lite-preview", type="google"),
        "librarian": LLMConf(model="gemini-3.1-flash-lite-preview-mini", type="google"),
        "notetaker": LLMConf(model="gemini-3.1-flash-lite-preview-mini", type="google"),
        "researcher": LLMConf(model="gemini-3.1-flash-lite-preview-mini", type="google")
    })

    def get_llm_for_agent(self, agent_name: str) -> LLMConf:
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


config_manager = ConfigManager()