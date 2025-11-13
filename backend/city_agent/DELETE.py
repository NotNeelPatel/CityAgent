from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from ai_api_selector import get_agent_model
from google.adk.sessions import InMemorySessionService
import os, json, re, pandas as pd, asyncio

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

APP_NAME = "Vectorize_Excel_App"
USER_ID = "1234"
SESSION_ID = "session1234"


def _is_english_header(h: str) -> bool:
    return isinstance(h, str) and bool(re.search(r"[A-Za-z]", h)) and not re.search(r"[^\x00-\x7F]", h)

ai_api = get_agent_model()

# Step 3: Wrap the planner in an LlmAgent
agent = LlmAgent(
    model=ai_api,  # Set your model name
    name= APP_NAME,
    instruction=_INSTRUCTIONS,
)

# Session and Runner
session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)


session = session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)


# Agent Interaction
async def call_agent(
    runner_instance: Runner,
    agent_instance: LlmAgent,
    session_id: str,
    query: str):
    
    """Sends a query to the specified agent/runner and prints results."""
    print(f"\n>>> Calling Agent: '{agent_instance.name}' | Query: {query}")

    content = types.Content(role='user', parts=[types.Part(text=query)])
    
    final_response_content = "No final response received."
    async for event in runner_instance.run_async(user_id=USER_ID, session_id=session_id, new_message=content):
        # print(f"Event: {event.type}, Author: {event.author}") # Uncomment for detailed logging
        if event.is_final_response() and event.content and event.content.parts:
            # For output_schema, the content is the JSON string itself
            final_response_content = event.content.parts[0].text
            
    print(f"<<< Agent '{agent_instance.name}' Response: {final_response_content}")
    
    print("\n\n\n RESPONSE FROM THE AGENT -------------------------- \n"+ final_response_content)

    # current_session = await session_service.get_session(app_name=APP_NAME,
    #                                               user_id=USER_ID,
    #                                               session_id=session_id)
    # stored_output = current_session.state.get(agent_instance.output_key)

    # # Pretty print if the stored output looks like JSON (likely from output_schema)
    # print(f"--- Session State ['{agent_instance.output_key}']: ", end="")
    # print("\n\n\n HERE IS THE STORED OUTPUT -------------------------- \n")
    # try:
    #     # Attempt to parse and pretty print if it's JSON
    #     parsed_output = json.loads(stored_output)
    #     print(json.dumps(parsed_output, indent=2))
    # except (json.JSONDecodeError, TypeError):
    #      # Otherwise, print as string
    #     print(stored_output)
    # print("-" * 30)

            

async def vectorize_excel(filepath: str):
    print("--- Creating Sessions ---")
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    
    df = pd.read_csv(filepath, encoding="cp1252")
    headers = [h for h in df.columns.tolist() if _is_english_header(h)]
    sample_rows = df.head(5).to_dict(orient="records")
    
    query = "{headers:" + str(headers) + " sample_rows: " + str(sample_rows) + "}"
    
    await call_agent(runner, agent, SESSION_ID, query)
    

if __name__ == "__main__":
    asyncio.run( vectorize_excel(r"C:\Users\aashn\OneDrive\Documents\Aashna\2 UNIVERSITY\4th year\Capstone\CityAgent\backend\city_agent\data\4_Rates_fees_and_charges.csv"))
