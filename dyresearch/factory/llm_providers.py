from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm

from ..config import LLMConf, ModelType
from ..utils.logger import get_logger

load_dotenv("config.env")

logger = get_logger(__name__)


def get_litellm_model(conf: LLMConf) -> LiteLlm:

    if conf.type == ModelType.AZURE_OPENAI:
        model=f"azure/{conf.model}"
    elif conf.type == ModelType.OLLAMA:
        model=f"ollama/{conf.model}"
    elif conf.type == ModelType.TRANSFORMERS:
        model=f"huggingface/{conf.model}"
    elif conf.type == ModelType.GOOGLE:
        model=f"{conf.model}"
    elif conf.type == ModelType.GROQ:
        model=f"groq/{conf.model}"
    else: 
        logger.error(f"❌ Model of type {conf.type} is not implemented yet!")
        return None

    if model:
        llm = LiteLlm(
            model=model,
            api_key=conf.api_key,
            api_base=conf.endpoint,
            api_version=conf.api_version,
        )

        logger.info(f"✅ Initialized LiteLLM with model type: {conf.type}")

        return llm
        