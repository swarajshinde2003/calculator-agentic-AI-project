import os
from dotenv import load_dotenv
from typing import Literal , Optional, Any
from pydantic import BaseModel , Field
from utils.config_loader import load_config
from langchain_openai import ChatOpenAI


class ModelLoader :
    def __init__(self, model_provider  : Literal["ollama"] = "ollama"):
        self.model_provider  = model_provider
        self.config = load_config()
    
    def load_llm(self):
        """Load and return the LLM """
        print("LLM loading....")
        ollama_api_key = os.getenv("OLLAMA_API_KEY")
        if not ollama_api_key:
            raise EnvironmentError("API key not found")
        model = self.config["llm"]["ollama"]["model_name"]
        base_url = self.config["llm"]["ollama"]["base_url"]
        
        llm = ChatOpenAI(
            model = model,
            base_url= base_url,
            api_key=ollama_api_key
        )
        return llm 