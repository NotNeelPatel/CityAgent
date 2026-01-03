import os
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

# Directory that contains agent packages (src)
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
SERVE_WEB_INTERFACE = False  # Set to false to keep backend API-only

ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

adk_app: FastAPI = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    # session_service_uri= <>,  # sessions are stored in memory for now, and not persisted
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

app = FastAPI(title="CityAgent API")

app.mount("/adk", adk_app)


@app.get("/health")
async def health():
    return {"status": "ok"}


# add more custom endpoints below if needed
