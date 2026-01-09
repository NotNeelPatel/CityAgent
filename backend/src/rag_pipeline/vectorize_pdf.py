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

_INSTRUCTIONS = """
You are a document processing assistant for asset management reports. 
Your goal is to transform provided text into a structured JSON format.

### Tasks:
- Translate all visible data tables into standard Markdown syntax.
- Extract only English text content.
- Identify and list specific figures, percentages, and dates in the metrics field.
- Provide a summary of the current section in the context header.
- Use the following classifications:
    - Service Area: (e.g., Transportation, Water, Facilities)
    - Data Type: (e.g., Financial, Condition, Inventory)
    - Topic: A brief subject label.

### Schema Requirements:
Ensure the output follows the keys and structure provided in the JSON schema section.
"""

OUTPUT_SCHEMA_DICT = {
    "type": "object",
    "properties": {
        "metadata": {
            "type": "object",
            "properties": {
                "source_file": {"type": "string", "description": "The name of the source PDF file."},
                "service_area": {"type": "string", "description": "Specific name like 'Transportation' or 'Citywide'."},
                "topic": {"type": "string", "description": "The primary topic discussed in this section."},
                "data_type": {"type": "string", "description": "Category like 'Financial Analysis' or 'Condition Report'."}
            },
            "required": ["source_file", "service_area", "topic", "data_type"],
            "additionalProperties": False
        },
        "page_content": {
            "type": "object",
            "properties": {
                "context_header": {"type": "string", "description": "The heading or context for this specific chunk."},
                "content_body": {"type": "string", "description": "The main text content, with tables converted to Markdown."},
                "key_metrics": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "List of numerical figures, percentages, and date ranges."
                }
            },
            "required": ["context_header", "content_body", "key_metrics"],
            "additionalProperties": False
        }
    },
    "required": ["metadata", "page_content"],
    "additionalProperties": False
}

APP_NAME = "Vectorize_PDF_App"
USER_ID = "2468"
SESSION_ID = "session2468"

ai_api = get_agent_model()

agent = LlmAgent(
    model=ai_api,
    name="PDF_Vectorization_Agent",
    instruction=f"{_INSTRUCTIONS}\n\nSTRICT REQUIREMENT: Return ONLY a valid JSON object matching this schema:\n{json.dumps(OUTPUT_SCHEMA_DICT, indent=2)}",
    include_contents= "none",
    generate_content_config={
        "response_mime_type": "application/json",
    }
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

    attempts = 0
    chunk_number = 0
    while (chunk_number < num_chunks):
        attempts += 1
        start = min(chunk_size * chunk_number, abs(chunk_size * chunk_number - overlap_size)) 
        end = min(doc_length, chunk_size * (chunk_number+1))
        response = await call_agent(runner, agent, SESSION_ID, query[start:end])
        try:
            chunk = json.loads(response)
            knowledge_objects.append(chunk)
            attempts = 0
        except json.JSONDecodeError as e:
            print(f"JSON decode error for chunk {chunk}: {e}")
            if attempts < 2:
                chunk_number -= 1  # Retry the same chunk
        chunk_number += 1
    
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
