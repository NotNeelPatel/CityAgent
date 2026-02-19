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
    Orchestrates the CityAgent pipeline: Fetcher -> Location -> Math -> Reasoner -> Validator.
    Uses reactive logic to skip unnecessary agents and a loop for validation.
    """

    orchestrator_agent: LlmAgent
    data_fetcher: LlmAgent
    location_agent: LlmAgent
    spreadsheet_analyst: LlmAgent
    reasoner_agent: LlmAgent
    validator_agent: LlmAgent
    output_agent: LlmAgent

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        name: str,
        orchestrator_agent: LlmAgent,
        data_fetcher: LlmAgent,
        location_agent: LlmAgent,
        spreadsheet_analyst: LlmAgent,
        reasoner_agent: LlmAgent,
        validator_agent: LlmAgent,
        output_agent: LlmAgent,
    ):
        sub_agents_list = [data_fetcher, location_agent, spreadsheet_analyst, reasoner_agent, validator_agent, output_agent]
        super().__init__(
            name=name,
            orchestrator_agent=orchestrator_agent,
            data_fetcher=data_fetcher,
            location_agent=location_agent,
            spreadsheet_analyst=spreadsheet_analyst,
            reasoner_agent=reasoner_agent,
            validator_agent=validator_agent,
            output_agent=output_agent,
            #sub_agents=sub_agents_list,
        )

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting CityAgent workflow.")

        async for event in self.orchestrator_agent.run_async(ctx):
            yield event

        """
        print("\n\nSTATE:", ctx.session.state)
        query = ctx.session.state.get("prompt", "").lower()
        if any(word in query for word in ["near", "at", "in", "park", "street"]):
            logger.info(f"[{self.name}] Location context detected. Running LocationAgent...")
            async for event in self.location_agent.run_async(ctx):
                yield event

        fetched_data = ctx.session.state.get("raw_data", "")
        if any(char.isdigit() for char in fetched_data):
            logger.info(f"[{self.name}] Numerical data detected. Running SpreadsheetAnalyst...")
            async for event in self.spreadsheet_analyst.run_async(ctx):
                yield event
        """
        is_valid = False
        attempts = 0
        while not is_valid and attempts < 2:
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

        logger.info(f"[{self.name}] Finalizing output...")
        async for event in self.output_agent.run_async(ctx):
            yield event

ai_api = get_agent_model()


reasoner_agent = LlmAgent(
    name="Reasoner",
    model= ai_api,
    instruction="""You are part of the larger CityAgent framework. Using the data fetched by the DataFetcher and any analysis from the SpreadsheetAnalyst, 
    construct a logical response to the user's query. If the data is insufficient or irrelevant, state that clearly.
    Ensure you cite specific data points using the metadata 'filename' and 'last_updated'. DO NOT MENTION PREVIOUS STEPS MADE BY OTHER AGENTS""",
    output_key="reasoning_output",
)

output_agent = LlmAgent(
    name="OutputAgent",
    model= ai_api,
    instruction="""You are part of the larger CityAgent framework. Format the following response
    for the frontend that the user shall see (DO NOT MENTION AGENTS): {{reasoning_output}}

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
    output_key="final_response",
)

validator_agent = LlmAgent(
    name="ValidatorAgent",
    model= ai_api,
    instruction="Set the validation_result to VALID",
    output_key="validation_result",
)

location_agent = LlmAgent(
    name="LocationAgent",
    model= ai_api,
    instruction="""return none""",
    output_key="location_context",
)

spreadsheet_analyst = LlmAgent(
    name="SpreadsheetAnalyst",
    model= ai_api,
    instruction="""You are part of the larger CityAgent framework. Your task is to analyze numerical data. To do so, use the tool get_spreadsheet_info(<filename>) which takes in a query of the filename, and returns the head and first 5 rows of the spreadsheet.
    If there are multiple sheets (like in an excel file), it will return multiple results. Use this tool to get specific data points or statistics, including the following:
    - get_mean(<filename>, <column_name>) returns the mean of a column
    - filter_values(<filename>, <column_name>, <keyword>) returns rows where the column contains the keyword
    Always use these tools to analyze the data instead of trying to do the analysis yourself. Only provide the results of the tool calls in your output, do not provide any reasoning or explanation
    """,
    output_key="math_results",
    tools=[get_spreadsheet_info, get_mean, filter_values],
)

data_fetcher = LlmAgent(
    name="DataFetcher",
    model= ai_api,
    instruction="""
    Your ONLY task is to use 'search_data' to find documents relevant to the prompt.
    - Provide the raw text snippets and citations (filename/last_updated) for all other data.
    - DO NOT perform calculations or answer the user's question directly.
    - DO NOT attempt to search more than 3 times.
    - If you find a relevant spreadsheet (CSV/Excel), explicitly state: "SPREADSHEET_FOUND: [filename]". Tell the Orchestrator Agent to invoke the SpreadsheetAnalyst
    """,
    tools=[search_data],
)

orchestrator_agent = LlmAgent(
    name="CityAgent_Orchestrator",
    model=ai_api,
    instruction="""Analyze the query. 
    1. Invoke data_fetcher to find documents.
    2. If the query involves spreadsheet data, ALWAYS invoke spreadsheet_analyst.
    3. ALWAYS transfer_to_agent to reasoner_agent to construct a response. DO NOT SKIP THE REASONER.""",
    sub_agents=[data_fetcher, spreadsheet_analyst, reasoner_agent]
)

root_agent = OrchestratorAgent(
    name="CityAgent_Orchestrator",
    orchestrator_agent=orchestrator_agent,
    data_fetcher=data_fetcher,
    location_agent=location_agent,
    spreadsheet_analyst=spreadsheet_analyst,
    reasoner_agent=reasoner_agent,
    validator_agent=validator_agent,
    output_agent=output_agent,
)

agent = root_agent