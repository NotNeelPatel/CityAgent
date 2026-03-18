import os
import json
import re
import time
import gc
from pathlib import Path

from supabase import Client

from src.events_interface import make_event
from src.rag_pipeline.vectorize_excel import vectorize_excel
from src.rag_pipeline.vectorize_pdf import vectorize_pdf
from src.ai_api_selector import get_embedding_model
from src.supabase_interface import get_supabase_client, download_supabase_file

_embedding_model = None

EMBEDDING_MAX_RETRIES = max(1, int(os.getenv("EMBEDDING_MAX_RETRIES", "6")))
EMBEDDING_BASE_BACKOFF_SECONDS = float(os.getenv("EMBEDDING_BASE_BACKOFF_SECONDS", "5"))
SUPABASE_INSERT_MAX_RETRIES = max(1, int(os.getenv("SUPABASE_INSERT_MAX_RETRIES", "5")))
SUPABASE_INSERT_BASE_BACKOFF_SECONDS = float(
    os.getenv("SUPABASE_INSERT_BASE_BACKOFF_SECONDS", "2")
)


def _safe_remove_temp_file(path: str, retries: int = 20, delay_seconds: float = 0.25):
    for attempt in range(retries):
        try:
            os.remove(path)
            return True
        except PermissionError:
            # Windows can hold transient file handles briefly (Pandas/openpyxl/http stack).
            gc.collect()
            if attempt == retries - 1:
                print(
                    f"Warning: could not delete temporary file after {retries} attempts: {path}"
                )
                return False
            time.sleep(delay_seconds)


def get_embedding_model_cached():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = get_embedding_model()
    return _embedding_model


def query_retriever(query: str):
    """Run a semantic retrieval query using Supabase RPC."""
    client = get_supabase_client()
    rpc_name = os.getenv("SUPABASE_MATCH_RPC", "match_documents")
    match_count = int(os.getenv("SUPABASE_MATCH_COUNT", "4"))
    query_mode = os.getenv("SUPABASE_MATCH_MODE", "text").strip().lower()

    if query_mode == "text":
        payload = {"query_text": query, "match_count": match_count}
    else:
        query_embedding = get_embedding_model_cached().embed_query(query)
        payload = {"query_embedding": query_embedding, "match_count": match_count}

    response = client.rpc(rpc_name, payload).execute()
    return json.dumps(response.data or [])


