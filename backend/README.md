## 1. Vector Store Setup (Chroma + LangChain)

This step loads your backend/data/ folder, vectorizes all CSV/XLSX files, and writes them into a persistent ChromaDB directory (backend/chroma_langchain_db).

Run once to build or refresh the vector DB:

From the project root:

```bash
cd backend/src
python -m rag_pipeline.vector
```

## 2. Running CityAgent with ADK Web

ADK Web provides a built-in UI to test your agents without writing a frontend.

Run ADK Web:

```bash
cd backend/src
adk web --port 8000
```
