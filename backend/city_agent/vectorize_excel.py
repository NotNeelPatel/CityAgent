from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from city_agent.ai_api_selector import get_agent_model
from google.adk.sessions import InMemorySessionService
from langchain_core.documents import Document
import json, re, pandas as pd, asyncio

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

Examples

Example A:
headers: {0:"Title", 1:"Body", 2:"Slug",3:"Created At",4:"Author",5:"Language",6:"Word Count",7:"ColSearch"}->
{"page_content":{0:"Title",1:"Body",7:"ColSearch"],"metadata":[2:"Slug",3:"Created At",4:"Author",5:"Language",6:"Word Count"}}

Example B
headers: {0:"Name",1:"Description",2:"Category",3:"Image URL",4:"SKU",5:"In Stock",6:"Price"}->
{"page_content":{0:"Name",1:"Description"],"metadata":[2:"Category",2:"Image URL",4:"SKU",5:"In Stock",6:"Price"}}

Example C
headers: {0:"Résumé",1:"Titre",2:"Lien",3:"Date",4:"Notes"}->
{"page_content":{4:"Notes"],"metadata":[2:"Lien",3:"Date"}}
"""

APP_NAME = "Vectorize_Excel_App"
USER_ID = "1234"
SESSION_ID = "session1234"


def _is_english_header(h: str) -> bool:
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

session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)


async def call_agent(
    runner_instance: Runner, agent_instance: LlmAgent, session_id: str, query: str
):

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
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )

    df = None
    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath, encoding="cp1252")
    elif filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath)

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

    documents = []
    ids = []

    for i, row in df.iterrows():
        page_content = {v: row.iloc[k] for k, v in parsed["page_content"].items()}
        metadata = {v: row.iloc[k] for k, v in parsed["metadata"].items()}

        str_page_content = " ".join(
            [str(v) for v in page_content.values() if pd.notna(v)]
        )

        doc = Document(page_content=str_page_content, metadata=metadata, id=str(i))
        ids.append(str(i))
        documents.append(doc)

    # print(str_page_content)
    # print(metadata)
    return documents, ids


if __name__ == "__main__":
    asyncio.run(vectorize_excel(r"path-to-your-file"))
