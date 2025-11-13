from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from ai_api_selector import get_agent_model
from google.adk.sessions import InMemorySessionService
import os, json, re, pandas as pd, asyncio

_INSTRUCTIONS = """
Task: Classify tabular column names into two disjoint sets: 'page_content' and 'metadata'.

Output Format:
Return only a valid minified JSON object:
{"page_content":[...],"metadata":[...]}

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
headers: ["Title","Body","Slug","Created At","Author","Language","Word Count","ColSearch"]->
{"page_content":["Title","Body","ColSearch"],"metadata":["Slug","Created At","Author","Language","Word Count"]}

Example B
headers: ["Name","Description","Category","Image URL","SKU","In Stock","Price"]->
{"page_content":["Name","Description"],"metadata":["Category","Image URL","SKU","In Stock","Price"]}

Example C
headers: ["Résumé","Titre","Lien","Date","Notes"]->
{"page_content":["Notes"],"metadata":["Lien","Date"]}
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
            

async def vectorize_excel(filepath: str):
    print("--- Creating Sessions ---")
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    
    if(filepath.endswith('.csv')):
        df = pd.read_csv(filepath, encoding="cp1252")
    elif(filepath.endswith('.xlsx')):
        df = pd.read_excel(filepath)
    headers = [h for h in df.columns.tolist() if _is_english_header(h)]
    sample_rows = df.head(5).to_dict(orient="records")
    
    query = "{headers:" + str(headers) + " sample_rows: " + str(sample_rows) + "}"
    
    await call_agent(runner, agent, SESSION_ID, query)
    

if __name__ == "__main__":
    asyncio.run( vectorize_excel("<path to data>") )
