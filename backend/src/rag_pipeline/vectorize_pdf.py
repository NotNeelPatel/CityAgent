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
The main task is to vectorize the provided asset management document into a SINGLE valid JSON object. This object must contain an array of "Knowledge Objects" that preserve the semantic meaning of the report sections for a vector database.

STRICT OUTPUT RULES:
    NO PROSE: No introduction, no summary, and no "Here is your JSON."
    VALIDITY: The response must be one single, valid, minified JSON object.
    ARRAY WRAPPING: Every individual section must be an object inside a single parent array called "knowledge_objects".
    NO DUPLICATE KEYS: Ensure the JSON does not contain duplicate root keys.
    ESCAPING: You must escape all double quotes within the content_body (e.g., use \") and ensure no trailing commas remain at the end of the array.
    ENGLISH ONLY: Extract only English content. Ignore all French translations.
    TABLE HANDLING: Convert all tables into Markdown format inside the content_body.
JSON SCHEMA:
{
  "knowledge_objects": [
    {
      "metadata": {
        "source_file": "string",
        "service_area": "string",
        "topic": "string",
        "data_type": "string"
      },
      "page_content": {
        "context_header": "string",
        "content_body": "string (Markdown for tables)",
        "key_metrics": ["string", "string"]
      }
    }
  ]
}
SPECIFIC DATA HANDLING:
    Service Area: Use specific names like "Transportation," "Wastewater," or "Citywide."
    Data Type: Use categories like "Financial Analysis," "Condition Report," or "Policy Change."
    Key Metrics: Extract all numerical figures, percentages, and date ranges (e.g., "$10.8 billion," "15% poor condition").
Please process the provided text into this single minified JSON object now.
"""

APP_NAME = "Vectorize_PDF_App"
USER_ID = "2468"
SESSION_ID = "session2468"

ai_api = get_agent_model()

agent = LlmAgent(
    model=ai_api,
    name="PDF_Vectorization_Agent",
    instruction=_INSTRUCTIONS,
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
        json.JSONDecodeError: If the concatenated agent response is not valid JSON.
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
    doc_length = len(query)
    num_chunks = doc_length // chunk_size + 1
    raw_responses = []
    for i in range(num_chunks):
        raw_responses.append(await call_agent(runner, agent, SESSION_ID, query[chunk_size * i : min(doc_length, chunk_size * (i+1))])) 
    
    # Assemble JSON response
    response_header = f'{{"{filepath}":['
    responses = ",".join(raw_responses)
    response_footer = "]}"

    agent_response = response_header + responses + response_footer
    print(agent_response)
    parsed_root = json.loads(agent_response)

    # Expect parsed_root to contain a top-level "data" entry; fall back to the root.
    parsed_data = parsed_root.get(f"{filepath}_data", parsed_root)

    # Normalize parsed_data to a list of knowledge objects
    if isinstance(parsed_data, dict):
        # If the dict uses numeric-string keys (e.g. pages), convert to a list ordered by key
        if all(isinstance(k, str) and k.isdigit() for k in parsed_data.keys()):
            items = [v for _, v in sorted(parsed_data.items(), key=lambda x: int(x[0]))]
        else:
            items = [parsed_data]
    elif isinstance(parsed_data, list):
        items = parsed_data
    else:
        items = [parsed_data]

    documents = []
    ids = []
    # Unwrap a top-level "knowledge_objects" container if present
    if len(items) == 1 and isinstance(items[0], dict) and "knowledge_objects" in items[0]:
        ko = items[0]["knowledge_objects"]
        items = ko if isinstance(ko, list) else [ko]

    documents = []
    ids = []

    for item in items:
        # Pull content: prefer structured content_body when available
        page_content_obj = item.get("page_content") if isinstance(item, dict) else None

        if isinstance(page_content_obj, dict):
            content = page_content_obj.get("content_body") or json.dumps(page_content_obj, ensure_ascii=False)
        elif page_content_obj is not None:
            content = str(page_content_obj)
        else:
            # Fallback to the whole item as text
            content = json.dumps(item, ensure_ascii=False)

        # Merge metadata and add file info
        meta = {}
        if isinstance(item, dict) and isinstance(item.get("metadata"), dict):
            meta.update(item.get("metadata"))
        meta["source_file"] = os.path.basename(filepath)
        meta["last_updated"] = str(ctime(os.path.getmtime(filepath)))

        _id = str(uuid.uuid4())
        # Store the id in metadata instead of passing an unsupported 'id' kwarg to Document
        meta["document_id"] = _id
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
