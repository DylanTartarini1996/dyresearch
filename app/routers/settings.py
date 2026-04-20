from fastapi import APIRouter, HTTPException

from app.settings.config_manager import FullConfiguration, config_manager
from dyresearch.utils.logger import get_logger

logger = get_logger(__name__)

settings_router = APIRouter(prefix="/settings", tags=["Settings"])

@settings_router.get("", response_model=FullConfiguration)
async def get_settings():
    config = config_manager.load()
    if config.default_llm.api_key:
        config.default_llm.api_key = "sk-..." + config.default_llm.api_key[-4:]
    for agent in config.agent_configs.values():
        if agent.api_key:
            agent.api_key = "sk-..." + agent.api_key[-4:]
    return config

@settings_router.post("")
async def update_settings(new_config: FullConfiguration):
    """Updates and persists the configuration."""
    try:
        config_manager.save(new_config)
        return {"status": "success", "message": "Configuration updated and saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@settings_router.get("/status")
async def get_status():
    """Checks if the engine has valid API keys to run."""
    config = config_manager.load()