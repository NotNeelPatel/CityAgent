# 1. Vector Store Setup (Chroma + LangChain)

This step loads your backend/data/ folder, vectorizes all CSV/XLSX files, and writes them into a persistent ChromaDB directory (backend/chroma_langchain_db).

Run once to build or refresh the vector DB:

From the project root:

```bash
cd backend/src
python -m rag_pipeline.vector
```

# 2. Running CityAgent with ADK Web

ADK Web provides a built-in UI to test your agents without writing a frontend.

Run ADK Web:

```bash
cd backend/src
adk web --port 8000
```

# 3. Running the FastAPI Server (Backend API)

This starts the FastAPI server so you can hit the ADK endpoints (create sessions, send messages, etc.) through HTTP.

From the project root:

```bash
cd backend
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

You should see Uvicorn running on port 8000.

## 3.1 Requests and Responses

### Step 1: Create a session (POST)

#### Postman

- Method: POST
- URL: `http://localhost:8000/adk/apps/city_agent/users/dev/sessions/test`
- Body: none

#### Curl

```bash
curl -X POST "http://localhost:8000/adk/apps/city_agent/users/dev/sessions/test"
```

If successful, you should get a 200 range response.

### Step 2: Send a message to the agent (POST)

#### Postman

- Method: POST
- URL: `http://localhost:8000/adk/run`
- Headers: `Content-Type: application/json`
- Body (raw JSON):

```JSON
{
  "appName": "city_agent",
  "user_id": "dev",
  "session_id": "test",
  "new_message": {
    "parts": [
      {
        "text": "What is the condition of percy road starting from queensway?"
      }
    ],
    "role": "user"
  }
}
```

#### Curl

```bash
curl -X POST "http://localhost:8000/adk/run" \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "city_agent",
    "user_id": "dev",
    "session_id": "test",
    "new_message": {
      "parts": [
        { "text": "What is the condition of percy road starting from queensway?" }
      ],
      "role": "user"
    }
  }'
```

Expected: the response should mention that the condition is poor (assuming your data includes that road segment).
