import json
import os
from typing import Any, Optional, Tuple

import pymupdf4llm

# PyMuPDF is sometimes referred to as fitz so add a compatibility import
try:
	import pymupdf as fitz
except Exception:
	import fitz

from src.supabase_interface import download_supabase_file
from city_agent.error_codes import ErrorCode


_PDF_CACHE: dict[str, dict[str, Any]] = {}
_PDF_CACHE_MAX_ENTRIES = 4


def _get_cached_pdf_entry(filename: str) -> Optional[dict[str, Any]]:
	entry = _PDF_CACHE.get(filename)
	if not entry:
		return None
	local_path = entry.get("local_path")
	if not local_path or not os.path.exists(local_path):
		_PDF_CACHE.pop(filename, None)
		return None
	return entry


def _store_pdf_cache_entry(filename: str, local_path: str, parsed_pages: Any) -> None:
	_PDF_CACHE[filename] = {
		"local_path": local_path,
		"parsed_pages": parsed_pages,
	}
	# Keep cache bounded to prevent unbounded memory growth.
	while len(_PDF_CACHE) > _PDF_CACHE_MAX_ENTRIES:
		oldest_key = next(iter(_PDF_CACHE))
		_PDF_CACHE.pop(oldest_key, None)


def _normalize_for_json(value: Any) -> Any:
	"""Convert non-JSON-native values into JSON-safe primitives."""
	if isinstance(value, dict):
		return {str(k): _normalize_for_json(v) for k, v in value.items()}
	if isinstance(value, (list, tuple, set)):
		return [_normalize_for_json(v) for v in value]
	if hasattr(value, "item"):
		try:
			value = value.item()
		except Exception:
			pass
	return value


def _tool_success(tool_name: str, data: dict) -> str:
	payload = {
		"status": "success",
		"tool": tool_name,
		"data": _normalize_for_json(data),
		"error": None,
	}
	return json.dumps(payload, ensure_ascii=True)


def _tool_error(
	message: str,
	tool_name: str = "unknown",
	code: str = ErrorCode.TOOL_EXECUTION_ERROR.value,
) -> str:
	payload = {
		"status": "error",
		"tool": tool_name,
		"data": None,
		"error": {
			"code": code,
			"message": message,
		},
	}
	return json.dumps(_normalize_for_json(payload), ensure_ascii=True)


def _get_pdf(filename: str) -> Tuple[Optional[dict], Optional[str]]:
	"""Download and open a PDF with local parsers.

	Returns a dict that includes:
	  - path: local file path
	  - document: PyMuPDF document object for page-level parsing
	  - parsed_pages: pymupdf4llm page chunks for lightweight inspection
	"""
	if not filename.lower().endswith(".pdf"):
		return None, _tool_error(
			f"Unsupported file type for file '{filename}'. Only .pdf files are supported.",
			tool_name="pdf",
			code=ErrorCode.UNSUPPORTED_FILE_TYPE.value,
		)

	try:
		cached_entry = _get_cached_pdf_entry(filename)
		if cached_entry:
			local_path = cached_entry["local_path"]
			parsed_pages = cached_entry.get("parsed_pages")
		else:
			db_file_info = download_supabase_file(filename, "documents")
			local_path = db_file_info[0]

			if not local_path.lower().endswith(".pdf"):
				return None, _tool_error(
					f"Downloaded file '{filename}' is not a supported PDF type.",
					tool_name="pdf",
					code=ErrorCode.UNSUPPORTED_DOWNLOADED_TYPE.value,
				)

			parsed_pages = pymupdf4llm.to_markdown(local_path, page_chunks=True)
			_store_pdf_cache_entry(filename, local_path, parsed_pages)

		document = fitz.open(local_path)
		return {
			"path": local_path,
			"document": document,
			"parsed_pages": parsed_pages,
			"cache_key": filename,
		}, None
	except FileNotFoundError:
		return None, _tool_error(
			f"File not found: {filename}. Retry with an exact filename from search_data results.",
			tool_name="pdf",
			code=ErrorCode.FILE_NOT_FOUND.value,
		)
	except Exception as e:
		return None, _tool_error(
			f"Error reading file '{filename}': {str(e)}. Retry once; if it persists, try another file.",
			tool_name="pdf",
			code=ErrorCode.READ_FAILURE.value,
		)


