import logging
from typing import AsyncGenerator
from typing_extensions import override

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

import asyncio
from rag_pipeline.vector import query_retriever
from ai_api_selector import get_agent_model
from city_agent.agent_tools.math_analyst_tools import get_spreadsheet_info_impl, get_mean_impl, filter_values_impl

async def get_spreadsheet_info(filename: str) -> str:
    return await asyncio.to_thread(get_spreadsheet_info_impl, filename)

async def get_mean(filename: str, column_name: str) -> float:
    return await asyncio.to_thread(get_mean_impl, filename, column_name)

async def filter_values(filename: str, column_name: str, keyword: str) -> str:
    return await asyncio.to_thread(filter_values_impl, filename, column_name, keyword)

async def search_data(query: str) -> str:
    """
    Offload the (potentially) blocking retriever call to a thread so the
    async event loop isn't blocked when this tool is used inside an async
    agent/runtime.
    """
    relevant_data = await asyncio.to_thread(query_retriever, query)
    return relevant_data

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    Orchestrates the CityAgent pipeline: DataAnalyst -> Reasoner -> Validator.
    Uses reactive logic to skip unnecessary agents and a loop for validation.
    """

    orchestrator_agent: LlmAgent
    data_analyst: LlmAgent
    reasoner_agent: LlmAgent
    validator_agent: LlmAgent

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        name: str,
        orchestrator_agent: LlmAgent,
        data_analyst: LlmAgent,
        reasoner_agent: LlmAgent,
        validator_agent: LlmAgent,
    ):
        sub_agents_list = [data_analyst, reasoner_agent, validator_agent,]
        super().__init__(
            name=name,
            orchestrator_agent=orchestrator_agent,
            data_analyst=data_analyst,
            reasoner_agent=reasoner_agent,
            validator_agent=validator_agent,
            #sub_agents=sub_agents_list,
        )

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting CityAgent workflow.")


        is_valid = False
        attempts = 0
        while not is_valid and attempts < 2:
            async for event in self.orchestrator_agent.run_async(ctx):
                yield event
            
            async for event in self.reasoner_agent.run_async(ctx):
                yield event
            #logger.info(f"[{self.name}] Running Reasoner (Attempt {attempts + 1})...")
            """
            logger.info(f"[{self.name}] Validating response...")
            async for event in self.validator_agent.run_async(ctx):
                yield event
            # Check validation result stored in session state by the Validator agent
            if ctx.session.state.get("validation_result") == "VALID":
                is_valid = True
            else:
                attempts += 1
                logger.warning(f"[{self.name}] Validation failed. Feedback: {ctx.session.state.get('validator_agent_feedback')}")
            """
            # Validator not implemented, assume always valid
            is_valid = True


ai_api = get_agent_model()

reasoner_agent = LlmAgent(
    name="Reasoner",
    model= ai_api,
    instruction="""You are part of the larger CityAgent framework. Using the data fetched by the DataAnalyst and any analysis from the SpreadsheetAnalyst, 
    construct a logical response to the user's query. If the data is insufficient or irrelevant, state that clearly.
    Ensure you cite specific data points using the metadata 'filename' and 'last_updated'. DO NOT MENTION PREVIOUS STEPS MADE BY OTHER AGENTS
    Use the following format for your answers, if there are no sources, still include an empty sources list.
    ONLY output in minified JSON format as follows:
    {
    "response": "<final formatted answer here>",
    "sources": [{"filename": "<filename>",
        "lastUpdated": "2026-10-01",
        "href": "#",
        }]
    }
    """,
)

validator_agent = LlmAgent(
    name="ValidatorAgent",
    model= ai_api,
    instruction="Set the validation_result to VALID",
    output_key="validation_result",
)

data_analyst = LlmAgent(
    name="DataAnalyst",
    model= ai_api,
    instruction="""
    Your task is to use 'search_data' to find documents relevant to the prompt, note that there are dedicated spreadsheet tools for better searching.
    - Provide the raw text snippets and citations (filename/last_updated) for all other data.
    - DO NOT attempt to search more than 3 times.
    - If you find a relevant spreadsheet (CSV/Excel), use the following tools to analyze it:
    - get_spreadsheet_info(<filename>) which takes in a query of the filename, and returns the head and first 5 rows of the spreadsheet.
    - If there are multiple sheets (like in an excel file), it will return multiple results.
    - get_mean(<filename>, <column_name>) returns the mean of a column
    - filter_values(<filename>, <column_name>, <keyword>) returns rows where the column contains the keyword. ALWAYS INVOKE filter_values if there is a spreadsheet to ensure full coverage
    """,
    tools=[search_data, get_spreadsheet_info, get_mean, filter_values],
)

orchestrator_agent = LlmAgent(
    name="CityAgent_Orchestrator",
    model=ai_api,
    instruction="""Analyze the query. Invoke data_analyst to find documents. If the prompt seems inappropriate, respond with "invalid prompt".
    """,
    sub_agents=[data_analyst, reasoner_agent]
)

root_agent = OrchestratorAgent(
    name="CityAgent_Orchestrator",
    orchestrator_agent=orchestrator_agent,
    data_analyst=data_analyst,
    reasoner_agent=reasoner_agent,
    validator_agent=validator_agent,
)

agent = root_agent