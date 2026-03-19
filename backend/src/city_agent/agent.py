import logging
import json
from typing import Any, AsyncGenerator, Callable
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
from city_agent.error_codes import ErrorCode

search_data_count = 0

# Max number of times the agent can call search_data tool per query.
MAX_SEARCH_CALLS = 3


def _tool_error(tool_name: str, error: Exception) -> str:
    return json.dumps(
        {
            "status": "error",
            "tool": tool_name,
            "data": None,
            "error": {
                "code": ErrorCode.TOOL_EXECUTION_ERROR.value,
                "message": str(error),
            },
        },
        ensure_ascii=True,
    )


def _tool_success(tool_name: str, data: dict) -> str:
    return json.dumps(
        {
            "status": "success",
            "tool": tool_name,
            "data": data,
            "error": None,
        },
        ensure_ascii=True,
    )


def _is_tool_error(payload: Any) -> bool:
    if not isinstance(payload, str):
        return False
    try:
        decoded = json.loads(payload)
    except Exception:
        return False
    if not isinstance(decoded, dict):
        return False
    return decoded.get("status") == "error"


async def _run_tool(tool_name: str, tool_func: Callable[..., Any], *args: Any) -> Any:
    """Run sync tool code in a thread and convert failures to non-throwing tool errors."""
    try:
        return await asyncio.to_thread(tool_func, *args)
    except Exception as e:
        return _tool_error(tool_name, e)


# Convert synchronous spreadsheet analysis tools to asynchronous versions using asyncio.to_thread
async def get_spreadsheet_info(filename: str) -> str:
    return await _run_tool("get_spreadsheet_info", get_spreadsheet_info_impl, filename)


async def get_mean(filename: str, column_name: str) -> str:
    return await _run_tool("get_mean", get_mean_impl, filename, column_name)


async def filter_values(filename: str, columns: list, keyword: str) -> str:
    return await _run_tool("filter_values", filter_values_impl, filename, columns, keyword)


async def get_unique_values(filename: str, column_name: str) -> str:
    return await _run_tool("get_unique_values", get_unique_values_impl, filename, column_name)


async def count_values(filename: str, column_name: str) -> str:
    return await _run_tool("count_values", count_values_impl, filename, column_name)


async def get_min_in_column(filename: str, column_name: str) -> str:
    return await _run_tool("get_min_in_column", get_min_in_column_impl, filename, column_name)


async def get_max_in_column(filename: str, column_name: str) -> str:
    return await _run_tool("get_max_in_column", get_max_in_column_impl, filename, column_name)


async def get_sum_in_column(filename: str, column_name: str) -> str:
    return await _run_tool("get_sum_in_column", get_sum_in_column_impl, filename, column_name)


async def get_sum_of_filtered_values(
    filename: str,
    column_name: str,
    keyword: str,
    filter_column: str = "",
) -> str:
    resolved_filter_column = filter_column.strip() or None
    return await _run_tool(
        "get_sum_of_filtered_values",
        get_sum_of_filtered_values_impl,
        filename,
        column_name,
        keyword,
        resolved_filter_column,
    )


async def filter_values_in_range(
    filename: str, column_name: str, min_value: float, max_value: float
) -> str:
    return await _run_tool(
        "filter_values_in_range",
        filter_values_in_range_impl,
        filename,
        column_name,
        min_value,
        max_value,
    )


