from pathlib import Path
from unittest.mock import patch
import pytest

from city_agent.agent_tools.spreadsheet_analysis_tools import (
    get_spreadsheet_info_impl,
    get_mean_impl,
    get_min_in_column_impl,
    get_max_in_column_impl,
    get_sum_in_column_impl,
    get_sum_of_filtered_values_impl,
    filter_values_impl,
    filter_values_in_range_impl,
    get_unique_values_impl,
    count_values_impl,
)
from city_agent.error_codes import ErrorCode

FIXTURE_CSV = (
    Path(__file__).resolve().parent.parent
    / "vectorize_tests"
    / "fixtures"
    / "sample_roads.csv"
)


def _mock_download_supabase_file(storage_location: str, bucket: str | None = None):
    return str(FIXTURE_CSV), bucket or "documents", storage_location


@pytest.fixture(autouse=True)
def mock_supabase():
    with patch(
        "city_agent.agent_tools.spreadsheet_analysis_tools.download_supabase_file",
        side_effect=_mock_download_supabase_file,
    ):
        yield


class TestSpreadsheetToolsOffline:
    """Fast, deterministic unit tests for spreadsheet tools ($0 cost, offline)."""

    def test_get_spreadsheet_info(self):
        res = get_spreadsheet_info_impl("sample_roads.csv")
        assert '"status": "success"' in res
        assert "FERGUS CR" in res
        assert "PQI" in res

    def test_get_mean_pqi(self):
        res = get_mean_impl("sample_roads.csv", "PQI")
        assert '"status": "success"' in res
        # (85.2 + 42.1 + 78.5) / 3 = 68.6
        assert "68.6" in res

    def test_get_min_in_column(self):
        res = get_min_in_column_impl("sample_roads.csv", "PQI")
        assert '"status": "success"' in res
        assert "42.1" in res

    def test_get_max_in_column(self):
        res = get_max_in_column_impl("sample_roads.csv", "PQI")
        assert '"status": "success"' in res
        assert "85.2" in res

    def test_get_sum_in_column(self):
        res = get_sum_in_column_impl("sample_roads.csv", "PQI")
        assert '"status": "success"' in res
        # 85.2 + 42.1 + 78.5 = 205.8
        assert "205.8" in res

    def test_filter_values_by_keyword(self):
        res = filter_values_impl(
            "sample_roads.csv", ["Road Name"], "FERGUS"
        )
        assert '"status": "success"' in res
        assert "FERGUS CR" in res
        assert "AGES DR" not in res

    def test_filter_values_in_range(self):
        res = filter_values_in_range_impl(
            "sample_roads.csv", "PQI", 40.0, 80.0
        )
        assert '"status": "success"' in res
        assert "AGES DR" in res
        assert "WELLINGTON ST" in res
        assert "FERGUS CR" not in res  # 85.2 is out of range 40-80

    def test_get_unique_values(self):
        res = get_unique_values_impl("sample_roads.csv", "Ward")
        assert '"status": "success"' in res
        assert "3" in res or 3 in res

    def test_count_values(self):
        res = count_values_impl("sample_roads.csv", "Ward")
        assert '"status": "success"' in res

    def test_column_not_found_error(self):
        res = get_mean_impl("sample_roads.csv", "NonExistentColumn")
        assert '"status": "error"' in res
        assert ErrorCode.COLUMN_NOT_FOUND.value in res

    def test_unsupported_file_type(self):
        res = get_spreadsheet_info_impl("invalid_doc.docx")
        assert '"status": "error"' in res
        assert ErrorCode.UNSUPPORTED_FILE_TYPE.value in res
