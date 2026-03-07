import os
from fastapi import FastAPI
from fastapi import Header, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel
from google.adk.cli.fast_api import get_fast_api_app
from src.rag_pipeline.vector import (
    get_supabase_client,
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
async def verify_auth(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        supabase_client = get_supabase_client()
        user_response = supabase_client.auth.get_user(token)
        if not user_response or not getattr(user_response, "user", None):
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@adk_app.middleware("http")
async def verify_auth_adk(request: Request, call_next):
    if request.url.path.startswith("/adk"):
        try:
            await verify_auth(request.headers.get("Authorization"))
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    response = await call_next(request)
    return response

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
    
AuthUser = Depends(verify_auth)

@app.post("/api/vectorize-file")
async def vectorize_file(request: VectorizeRequest, user=AuthUser):
    try:
        return await vectorize_and_store_supabase_file(
            storage_location=request.storage_path, bucket=request.bucket
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/vectorize-file/delete-vectors")
async def delete_vectors_for_file(request: VectorizeRequest, user=AuthUser):
    try:
        return delete_vector_from_vector_store(
            storage_location=request.storage_path, bucket=request.bucket
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
