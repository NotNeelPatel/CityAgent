import logging
from typing import AsyncGenerator
from typing_extensions import override

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

import asyncio
from rag_pipeline.vector import query_retriever
from ai_api_selector import get_agent_model
from city_agent.agent_tools.spreadsheet_analysis_tools import (
    get_spreadsheet_info_impl,
    get_mean_impl,
    filter_values_impl,
    get_unique_values_impl,
    count_values_impl,
    get_min_in_column_impl,
    get_max_in_column_impl,
    filter_values_in_range_impl,
    get_sum_in_column_impl,
    get_sum_of_filtered_values_impl,
)

search_data_count = 0

# Max number of times the agent can call search_data tool per query.
MAX_SEARCH_CALLS = 3

# Convert synchronous spreadsheet analysis tools to asynchronous versions using asyncio.to_thread
async def get_spreadsheet_info(filename: str) -> str:
    return await asyncio.to_thread(get_spreadsheet_info_impl, filename)

async def get_mean(filename: str, column_name: str) -> float:
    return await asyncio.to_thread(get_mean_impl, filename, column_name)

async def filter_values(filename: str, columns: list, keyword: str) -> str:
    return await asyncio.to_thread(filter_values_impl, filename, columns, keyword)

async def get_unique_values(filename: str, column_name: str) -> str:
    return await asyncio.to_thread(get_unique_values_impl, filename, column_name)

async def count_values(filename: str, column_name: str) -> str:
    return await asyncio.to_thread(count_values_impl, filename, column_name)

async def get_min_in_column(filename: str, column_name: str) -> float:
    return await asyncio.to_thread(get_min_in_column_impl, filename, column_name)

async def get_max_in_column(filename: str, column_name: str) -> float:
    return await asyncio.to_thread(get_max_in_column_impl, filename, column_name)

async def get_sum_in_column(filename: str, column_name: str) -> float:
    return await asyncio.to_thread(get_sum_in_column_impl, filename, column_name)

async def get_sum_of_filtered_values(filename: str, column_name: str, keyword: str) -> float:
    return await asyncio.to_thread(get_sum_of_filtered_values_impl, filename, column_name, keyword)

async def filter_values_in_range(filename: str, column_name: str, min_value: float, max_value: float) -> str:
    return await asyncio.to_thread(filter_values_in_range_impl, filename, column_name, min_value, max_value)

async def search_data(query: str) -> str:
    """
    Offload the (potentially) blocking retriever call to a thread so the
    async event loop isn't blocked when this tool is used inside an async
    agent/runtime.
    """
    global search_data_count
    if(search_data_count >= MAX_SEARCH_CALLS):
        return "Search data tool has been called too many times for this query. This limit will reset for the next query."
    relevant_data = await asyncio.to_thread(query_retriever, query)
    search_data_count += 1
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
        super().__init__(
            name=name,
            orchestrator_agent=orchestrator_agent,
            data_analyst=data_analyst,
            reasoner_agent=reasoner_agent,
            validator_agent=validator_agent,
        )

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        global search_data_count
        logger.info(f"[{self.name}] Starting CityAgent workflow.")


        is_valid = False
        attempts = 0
        search_data_count = 0 
        print("search_data_count reset to 0 at start of workflow")
        while not is_valid and attempts < 2:
            async for event in self.orchestrator_agent.run_async(ctx):
                yield event
            
            logger.info(f"[{self.name}] Running Reasoner (Attempt {attempts + 1})...")
            async for event in self.reasoner_agent.run_async(ctx):
                yield event
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
    If the question is not relevant to City of Ottawa, the "response" key should be "I'm sorry, I can only answer questions related to the City of Ottawa.".
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
    - If you find a relevant spreadsheet (csv/xlsx), use the following tools to analyze it:
    - get_spreadsheet_info(<filename>) which takes in a query of the filename, and returns the head and first 5 rows of the spreadsheet.
    - If there are multiple sheets (like in an excel file), it will return multiple results.
    - get_mean(<filename>, <column_name>) returns the mean of a column.
    - get_unique_values(<filename>, <column_name>) returns unique values for a column.
    - count_values(<filename>, <column_name>) returns counts for each unique value in a column.
    - get_min_in_column(<filename>, <column_name>) returns the minimum numeric value in a column.
    - get_max_in_column(<filename>, <column_name>) returns the maximum numeric value in a column.
    - filter_values(<filename>, <columns>, <keyword>) returns rows with keyword in specified columns.
    - filter_values_in_range(<filename>, <column_name>, <min_value>, <max_value>) returns rows with values in a specified column within a range.
    - get_sum_in_column(<filename>, <column_name>) returns the sum of a numeric column.
    - get_sum_of_filtered_values(<filename>, <column_name>, <keyword>) returns the sum of values in a numeric column for rows that contain the keyword.
    """,
    tools=[
        search_data,
        get_spreadsheet_info,
        get_mean,
        get_unique_values,
        count_values,
        get_min_in_column,
        get_max_in_column,
        filter_values,
        filter_values_in_range,
        get_sum_in_column,
        get_sum_of_filtered_values,
    ],
)

orchestrator_agent = LlmAgent(
    name="CityAgent_Orchestrator",
    model=ai_api,
    instruction="""Analyze the query. Invoke data_analyst to find documents.
    The data_analyst also has spreadsheet analysis tools. If the prompt
    is not relevant to City of Ottawa Asset Management, respond with 
    "irrelevant question".
    """,
    sub_agents=[data_analyst]
)

root_agent = OrchestratorAgent(
    name="CityAgent_Root",
    orchestrator_agent=orchestrator_agent,
    data_analyst=data_analyst,
    reasoner_agent=reasoner_agent,
    validator_agent=validator_agent,
)

agent = root_agent