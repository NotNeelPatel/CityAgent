from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import Agent
import os
import asyncio
from city_agent.vector import query_retriever

os.environ["OLLAMA_API_BASE"] = os.getenv("OLLAMA_API_BASE")


async def search_data(query: str) -> str:
    # Offload the (potentially) blocking retriever call to a thread so the
    # async event loop isn't blocked when this tool is used inside an async
    # agent/runtime.
    relevant_data = await asyncio.to_thread(query_retriever, query)
    return relevant_data


root_agent = Agent(
    model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
    name="CityAgent_Orchestrator",
    description=("A helpful assistant for user questions."),
    instruction=(
        'You are CityAgent Orchestrator. Your job is to answer user questions about municipal committees and their fees/expenditures using the tool "search_data(query)". query is the department, committee, service_area, or description relevent to the users question. Use the tool to find relevant information and provide accurate answers. If the tool returns no relevant information, respond with "I could not find any relevant information."'
    ),
    tools=[search_data],
)

"""
Potential questions to ask the agent:
Q: "What is the fence viewer fee in 2025?" 
A: 440

Q: "When does the fee increase for fence viewer services take effect?" 
A: 2025-01-01

Q: "How much did rental prices in Nepean sportplex increase from 2024 to 2025?"

Q: "How many Childrens Services are there?"
"""