def _extract_retry_after_seconds(error_text: str):
    match = re.search(r"retry after (\d+)\s*seconds", error_text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _embed_documents_with_retry(texts: list[str]):
    attempt = 0
    while True:
        attempt += 1
        try:
            return get_embedding_model_cached().embed_documents(texts)
        except Exception as exc:
            error_name = exc.__class__.__name__
            error_text = str(exc)
            is_rate_limited = (
                error_name == "RateLimitError"
                or "429" in error_text
                or "RateLimit" in error_text
            )
            if not is_rate_limited or attempt >= EMBEDDING_MAX_RETRIES:
                raise

            retry_after = _extract_retry_after_seconds(error_text)
            backoff = (
                retry_after
                if retry_after is not None
                else EMBEDDING_BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            )
            print(
                f"Embedding rate-limited. Retrying in {backoff:.1f}s "
                f"(attempt {attempt}/{EMBEDDING_MAX_RETRIES})."
            )
            time.sleep(backoff)


def add_documents_to_vector_store(documents, ids):
    """Insert chunked documents into Supabase and yield progress events."""
    if not documents:
        return

    table_name = os.getenv("SUPABASE_VECTOR_TABLE", "documents")
    content_col = os.getenv("SUPABASE_CONTENT_COLUMN", "content")
    metadata_col = os.getenv("SUPABASE_METADATA_COLUMN", "metadata")
    id_col = os.getenv("SUPABASE_ID_COLUMN", "id")
    source_last_updated_col = os.getenv(
        "SUPABASE_SOURCE_LAST_UPDATED_COLUMN", "source_last_updated"
    )
    source_filename_col = os.getenv(
        "SUPABASE_SOURCE_FILENAME_COLUMN", "source_filename"
    )
    source_bucket_col = os.getenv("SUPABASE_SOURCE_BUCKET_COLUMN", "source_bucket")
    embedding_col = os.getenv("SUPABASE_EMBEDDING_COLUMN", "embedding")
    write_embeddings = os.getenv(
        "SUPABASE_WRITE_EMBEDDINGS", "true"
    ).strip().lower() in ("1", "true", "yes", "on")
    insert_batch_size = int(os.getenv("SUPABASE_INSERT_BATCH_SIZE", "50"))

    client = get_supabase_client()
    total_chunks = len(documents)
    completed = 0

    for i in range(0, total_chunks, insert_batch_size):
        chunk_docs = documents[i : i + insert_batch_size]
        chunk_ids = ids[i : i + insert_batch_size]
        chunk_texts = [doc.page_content for doc in chunk_docs]

        chunk_embeddings = (
            _embed_documents_with_retry(chunk_texts)
            if write_embeddings and embedding_col
            else None
        )

        payload = []
        for idx, (doc, _id) in enumerate(zip(chunk_docs, chunk_ids)):
            row = {
                content_col: doc.page_content,
                metadata_col: doc.metadata,
            }
            if id_col:
                row[id_col] = _id
            if source_filename_col:
                row[source_filename_col] = doc.metadata.get("source_filename")
            if source_last_updated_col:
                row[source_last_updated_col] = doc.metadata.get("source_last_updated")
            if source_bucket_col:
                row[source_bucket_col] = doc.metadata.get("source_bucket")
            if chunk_embeddings is not None:
                row[embedding_col] = chunk_embeddings[idx]
            payload.append(row)

        try:
            _insert_rows_with_retry(client, table_name, payload, i, len(chunk_docs))
            completed += len(chunk_docs)

            yield make_event(
                "loading",
                message=f"Embedding ({completed}/{total_chunks})",
                chunks_embedded=completed,
            )

        except Exception:
            # degrade to row-by-row and still report progress
            for row_idx, row in enumerate(payload):
                _insert_rows_with_retry(client, table_name, [row], i + row_idx, 1)
                completed += 1
                yield make_event(
                    "loading",
                    message=f"Embedding ({completed}/{total_chunks})",
                    chunks_embedded=completed,
                )


def delete_vector_from_vector_store(storage_location: str, bucket: str | None):
    """Delete vector rows associated with a storage object."""
    if not bucket:
        raise ValueError("bucket is required to delete associated vectors.")

    file_path = storage_location.strip().lstrip("/")
    if not file_path:
        raise ValueError("storage_path is required to delete associated vectors.")

    table_name = os.getenv("SUPABASE_VECTOR_TABLE", "documents")
    source_filename_col = os.getenv(
        "SUPABASE_SOURCE_FILENAME_COLUMN", "source_filename"
    )
    source_bucket_col = os.getenv("SUPABASE_SOURCE_BUCKET_COLUMN", "source_bucket")

    client = get_supabase_client()
    delete_query = client.table(table_name).delete().eq(source_filename_col, file_path)
    if source_bucket_col:
        delete_query = delete_query.eq(source_bucket_col, bucket)

    response = delete_query.execute()
    deleted_rows = len(response.data) if response.data else 0
    return {
        "status": "ok",
        "bucket": bucket,
        "file_path": file_path,
        "deleted_rows": deleted_rows,
    }


def _is_transient_insert_error(error_text: str) -> bool:
    lower = error_text.lower()
    return (
        "remoteprotocolerror" in lower
        or "server disconnected" in lower
        or "readerror" in lower
        or "bad record mac" in lower
        or "sslv3_alert_bad_record_mac" in lower
        or "timed out" in lower
        or "connection reset" in lower
        or "temporarily unavailable" in lower
    )


def _insert_rows_with_retry(
    client: Client, table_name: str, rows: list, start_idx: int, size: int
):
    for attempt in range(1, SUPABASE_INSERT_MAX_RETRIES + 1):
        try:
            client.table(table_name).insert(rows).execute()
            return
        except Exception as exc:
            error_text = str(exc)
            is_transient = _is_transient_insert_error(error_text)
            is_last_attempt = attempt == SUPABASE_INSERT_MAX_RETRIES

            if not is_transient or is_last_attempt:
                raise

            backoff = SUPABASE_INSERT_BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(
                f"Supabase insert transient failure for batch {start_idx}-{start_idx + size}. "
                f"Retrying in {backoff:.1f}s (attempt {attempt}/{SUPABASE_INSERT_MAX_RETRIES})."
            )
            time.sleep(backoff)


async def vectorize_and_store_supabase_file(
    storage_location: str, bucket: str | None = None
):
    """Download from Supabase Storage, vectorize, then upsert into pgvector."""
    temp_path, bucket_name, file_path, last_updated = download_supabase_file(
        storage_location, bucket
    )
    extension = Path(file_path).suffix.lower()

    try:
        yield make_event(
            "loading",
            message="Chunking",
            file_path=file_path,
        )

        if extension == ".pdf":
            documents, ids = await vectorize_pdf(temp_path)
        else:
            documents, ids = await vectorize_excel(temp_path)

        if not documents or not ids:
            raise RuntimeError(
                "Vectorization produced zero chunks. Verify source file content/columns."
            )

        total_chunks = len(ids)

        for doc in documents:
            doc.metadata["source_bucket"] = bucket_name
            doc.metadata["source_filename"] = file_path
            doc.metadata["source_last_updated"] = last_updated

        print(f"Vectorization complete for {file_path}. Total chunks: {total_chunks}")

        yield make_event(
            "loading",
            message="Embedding",
            file_path=file_path,
            chunks_embedded=0,
            total_chunks=total_chunks,
        )

        for event in add_documents_to_vector_store(documents, ids):
            yield make_event(
                event["type"],
                message=event.get("message"),
                file_path=file_path,
                chunks_embedded=event.get("chunks_embedded"),
                total_chunks=total_chunks,
            )

        yield make_event(
            "success",
            message="Fully vectorized",
            file_path=file_path,
            chunks_embedded=total_chunks,
            total_chunks=total_chunks,
        )

    finally:
        if os.path.exists(temp_path):
            _safe_remove_temp_file(temp_path)
