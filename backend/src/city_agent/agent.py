import logging
from typing import AsyncGenerator
from typing_extensions import override

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

import asyncio
from rag_pipeline.vector import query_retriever
from ai_api_selector import get_agent_model


async def search_data(query: str) -> str:
    # Offload the (potentially) blocking retriever call to a thread so the
    # async event loop isn't blocked when this tool is used inside an async
    # agent/runtime.
    relevant_data = await asyncio.to_thread(query_retriever, query)
    return relevant_data

logger = logging.getLogger(__name__)

# --- Custom Orchestrator Agent ---
class OrchestratorAgent(BaseAgent):
    """
    Orchestrates the CityAgent pipeline: Fetcher -> Location -> Math -> Reasoner -> Validator.
    Uses reactive logic to skip unnecessary agents and a loop for validation.
    """

    # Field Declarations for Pydantic
    data_fetcher: LlmAgent
    location_agent: LlmAgent
    math_analyst: LlmAgent
    reasoner_agent: LlmAgent
    validator_agent: LlmAgent
    output_agent: LlmAgent

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        name: str,
        data_fetcher: LlmAgent,
        location_agent: LlmAgent,
        math_analyst: LlmAgent,
        reasoner_agent: LlmAgent,
        validator_agent: LlmAgent,
        output_agent: LlmAgent,
    ):
        # We define sub_agents for the framework to manage their lifecycle
        sub_agents_list = [data_fetcher, location_agent, math_analyst, reasoner_agent, validator_agent, output_agent]
        super().__init__(
            name=name,
            data_fetcher=data_fetcher,
            location_agent=location_agent,
            math_analyst=math_analyst,
            reasoner_agent=reasoner_agent,
            validator_agent=validator_agent,
            output_agent=output_agent,
            sub_agents=sub_agents_list,
        )

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting CityAgent workflow.")

        
        # 1. DATA FETCHER (Foundational step)
        async for event in self.data_fetcher.run_async(ctx):
            yield event

        # 2. REACTIVE LOCATION AGENT
        # Only run if the query or fetched data suggests a geographical context
        """
        print("\n\nSTATE:", ctx.session.state)
        query = ctx.session.state.get("prompt", "").lower()
        if any(word in query for word in ["near", "at", "in", "park", "street"]):
            logger.info(f"[{self.name}] Location context detected. Running LocationAgent...")
            async for event in self.location_agent.run_async(ctx):
                yield event

        # 3. REACTIVE MATH ANALYST
        # Check if numerical data was fetched that needs processing
        fetched_data = ctx.session.state.get("raw_data", "")
        if any(char.isdigit() for char in fetched_data):
            logger.info(f"[{self.name}] Numerical data detected. Running MathAnalyst...")
            async for event in self.math_analyst.run_async(ctx):
                yield event
        """
        # 4. REASONING & VALIDATION LOOP (The Core Logic)
        is_valid = False
        attempts = 0
        while not is_valid and attempts < 2:
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
            is_valid = True

        # 5. FINAL OUTPUT
        # Pass the validated reasoning to the Output Agent for formatting
        logger.info(f"[{self.name}] Finalizing output...")
        async for event in self.output_agent.run_async(ctx):
            yield event

# --- Agent Definitions ---

ai_api = get_agent_model()

data_fetcher = LlmAgent(
    name="DataFetcher",
    model= ai_api,
    instruction="You are CityAgent DataFetcher, part of the larger CityAgent framework. Your task is to fetch relevant data based on a user's query. If no relevant data is found or the query is inappropriate given the context of providing an answer relating to the City of Ottawa asset management, respond with a string that says 'no data found'. Only provide raw data output that is relevant to the query.",
    output_key="raw_data",
    tools=[search_data],
)

reasoner_agent = LlmAgent(
    name="Reasoner",
    model= ai_api,
    instruction="""You are CityAgent Reasoner, part of the larger CityAgent framework. Using the data in {{raw_data}}, 
    construct a logical response to the user's query. If the data is insufficient or irrelevant, state that clearly.
    Ensure you cite specific data points.""",
    output_key="reasoning_output",
)

output_agent = LlmAgent(
    name="OutputAgent",
    model= ai_api,
    instruction="""You are CityAgent OutputAgent, part of the larger CityAgent framework. Format the following response into a clean, professional response 
    for the frontend that the user shall see (DO NOT MENTION OTHER AGENTS): {{reasoning_output}}

    Use the following format for your answers, if there are no sources, still include an empty sources list.:
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

math_analyst = LlmAgent(
    name="MathAnalyst",
    model= ai_api,
    instruction="""return none""",
    output_key="math_results",
)

root_agent = OrchestratorAgent(
    name="CityAgent_Orchestrator",
    data_fetcher=data_fetcher,
    location_agent=location_agent,
    math_analyst=math_analyst,
    reasoner_agent=reasoner_agent,
    validator_agent=validator_agent,
    output_agent=output_agent,
)

agent = root_agent