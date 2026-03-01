import os
from fastapi import FastAPI
from fastapi import Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.cli.fast_api import get_fast_api_app
from src.rag_pipeline.vector import (
    vectorize_and_store_supabase_file,
    delete_vector_from_vector_store,
)

# Directory that contains agent packages (src)
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
SERVE_WEB_INTERFACE = False  # Set to false to keep backend API-only

ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
if cors_origins_env:
    ALLOWED_ORIGINS = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

adk_app: FastAPI = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    # session_service_uri= <>,  # sessions are stored in memory for now, and not persisted
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

app = FastAPI(title="CityAgent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/adk", adk_app)


@app.get("/health")
async def health():
    return {"status": "ok"}


class VectorizeRequest(BaseModel):
    storage_path: str
    bucket: str | None = None


@app.post("/api/vectorize-file")
async def vectorize_file(request: VectorizeRequest):
    try:
        return await vectorize_and_store_supabase_file(
            storage_location=request.storage_path, bucket=request.bucket
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/vectorize-file/delete-vectors")
async def delete_vectors_for_file(request: VectorizeRequest):
    try:
        return delete_vector_from_vector_store(
            storage_location=request.storage_path, bucket=request.bucket
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