def get_pdf_info_impl(filename: str) -> str:
	"""Return basic information about a PDF."""
	pdf_ctx, error = _get_pdf(filename)
	if error:
		return error

	document = pdf_ctx["document"]
	cache_key = pdf_ctx.get("cache_key")
	try:
		page_count = int(document.page_count)
		cached_entry = _PDF_CACHE.get(cache_key) if cache_key else None
		cached_counts = (
			cached_entry.get("table_counts_by_page") if cached_entry else None
		)
		if isinstance(cached_counts, dict):
			table_counts_by_page = dict(cached_counts)
			pages_with_tables = sorted(int(page) for page in table_counts_by_page.keys())
		else:
			pages_with_tables = []
			table_counts_by_page = {}
			for page_idx in range(page_count):
				page = document.load_page(page_idx)
				table_finder = page.find_tables()
				table_count = len(table_finder.tables) if table_finder else 0
				if table_count > 0:
					page_num = page_idx + 1
					pages_with_tables.append(page_num)
					table_counts_by_page[str(page_num)] = table_count
			if cached_entry is not None:
				cached_entry["table_counts_by_page"] = dict(table_counts_by_page)
	finally:
		document.close()

	return _tool_success(
		"get_pdf_info",
		{
			"filename": filename,
			"page_count": page_count,
			"pages_with_tables": pages_with_tables,
			"pages_with_tables_count": len(pages_with_tables),
			"table_counts_by_page": table_counts_by_page,
		},
	)


def _extract_table_rows(table_obj: Any) -> list[dict]:
	"""Normalize PyMuPDF table output into list[dict]."""
	extracted = table_obj.extract()
	if not extracted:
		return []

	headers = extracted[0]
	rows = extracted[1:]
	normalized_rows: list[dict] = []
	for row in rows:
		row_dict = {}
		for idx, header in enumerate(headers):
			key = str(header).strip() if header is not None and str(header).strip() else f"column_{idx + 1}"
			row_dict[key] = row[idx] if idx < len(row) else None
		normalized_rows.append(row_dict)
	return normalized_rows


def extract_pdf_tables_impl(filename: str, page_num: int) -> str:
	"""Extract tabular data from a specific 1-indexed PDF page."""
	pdf_ctx, error = _get_pdf(filename)
	if error:
		return error

	document = pdf_ctx["document"]
	try:
		page_count = int(document.page_count)
		if page_num < 1 or page_num > page_count:
			return _tool_error(
				f"Page '{page_num}' is out of range for file '{filename}'. Valid pages are 1 to {page_count}.",
				tool_name="extract_pdf_tables",
				code=ErrorCode.READ_FAILURE.value,
			)

		page = document.load_page(page_num - 1)
		table_finder = page.find_tables()
		tables = list(table_finder.tables) if table_finder else []

		if not tables:
			return _tool_error(
				f"No tables found in file '{filename}' on page {page_num}.",
				tool_name="extract_pdf_tables",
				code=ErrorCode.READ_FAILURE.value,
			)

		serialized_tables = []
		for idx, table in enumerate(tables, start=1):
			serialized_tables.append(
				{
					"table_index": idx,
					"page_num": page_num,
					"rows": _extract_table_rows(table),
				}
			)

		return _tool_success(
			"extract_pdf_tables",
			{
				"filename": filename,
				"page_num": page_num,
				"table_count": len(serialized_tables),
				"tables": serialized_tables,
			},
		)
	except Exception as e:
		return _tool_error(
			f"Error extracting tables from file '{filename}' page {page_num}: {str(e)}",
			tool_name="extract_pdf_tables",
			code=ErrorCode.READ_FAILURE.value,
		)
	finally:
		document.close()
