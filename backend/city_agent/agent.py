from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import Agent
import os

os.environ["OLLAMA_API_BASE"] = os.getenv('OLLAMA_API_BASE')

async def search_data(query:str) -> str:
    return f"The draft budget for the year {query} was $20"

root_agent = Agent(
    model=LiteLlm(
        model="ollama_chat/gpt-oss:20b"
    ),
    name="CityAgent_Orchestrator",
    description=('A helpful assistant for user questions.'),
    instruction=('Answer user questions to the best of your knowledge. You have access to the tool "search_data" which you can get the draft budget for any year by calling search_data(query), where query is the year'),
    tools=[search_data],
)
