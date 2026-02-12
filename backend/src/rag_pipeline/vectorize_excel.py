import os
from time import ctime
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from google.adk.sessions import InMemorySessionService
from langchain_core.documents import Document
import json, re, pandas as pd, asyncio
import uuid
from ai_api_selector import get_agent_model

# from ai_api_selector import get_agent_model

_INSTRUCTIONS = """
Task: Classify tabular column names into two disjoint sets: 'page_content' and 'metadata'.

Output Format:
Return only a valid minified JSON object:
{"page_content":{#:"header", ...},"metadata":{#:"header", ...}}

Inputs:
headers: list of column names
sample_row: list of small row objects for context

Definitions

page_content: Columns containing visible or descriptive text that belongs in a page's body (titles, summaries, paragraphs, captions, human-readable descriptions, bullet-like text).
metadata: Columns describing or organizing content (IDs, slugs, URLs, timestamps, authors, categories, tags, booleans, numeric codes, languages, statuses, counts, etc.).

Rules

1. Only include English headers. Ignore non-English or mixed-language ones entirely.
2. Use only the provided headers; never invent new ones.
3. Each header belongs to exactly one set (no overlap).
4. Infer meaning from 'sample_rows':

   * Long free text → 'page_content'
   * Titles, headlines → 'page_content'
   * IDs, GUIDs, numeric keys, booleans, enums, short codes, emails, phones → 'metadata'
   * URLs, slugs, filenames, file paths, image links → 'metadata'
   * Dates, times, timestamps → 'metadata'
   * Author, editor, owner, source, license → 'metadata'
   * Category, tag, topic, language, locale → 'metadata'
   * If uncertain, prefer 'metadata' for structural or administrative fields.
5. Keep header text exactly as given.
6. If a list would be empty, return an empty array.
7. Output only valid JSON. No text, comments, or formatting beyond that.
8. Use double quotes for all strings and property names (JSON standard).
9. Use string keys for indices. Example: "0" not 0.

Examples

Example A:
headers: {0:"Title", 1:"Body", 2:"Slug",3:"Created At",4:"Author",5:"Language",6:"Word Count",7:"ColSearch"}->
{"page_content":{0:"Title",1:"Body",7:"ColSearch"],"metadata":[2:"Slug",3:"Created At",4:"Author",5:"Language",6:"Word Count"}}

Example B
headers: {0:"Name",1:"Description",2:"Category",3:"Image URL",4:"SKU",5:"In Stock",6:"Price"}->
{"page_content":{0:"Name",1:"Description"],"metadata":[2:"Category",3:"Image URL",4:"SKU",5:"In Stock",6:"Price"}}

Example C
headers: {0:"Résumé",1:"Titre",2:"Lien",3:"Date",4:"Notes"}->
{"page_content":{4:"Notes"],"metadata":[2:"Lien",3:"Date"}}
"""

APP_NAME = "Vectorize_Excel_App"
USER_ID = "1234"
SESSION_ID = "session1234"

async def _vectorize(df: pd.DataFrame, filepath: str):
    """
    Vectorize a DataFrame by classifying columns and creating Document objects.
    This function processes a pandas DataFrame by:
    1. Loading the file into a pandas DataFrame (CSV or XLSX).
    2. Filtering headers to English-only with `_is_english_header`.
    3. Sending `indexed_headers` and a small set of `sample_rows` to the
    4. Parsing the agent response and building one `Document` per row using
    Args:
        df (pd.DataFrame): The pandas DataFrame to vectorize.
        filepath (str): The file path of the source file, used for metadata.
    Returns:
        tuple: A tuple containing:
            - documents (list[Document]): List of Document objects with page_content and metadata.
            - ids (list[str]): List of corresponding document IDs as UUID strings.
    """

    documents = []
    ids = []

    raw_headers = [h for h in df.columns.tolist() if _is_english_header(h)]
    indexed_headers = dict(enumerate(raw_headers))
    sample_rows = df.head(5).to_dict(orient="records")

    query = (
        "{headers:" + str(indexed_headers) + " sample_rows: " + str(sample_rows) + "}"
    )
    agent_response = await call_agent(runner, agent, SESSION_ID, query)

    parsed = json.loads(agent_response)
    parsed["page_content"] = {int(k): v for k, v in parsed["page_content"].items()}
    parsed["metadata"] = {int(k): v for k, v in parsed["metadata"].items()}

    for i, row in df.iterrows():
        page_content_values = []
        for k, col_name in parsed["page_content"].items():
            if col_name in row and pd.notna(row[col_name]):
                page_content_values.append(str(row[col_name]))

        str_page_content = " ".join(page_content_values)
        if not str_page_content.strip():
            continue

        metadata = {}

        for k, col_name in parsed["metadata"].items():
            if col_name in row and pd.notna(row[col_name]):
                metadata[col_name] = str(row[col_name])

        metadata["filename"] = os.path.basename(filepath)
        metadata["last_updated"] = str(ctime(os.path.getmtime(filepath))) 

        id = str(uuid.uuid4())
        doc = Document(page_content=str_page_content, metadata=metadata, id=id)
        ids.append(id)
        documents.append(doc)
    return documents, ids


def _is_english_header(h: str) -> bool:
    """Return True if header string appears to be English ASCII text.

    The heuristic checks that the header is a string, contains at least
    one ASCII letter, and contains no non-ASCII characters. This is a
    lightweight filter to skip non-English or binary-looking column
    names before sending headers to the agent.

    Args:
        h (str): Header value to inspect.

    Returns:
        bool: True if `h` looks like an English header, False otherwise.
    """

    return (
        isinstance(h, str)
        and bool(re.search(r"[A-Za-z]", h))
        and not re.search(r"[^\x00-\x7F]", h)
    )


ai_api = get_agent_model()

agent = LlmAgent(
    model=ai_api,
    name="Excel_Vectorization_Agent",
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


async def vectorize_excel(filepath: str):
    """Vectorize a spreadsheet or CSV into Document objects and ids.

     Args:
        filepath (str): Path to the CSV or XLSX file to vectorize.

    Returns:
        tuple[list[Document], list[str]]: A tuple containing the list of
            `Document` objects and a parallel list of their string ids.
    """

    session_service = await get_or_create_session(APP_NAME, USER_ID, SESSION_ID)

    sheets = []
    if filepath.endswith(".csv"):
        sheets.append(pd.read_csv(filepath, encoding="cp1252"))
    elif filepath.endswith(".xlsx"):
        excel_data = pd.ExcelFile(filepath)
        for sheet in excel_data.sheet_names:
            sheets.append(pd.read_excel(excel_data, sheet))
    
    documents = []
    ids = []

    for df in sheets:
        (documents, ids) = await _vectorize(df, filepath)

    return documents, ids


if __name__ == "__main__":
    asyncio.run(vectorize_excel(r"path-to-your-file"))

    # kill the session to free up memory since it's being stored in application memory currently
    # TODO: Maybe store in postgres to reuse sessions?
    session_service.delete_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
