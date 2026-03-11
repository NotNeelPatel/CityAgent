import logging
from typing import AsyncGenerator
from typing_extensions import override

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

import asyncio
from src.rag_pipeline.vector import query_retriever
from src.ai_api_selector import get_agent_model
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
    purge_cached_files,
)

search_data_count = 0

# Max number of times the agent can call search_data tool per query.
MAX_SEARCH_CALLS = 3


def _tool_error(tool_name: str, error: Exception) -> str:
    return f"TOOL_ERROR|tool={tool_name}|message={str(error)}"


# Convert synchronous spreadsheet analysis tools to asynchronous versions using asyncio.to_thread
async def get_spreadsheet_info(filename: str) -> str:
    try:
        return await asyncio.to_thread(get_spreadsheet_info_impl, filename)
    except Exception as e:
        return _tool_error("get_spreadsheet_info", e)


async def get_mean(filename: str, column_name: str) -> float:
    try:
        return await asyncio.to_thread(get_mean_impl, filename, column_name)
    except Exception as e:
        return _tool_error("get_mean", e)


async def filter_values(filename: str, columns: list, keyword: str) -> str:
    try:
        return await asyncio.to_thread(filter_values_impl, filename, columns, keyword)
    except Exception as e:
        return _tool_error("filter_values", e)


async def get_unique_values(filename: str, column_name: str) -> str:
    try:
        return await asyncio.to_thread(get_unique_values_impl, filename, column_name)
    except Exception as e:
        return _tool_error("get_unique_values", e)


async def count_values(filename: str, column_name: str) -> str:
    try:
        return await asyncio.to_thread(count_values_impl, filename, column_name)
    except Exception as e:
        return _tool_error("count_values", e)


async def get_min_in_column(filename: str, column_name: str) -> float:
    try:
        return await asyncio.to_thread(get_min_in_column_impl, filename, column_name)
    except Exception as e:
        return _tool_error("get_min_in_column", e)


async def get_max_in_column(filename: str, column_name: str) -> float:
    try:
        return await asyncio.to_thread(get_max_in_column_impl, filename, column_name)
    except Exception as e:
        return _tool_error("get_max_in_column", e)


async def get_sum_in_column(filename: str, column_name: str) -> float:
    try:
        return await asyncio.to_thread(get_sum_in_column_impl, filename, column_name)
    except Exception as e:
        return _tool_error("get_sum_in_column", e)


async def get_sum_of_filtered_values(
    filename: str, column_name: str, keyword: str
) -> float:
    try:
        return await asyncio.to_thread(
            get_sum_of_filtered_values_impl, filename, column_name, keyword
        )
    except Exception as e:
        return _tool_error("get_sum_of_filtered_values", e)


async def filter_values_in_range(
    filename: str, column_name: str, min_value: float, max_value: float
) -> str:
    try:
        return await asyncio.to_thread(
            filter_values_in_range_impl, filename, column_name, min_value, max_value
        )
    except Exception as e:
        return _tool_error("filter_values_in_range", e)


async def search_data(query: str) -> str:
    """
    Offload the (potentially) blocking retriever call to a thread so the
    async event loop isn't blocked when this tool is used inside an async
    agent/runtime.
    """
    global search_data_count
    if search_data_count >= MAX_SEARCH_CALLS:
        return "Search data tool has been called too many times for this query. This limit will reset for the next query."
    try:
        relevant_data = await asyncio.to_thread(query_retriever, query)
        search_data_count += 1
        return relevant_data
    except Exception as e:
        return _tool_error("search_data", e)


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
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        global search_data_count
        logger.info(f"[{self.name}] Starting CityAgent workflow.")

        is_valid = False
        attempts = 0
        search_data_count = 0
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
        purge_cached_files()  # Clear cached files after processing the query


ai_api = get_agent_model()

