import os
from time import ctime
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from google.adk.sessions import InMemorySessionService
from langchain_core.documents import Document
import json
import asyncio
import uuid
from ai_api_selector import get_agent_model
from ai_api_selector import get_agent_ctx_window_size
import pymupdf4llm
from pydantic import BaseModel, Field

_INSTRUCTIONS = """
You are an expert data extraction agent specialized in Municipal Asset Management reports. 
Your task is to analyze the provided document text and extract structured information for a vector database.

CORE EXTRACTION RULES:
1. Language Filtering: Many of these documents are bilingual. Extract ONLY English content. Completely ignore and discard all French translations.
2. Table Conversion: Locate all data tables. Reconstruct them accurately using Markdown table syntax within the 'content_body' field.
3. Metric Identification: Search for specific financial figures, percentages, condition ratings (e.g., "Good", "Poor", "1-10"), and dates. Populate the 'key_metrics' array with these findings.
4. Context Preservation: The 'context_header' should summarize the specific section or sub-section being processed so the vector search has localized context.

DATA CLASSIFICATION GUIDELINES:
- Service Area: Identify the infrastructure group (e.g., "Transportation", "Water & Sewer", "Facilities", "Parks"). If generic, use "Citywide".
- Data Type: Classify the section type (e.g., "Financial Strategy", "Condition Assessment", "Level of Service", "Inventory").
- Topic: Provide a brief 2-4 word description of the specific subject (e.g., "Bridge Lifecycle Costs").

OUTPUT REQUIREMENT:
Extract the data and populate the fields exactly as defined in the provided schema. Ensure the 'content_body' is comprehensive enough for semantic retrieval.
"""

# Define Pydantic models for structured output
class Metadata(BaseModel):
    source_file: str = Field(description="The name of the source PDF file.")
    service_area: str = Field(description="Specific name like 'Transportation' or 'Citywide'.")
    topic: str = Field(description="The primary topic discussed in this section.")
    data_type: str = Field(description="Category like 'Financial Analysis' or 'Condition Report'.")

class PageContent(BaseModel):
    context_header: str = Field(description="The heading or context for this specific chunk.")
    content_body: str = Field(description="The main text content, with tables converted to Markdown.")
    key_metrics: list[str] = Field(description="List of numerical figures, percentages, and date ranges.")

class OutputSchema(BaseModel):
    metadata: Metadata
    page_content: PageContent

APP_NAME = "Vectorize_PDF_App"
USER_ID = "2468"
SESSION_ID = "session2468"

ai_api = get_agent_model()

agent = LlmAgent(
    model=ai_api,
    name="PDF_Vectorization_Agent",
    instruction=_INSTRUCTIONS,
    include_contents= "none",
    output_schema = OutputSchema,
)

async def get_or_create_session(app_name: str, user_id: str, session_id: str):
    """Return an existing session or create a new in-memory session.

    Uses the `session_service` (InMemorySessionService) to fetch a
    session by `app_name`, `user_id`, and `session_id`. If no session
    exists, a new one is created and returned.

    Args:
        app_name (str): Application name for session namespace.
        user_id (str): User identifier.
        session_id (str): Session identifier.

    Returns:
        Session: The retrieved or newly-created session object.
    """

    existing_session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if existing_session:
        return existing_session
    else:
        return await session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )


session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)


