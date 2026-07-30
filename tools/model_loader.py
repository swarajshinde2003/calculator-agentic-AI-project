import os
import logging
from typing import Literal
from utils.config_loader import load_config
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(self, model_provider: Literal["ollama"] = "ollama"):
        self.model_provider = model_provider
        self.config = load_config()

    def load_llm(self):
        """Load and return the configured LLM."""
        logger.info("Loading LLM...")
        ollama_api_key = os.getenv("OLLAMA_API_KEY")
        if not ollama_api_key:
            raise EnvironmentError(
                "OLLAMA_API_KEY environment variable is not set. "
                "Add it to your .env file before starting the backend."
            )
        model = self.config["llm"]["ollama"]["model_name"]
        base_url = self.config["llm"]["ollama"]["base_url"]
        logger.info("LLM loaded: model=%s  base_url=%s", model, base_url)
        return ChatOpenAI(model=model, base_url=base_url, api_key=ollama_api_key)