reasoner_agent = LlmAgent(
    name="Reasoner",
    model=ai_api,
    instruction="""
    You are the CityAgent Reasoner. Your job is to synthesize a final answer
    based ONLY on the information provided by the data_analyst.

    RULES:
    * Source Integrity: You may only list a file along with its last_updated
    information in the sources array if it
    was explicitly provided in the current context.
    * Grounded Response: If the provided data does not contain the answer,
    state clearly that the information is unavailable.
    * No Agent Speak: Do not mention the DataAnalyst or previous internal
    steps taken. Speak directly to the user.
    * Filter: If the question is not about the City of Ottawa,
    your response key must be: "I'm sorry, I can only answer questions
    related to the City of Ottawa.".

    OUTPUT FORMAT:
    You MUST output in minified JSON format only:
    {
    "response": "<your detailed answer here>",
    "sources": [
    {
        "filename": "<exact_filename_from_context>",
        "lastUpdated": "<date_from_metadata>",
        "href": "#"
    }
    ]
    }
    If no sources exist, return "sources": [].
    """,
)

validator_agent = LlmAgent(
    name="ValidatorAgent",
    model=ai_api,
    instruction="Set the validation_result to VALID",
    output_key="validation_result",
)

data_analyst = LlmAgent(
    name="DataAnalyst",
    model=ai_api,
    instruction="""
    You are the CityAgent Data Analyst. You must use specialized Python tools
    to query and analyze City of Ottawa assets.

    STRICT TOOL PROTOCOL:
    1. Discovery: Use 'search_data' first to find filenames.
    2. Validation: If the file is a spreadsheet (.csv/.xlsx), you MUST use
    the tools below.
    3. No Regex: The 'keyword' argument in all tools is a simple string.
    DO NOT use regex patterns, wildcards, or boolean logic.
    4. Case Insensitivity: All tools handle case-insensitivity internally.

    TOOL REFERENCE:
    * get_spreadsheet_info(filename): Returns headers/first 5 rows.
    * get_mean(filename, column_name): Numeric average only.
    * get_unique_values(filename, column_name): Returns up to 20 unique items.
    * count_values(filename, column_name): Frequency of values in a column.
    * get_min_in_column / get_max_in_column: Finds numeric extremes.
    * filter_values(filename, columns, keyword): 'columns' MUST be a list.
    Example: ["Street Name", "Condition"].
    * filter_values_in_range(filename, column_name, min_value, max_value):
    Requires numeric floats for min/max.
    * get_sum_of_filtered_values(filename, column_name, keyword): Sums a
    column after filtering by a simple string keyword.

    OUTPUT REQUIREMENT:
    Provide the raw output of the tool, the filename, and 'last_updated'
    from metadata. If a tool returns 'Column not found', check the
    headers using 'get_spreadsheet_info' and retry once.
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
    instruction="""
    You are the CityAgent Orchestrator. Your sole responsibility is to analyze
    the user's query and coordinate the data_analyst to gather information.

    STRICT CONSTRAINTS:
    * DO NOT attempt to answer the user's question yourself.
    * DO NOT make assumptions about City of Ottawa assets.
    * If the query is not related to City of Ottawa Asset Management (e.g.,
    "What is the capital of France?"), respond exactly with:
    "irrelevant question".

    OPERATIONAL PROTOCOL:
    1. Assess Relevance: Determine if the query is about Ottawa infrastructure,
    roads, parks, or municipal assets.
    2. Formulate a Search Plan: Identify what specific points or
    documents are missing to fulfill the request.
    3. Delegate: Invoke the data_analyst to perform the actual data retrieval
    and technical analysis using its available tools.
    4. Pass the user's original intent and your refined plan to the sub-agent.
    """,
    sub_agents=[data_analyst],
)

root_agent = OrchestratorAgent(
    name="CityAgent_Root",
    orchestrator_agent=orchestrator_agent,
    data_analyst=data_analyst,
    reasoner_agent=reasoner_agent,
    validator_agent=validator_agent,
)

agent = root_agent