async def search_data(query: str) -> str:
    """
    Offload the (potentially) blocking retriever call to a thread so the
    async event loop isn't blocked when this tool is used inside an async
    agent/runtime.
    """
    global search_data_count
    if search_data_count >= MAX_SEARCH_CALLS:
        return json.dumps(
            {
                "status": "error",
                "tool": "search_data",
                "data": None,
                "error": {
                    "code": ErrorCode.MAX_SEARCH_CALLS_EXCEEDED.value,
                    "message": "Search data tool has been called too many times for this query. This limit will reset for the next query.",
                },
            },
            ensure_ascii=True,
        )
    relevant_data = await _run_tool("search_data", query_retriever, query)
    if _is_tool_error(relevant_data):
        return relevant_data
    search_data_count += 1
    return _tool_success(
        "search_data",
        {
            "query": query,
            "result": relevant_data,
        },
    )


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
    * No Agent Speak: Do not mention the DataAnalyst, search failures, or
    previous internal steps taken. Speak directly to the user. Frame missing
    data not as a failure, but as an opportunity to narrow down the search.
    * Filter: If the question is not about the City of Ottawa,
    your response key must be: "I'm sorry, I can only answer questions
    related to the City of Ottawa.".
    * Conversational Clarification (CRITICAL): If the retrieved data only
    partially answers the user, or if the initial query was too broad to yield
    a specific result, you MUST end your response with a targeted follow-up
    question. Ask the user for the exact missing details needed to run a better
    search (e.g., "I found the general road maintenance files, but to get you the
    exact cost, could you clarify if you are looking for a specific year or a
    particular street?").

    NUMERIC VALIDATION RULES:
    * If the question asks for a total, sum, or numeric result:
        * Ensure the response includes a numeric value from tool output
        * If no numeric value is present, state that the total could not be computed
        * Do NOT infer or estimate totals

    OUTPUT FORMAT:
    You MUST output in minified JSON format only:
    {
    "response": "<your detailed answer here, ending with a follow-up question if context is missing>",
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
    You are the CityAgent Data Analyst, an expert in querying and analyzing City of Ottawa assets. Your primary directive is accuracy and resilience. City datasets often contain inconsistent naming conventions, abbreviations, and acronyms. You must anticipate these discrepancies and navigate them proactively.

    STRICT TOOL PROTOCOL & WORKFLOW:

    1. Discovery & General Search:
    * ALWAYS begin with 'search_data'.
    * Formulate broad search queries. Do not over-constrain the initial search.
    * If the first search yields 0 results, strip your query down to the single most vital keyword and try again before giving up.

    2. Proactive Schema Inspection (CRITICAL - LOOK BEFORE YOU LEAP):
    * NEVER guess a column name for computation tools (like get_mean or filter_values) unless you are 100% certain of the exact string.
    * If you have a target spreadsheet but don't know the exact headers, you MUST run `get_spreadsheet_info` FIRST to map the user's request to the actual column names (e.g., mapping a request for "PQI" to the actual header "Pavement Quality Index (PQI)").

    3. Aggressive Keyword Normalization:
    * When filtering or searching within a dataset, you must reduce keywords to their absolute root to avoid formatting mismatches.
    * Strip all street types (Street, St, Ave, Avenue, Rd, Road). Search "Bank", not "Bank St".
    * Anticipate acronyms. If searching for "Condition", the data might say "Cond". If searching for "Pavement Quality", it might say "PQI". Use `get_unique_values` to verify how the data is actually formatted before applying a filter.

    4. Smart Filtering & Tool Selection:
    * If no filtering condition is present -> use get_sum_in_column.
    * If a filtering condition is present -> use get_sum_of_filtered_values WITH filter_column explicitly defined.
    * Do not use the legacy all-column fallback unless absolutely necessary.

    5. Tool Constraints:
    * NO REGEX. The 'keyword' argument is a simple string.
    * All tools are case-insensitive.
    * You may only use the specialized spreadsheet tools on files ending in .csv or .xlsx.

    TOOL REFERENCE (SPREADSHEETS ONLY):
    * get_spreadsheet_info(filename): Returns headers/first 5 rows.
    * get_mean(filename, column_name): Numeric average only.
    * get_unique_values(filename, column_name): Returns up to 20 unique items.
    * count_values(filename, column_name): Frequency of values in a column.
    * get_min_in_column / get_max_in_column: Finds numeric extremes.
    * get_sum_in_column(filename, column_name): Sums all values in a numeric column.
    * filter_values(filename, columns, keyword): 'columns' MUST be a list.
    * filter_values_in_range(filename, column_name, min_value, max_value): Requires numeric floats.
    * get_sum_of_filtered_values(filename, column_name, keyword, filter_column=""): Sums values in column_name after filtering by keyword.

    OUTPUT REQUIREMENT:
    All final responses MUST be structured JSON with keys: status, tool, data, error.
    * If status="success": populate the 'data' object. Include filename and 'last_updated' from metadata.
    * If status="error": follow error handling below.
    * NO AGENT SPEAK: Output ONLY the requested JSON or tool call. Do not explain your workflow.

    ERROR RECOVERY:
    * COLUMN_NOT_FOUND -> This means you failed step 2. Call get_spreadsheet_info immediately to find the real header name and retry.
    * NON_NUMERIC_SUM_COLUMN -> The column contains text. Call get_spreadsheet_info to find the correct numeric column.
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
