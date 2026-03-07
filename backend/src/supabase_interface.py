import os
import tempfile
from pathlib import Path
from supabase import create_client, Client

_supabase_client = None

SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".csv"}

def _require_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")
    return value

def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    supabase_url = _require_env("SUPABASE_URL")
    supabase_key = _require_env("SUPABASE_SERVICE_ROLE_KEY")
    _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client

def download_supabase_file(storage_location: str, bucket: str | None):
    file_path = file_path = storage_location.strip().lstrip("/")
    extension = Path(file_path).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{extension}'. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    file_bytes = get_supabase_client().storage.from_(bucket).download(file_path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp_file:
        tmp_file.write(file_bytes)
        temp_path = tmp_file.name

    return temp_path, bucket, file_path
