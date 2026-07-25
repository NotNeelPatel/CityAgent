import os
import pytest
from tests.test_harness import run_offline_tool_pipeline, check_numeric_precision

NUMERIC_PRECISION_CASES = [
    # NP-1: Known-Value Aggregations (6 cases)
    ("np1_mean_pqi", "Using spreadsheet tools, calculate the mean PQI across roads in sample_roads.csv.", 68.6),
    ("np1_min_pqi", "Using spreadsheet tools on sample_roads.csv, find the minimum PQI in the PQI column.", 42.1),
    ("np1_max_pqi", "Using spreadsheet tools on sample_roads.csv, find the maximum PQI in the PQI column.", 85.2),
    ("np1_fergus_pqi", "What is the PQI of FERGUS CR?", 85.2),
    ("np1_ages_pqi", "What is the PQI of AGES DR?", 42.1),
    ("np1_wellington_pqi", "What is the PQI of WELLINGTON ST?", 78.5),

    # NP-2: Range Filtering & Regression (5 cases)
    ("np2_range_40_80_ages", "Filter roads with PQI between 40 and 80.", 42.1),
    ("np2_range_40_80_wellington", "Filter roads with PQI between 40 and 80.", 78.5),
    ("np2_ward_12_count", "Which road segments are in Ward 12?", 78.5),
    ("np2_ward_3_count_fergus", "Which road segments are in Ward 3?", 85.2),
    ("np2_ward_3_count_ages", "Which road segments are in Ward 3?", 42.1),

    # NP-3: Schema Protocol & Error Handling (4 cases)
    ("np3_schema_before_mean", "Inspect headers of sample_roads.csv using get_spreadsheet_info before get_mean.", 68.6),
    ("np3_schema_before_min", "Inspect headers before finding minimum PQI.", 42.1),
    ("np3_schema_before_max", "Inspect headers before finding maximum PQI.", 85.2),
    ("np3_schema_before_filter", "Inspect headers before filtering Ward 12.", 78.5),
]


@pytest.mark.parametrize("case_id,query,expected_num", NUMERIC_PRECISION_CASES)
def test_numeric_precision_case(case_id: str, query: str, expected_num: float):
    """Executes numeric precision evaluation case ($0 API cost, deterministic)."""
    res = run_offline_tool_pipeline({"name": case_id, "query": query})
    assert res["status"] == "success"
    assert check_numeric_precision(res["response"], expected_num), f"Expected numeric value {expected_num} in response '{res['response']}'"


@pytest.mark.skipif(
    os.getenv("LIVE_LLM") != "1",
    reason="Live LLM tests skipped by default to prevent API costs. Set LIVE_LLM=1 to run.",
)
@pytest.mark.asyncio
async def test_numeric_precision_live():
    """Executes live ADK agent evaluation for numeric precision cases against live LLM API."""
    from tests.test_harness import evaluate_adk_live_suite
    await evaluate_adk_live_suite("tests/numeric_precision_tests/numeric_precision_evalset.json", agent_module="city_agent.eval_agents.data_analyst_eval_agent")