async def call_agent(
    runner_instance: Runner, agent_instance: LlmAgent, session_id: str, query: str
):
    """Send a query to the LLM agent and return the final textual response.

    The function builds a `types.Content` message from `query`, runs the
    agent via `runner_instance.run_async`, iterates events until the
    final response is received, and returns the textual content of that
    final response. The raw response is printed for debugging.

    Args:
        runner_instance (Runner): ADK Runner used to execute the agent.
        agent_instance (LlmAgent): The configured LLM agent instance.
        session_id (str): Session identifier to use for the run.
        query (str): The user message / instruction to send.

    Returns:
        str: The final textual response produced by the agent.
    """

    content = types.Content(role="user", parts=[types.Part(text=query)])

    final_response_content = "No final response received."
    async for event in runner_instance.run_async(
        user_id=USER_ID, session_id=session_id, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response_content = event.content.parts[0].text

    print(
        f"\n\n<<< Agent '{agent_instance.name}' Response: {final_response_content}\n\n"
    )

    return final_response_content


async def vectorize_pdf(filepath: str):
    """
    Asynchronously vectorize a PDF into a list of langchain_core.documents.Document objects and their UUIDs.
    Behavior:
    - Ensures the provided filepath points to a .pdf file.
    - Creates or retrieves an in-memory session for the application.
    - Converts the PDF to markdown via pymupdf4llm.to_markdown().
    - Splits the markdown into chunks based on the agent context window size and sends each chunk to an LLM agent via call_agent().
    - Concatenates the agent's chunked JSON responses into a single JSON payload keyed by the filepath, then parses and normalizes the resulting data into a list of "knowledge objects".
    - For each knowledge object, prefers page_content.content_body as the document text; falls back to the whole object JSON if necessary.
    - Merges any provided metadata, and adds/overrides source_file (basename of filepath) and last_updated (file modification time).
    - Constructs a Document for each item with a generated UUID and returns (documents, ids).
    Args:
        filepath (str): Path to the PDF file to process. Must end with ".pdf".
    Returns:
        Tuple[List[Document], List[str]]: A tuple containing a list of Document objects and a parallel list of UUID strings.
    Raises:
        ValueError: If filepath does not end with ".pdf".
        OSError: If there is an error accessing the file metadata.
        Any exceptions raised by call_agent, pymupdf4llm.to_markdown, or session management may propagate.
    Side effects and notes:
    - Prints debug information (agent responses and parsed item count).
    - Depends on external services: an LLM agent (call_agent/runner), pymupdf4llm, and an in-memory session service.
    - Assumes the agent returns valid minified JSON fragments that can be concatenated into a valid JSON array/object using the filepath as a key.
    """

    session_service = await get_or_create_session(APP_NAME, USER_ID, SESSION_ID)

    if(not filepath.endswith(".pdf")):
        raise ValueError("File is not a PDF")
        return
        
    query = pymupdf4llm.to_markdown(filepath) 

    ctx_window_size = get_agent_ctx_window_size()
    # According to OpenAI, 1 token ≈ 4 characters
    # Reserve half the space for each chunk (remaining space will be necessary for the LLM's output)
    chunk_size = ctx_window_size // 8
    overlap_size = chunk_size // 10
    doc_length = len(query)
    num_chunks = doc_length // chunk_size + 1
    knowledge_objects = []

    for i in range(num_chunks):
        start = min(chunk_size * i, abs(chunk_size * i - overlap_size)) 
        end = min(doc_length, chunk_size * (i+1))
        response = await call_agent(runner, agent, SESSION_ID, query[start:end])
        try:
            chunk = json.loads(response)
            knowledge_objects.append(chunk)
        except json.JSONDecodeError as e:
            print(f"JSON decode error for chunk {i}: {e}")
    
    documents = []
    ids = []

    # Convert knowledge objects to Langchain Documents
    for item in knowledge_objects:
        content = item["page_content"]["content_body"]
        meta = item["metadata"]
        meta["source_file"] = os.path.basename(filepath)
        meta["last_updated"] = str(ctime(os.path.getmtime(filepath)))

        _id = str(uuid.uuid4())
        doc = Document(page_content=content, metadata=meta)
        ids.append(_id)
        documents.append(doc)

    return documents, ids


if __name__ == "__main__":
    asyncio.run(vectorize_pdf(r"path-to-your-file"))

    # kill the session to free up memory since it's being stored in application memory currently
    # TODO: Maybe store in postgres to reuse sessions?
    session_service.delete_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
