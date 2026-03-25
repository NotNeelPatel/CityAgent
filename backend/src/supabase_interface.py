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


def download_supabase_file(storage_location: str, bucket="documents"):
    file_path = storage_location.strip().lstrip("/")
    extension = Path(file_path).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{extension}'. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    client = get_supabase_client()

    file_bytes = client.storage.from_(bucket).download(file_path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp_file:
        tmp_file.write(file_bytes)
        temp_path = tmp_file.name

    response = (
        client.table("documents")
        .select("last_updated")
        .eq("storage_path", file_path)
        .eq("storage_bucket", bucket)
        .limit(1)
        .execute()
    )

    metadata = response.data[0] if response.data else None
    last_updated = metadata.get("last_updated") if metadata else None

    return temp_path, bucket, file_path, last_updated


def list_supabase_documents(bucket: str = "documents"):
    """Return all indexed documents for a bucket from the documents table."""
    client = get_supabase_client()
    response = (
        client.table("documents")
        .select("storage_path,storage_bucket,last_updated")
        .eq("storage_bucket", bucket)
        .order("storage_path")
        .execute()
    )

    documents = response.data or []
    documents_list = [
        {
            "filename": item.get("storage_path"),
            "last_updated": item.get("last_updated"),
        }
        for item in documents
        if item.get("storage_path")
    ]
    return documents_list 
