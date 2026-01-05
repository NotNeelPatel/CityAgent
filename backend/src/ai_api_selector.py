from enum import Enum
import os
from google.adk.models.lite_llm import LiteLlm
from langchain_ollama import OllamaEmbeddings
from langchain_openai import AzureOpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()
AI_API_PROVIDER = os.getenv("AI_API_PROVIDER")

# Almost all LLMS support at least 32k token sizes, with most supporting >128k token sizes
# Default context window size is set to 32k for max compatibility. 
AGENT_CTX_WINDOW_SIZE = os.getenv("AGENT_CTX_WINDOW_SIZE") or "32000"

# Configuration for AI provider
class AIProvider(Enum):
    OLLAMA = "OLLAMA"
    AZURE = "AZURE"
    OPENAI = "OPENAI"


# Used to select Agent model
def get_agent_model() -> LiteLlm:
    if AI_API_PROVIDER == AIProvider.AZURE.value:
        ai_api = LiteLlm(model="azure/gpt-oss-120b")
    elif AI_API_PROVIDER == AIProvider.OLLAMA.value:
        os.environ["OLLAMA_API_BASE"] = os.getenv("OLLAMA_API_BASE")
        ai_api = LiteLlm(model="ollama_chat/gpt-oss:20b")
    elif AI_API_PROVIDER == AIProvider.OPENAI.value:
        ai_api = LiteLlm(
            model="openai/gpt-oss:latest",
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
        )
    return ai_api


# Used to select Embedding model
def get_embedding_model():
    if AI_API_PROVIDER == AIProvider.AZURE.value:
        embeddings = AzureOpenAIEmbeddings(
            model="text-embedding-ada-002",
            api_key=os.getenv("AZURE_API_KEY_EMBEDDING"),
            azure_endpoint=os.getenv("AZURE_API_BASE_EMBEDDING"),
            api_version=os.getenv("AZURE_API_VERSION_EMBEDDING"),
        )
    elif AI_API_PROVIDER == AIProvider.OLLAMA.value:
        embeddings = OllamaEmbeddings(
            model="nomic-embed-text:v1.5", base_url=os.getenv("OLLAMA_API_BASE")
        )
    elif AI_API_PROVIDER == AIProvider.OPENAI.value:
        embeddings = OpenAIEmbeddings(
            model="embeddinggemma:300m",
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
        )
    return embeddings

# Used to get the context window size of the agent (important for vectorization chunking)
def get_agent_ctx_window_size():
    return int(AGENT_CTX_WINDOW_SIZE)