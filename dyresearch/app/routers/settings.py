from fastapi import APIRouter, HTTPException

from ..settings.config_manager import FullConfiguration, config_manager
from ...core.utils.logger import get_logger

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
    if config.embedder.api_key:
        config.embedder.api_key = "sk-..." + config.embedder.api_key[-4:]
    return config

@settings_router.post("")
async def update_settings(new_config: FullConfiguration):
    """Updates and persists the configuration."""
    try:
        current_config = config_manager.load()
        
        # 1. Protect Default LLM Key
        if new_config.default_llm.api_key and new_config.default_llm.api_key.startswith("sk-..."):
            new_config.default_llm.api_key = current_config.default_llm.api_key

        # 2. Protect Agent Keys
        for agent_name, agent_cfg in new_config.agent_configs.items():
            if agent_cfg.api_key and agent_cfg.api_key.startswith("sk-..."):
                # Grab the actual key from the existing config
                old_key = current_config.agent_configs.get(agent_name, current_config.default_llm).api_key
                agent_cfg.api_key = old_key
                
        # 3. Protect Embedder Key (NEW)
        if new_config.embedder.api_key and new_config.embedder.api_key.startswith("sk-..."):
            new_config.embedder.api_key = current_config.embedder.api_key

        config_manager.save(new_config)
        return {"status": "success", "message": "Configuration updated and saved"}
        
    except Exception as e:
        logger.error(f"Save failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@settings_router.get("/status")
async def get_status():
    """Checks if the engine has valid API keys to run."""
    config = config_manager.load()