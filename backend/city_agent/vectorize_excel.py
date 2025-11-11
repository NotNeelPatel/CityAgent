import os, json, re, pandas as pd, asyncio
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types  # Content, Part
from dotenv import load_dotenv # amilesh needs this to load his env, TODO: figure out why
load_dotenv()
_INSTRUCTIONS = """
You classify tabular columns into two disjoint sets for a content page.

Goal
Return ONLY a minified JSON object with the exact shape:
{"page_content":[...],"metadata":[...]}

Inputs
- headers: list of column names
- sample_rows: a small list of row objects to infer column semantics

Definitions
- page_content: columns whose values belong in the visible body of a page. Rich descriptive fields, long text, summaries, titles, body content, captions, bullet-like text, human-readable descriptions.
- metadata: columns that annotate or organize content. IDs, slugs, URLs, file paths, timestamps, dates, language codes, authors, status, categories/tags, booleans, numeric codes, version, size, checksum, geocoords, counts, flags.

Rules
1) Consider ONLY headers written in English. Ignore any non-English or mixed-language headers. Do not include them in either list.
2) Never invent headers. Choose only from the provided headers.
3) No overlap. A header can appear in exactly one of page_content or metadata.
4) Heuristics from sample_rows:
   - Long free-form text, sentences or paragraphs → page_content.
   - Titles, headlines, subheadings → page_content.
   - IDs, GUIDs, numeric keys, booleans, enums, short codes, emails, phone numbers → metadata.
   - URLs, slugs, file names, file types, image paths → metadata.
   - Dates, times, timestamps, timezone, created_at, updated_at, published_on → metadata.
   - Author, editor, owner, source, license → metadata.
   - Category, tag, topic, language, locale → metadata.
   - If unsure, prefer metadata for clearly structural or administrative fields.
5) Keep original header text as-is.
6) If a bucket would be empty, return an empty array. Do not force anything.
7) Output must be exactly valid JSON with keys "page_content" and "metadata" and nothing else. No extra text.

Few-shot examples

Example A
headers: ["Title","Body","Slug","Created At","Author","Language","Word Count"]
Decision:
{"page_content":["Title","Body"],"metadata":["Slug","Created At","Author","Language","Word Count"]}

Example B
headers: ["Name","Description","Category","Image URL","SKU","In Stock","Price"]
Decision:
{"page_content":["Name","Description"],"metadata":["Category","Image URL","SKU","In Stock","Price"]}

Example C
headers: ["Resumo","Título","Link","Data","Notes"]   // only English headers count
Decision:
{"page_content":["Notes"],"metadata":["Link","Data"]}

Respond with JSON only.
"""

def _is_english_header(h: str) -> bool:
    return isinstance(h, str) and bool(re.search(r"[A-Za-z]", h)) and not re.search(r"[^\x00-\x7F]", h)

def _ensure_session_sync(session_service, app_name, user_id, session_id):
    async def _create():
        # If your ADK exposes get_session, you can try it here and skip create if it exists.
        await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop -> safe to run
        asyncio.run(_create())
    else:
        # There is a running loop -> schedule it (use this branch if you embed in an async app)
        asyncio.create_task(_create())

def ai_excel_helper(headers, rows):
    USE_AZURE = False

    if (USE_AZURE):
      AZURE_API_KEY = os.getenv("AZURE_API_KEY")
      AZURE_API_BASE= os.getenv("AZURE_API_BASE")
      AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")
      ai_api=LiteLlm(model="azure/gpt-oss-120b")
    else:
      os.environ["OLLAMA_API_BASE"] = os.getenv("OLLAMA_API_BASE")
      ai_api=LiteLlm(model="ollama_chat/gpt-oss:20b")

    agent = LlmAgent(
        name="Excel_helper",
        model=ai_api,
        description="Classifies headers into page_content vs metadata",
        instruction=_INSTRUCTIONS
    )

    # Session + runner
    app_name = "excel_classifier"
    user_id = "local_user"
    session_id = "excel_session"

    session_service = InMemorySessionService()
    session = session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    # _ensure_session_sync(session_service, app_name, user_id, session_id)  # <-- IMPORTANT

    # runner = Runner(agent=agent, app_name=app_name, session_service=session_service)

    # Build user message
    payload = {"headers": headers, "sample_rows": rows, "format": {"page_content": [], "metadata": []}}
    message = json.dumps(payload, ensure_ascii=False)
    content = types.Content(role="user", parts=[types.Part(text=message)])

    # Run and return final text only (no JSON parsing)
    final_text = None
    events = runner.run(user_id=user_id, session_id=session_id, new_message=content)
    for event in events:
        # print("DEBUG EVENT:", event)
        if event.is_final_response() and event.content and event.content.parts:
            part = event.content.parts[0]
            if getattr(part, "text", None):
                final_text = part.text.strip()

    return final_text

def vectorize_excel(filepath: str):
    df = pd.read_csv(filepath, encoding="cp1252")
    headers = [h for h in df.columns.tolist() if _is_english_header(h)]
    sample_rows = df.head(5).to_dict(orient="records")
    return ai_excel_helper(headers, sample_rows)
  
if __name__ == "__main__":
    resp = asyncio.run(vectorize_excel("./data/4_Rates_fees_and_charges.csv"))
    print(resp)