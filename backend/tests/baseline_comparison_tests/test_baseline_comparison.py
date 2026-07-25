import os
import pytest
from tests.test_harness import run_offline_tool_pipeline

BASELINE_COMPARISON_CASES = [
    ("bc1_fergus_lookup", "What is the exact PQI of FERGUS CR from COBBLE HILL DR (N) to COBBLE HILL DR (S)?"),
    ("bc2_ages_vs_wellington", "Is AGES DR generally in better or worse condition than WELLINGTON ST?"),
    ("bc3_ward3_assets", "Which road segments in sample_roads.csv are located in Ward 3?"),
    ("bc4_ward99_refusal", "Do you have data for Ward 99?"),
    ("bc5_best_arterial", "Which arterial road in the dataset has the highest PQI?"),
    ("bc6_mann_av_comparison", "Compare MANN AV eastbound vs westbound PQI."),
    ("bc7_replacement_cost", "What is the replacement cost for roads in Ward 3 rated Poor?"),
    ("bc8_lowest_pqi", "Which road in the dataset has the lowest PQI?"),
]


@pytest.mark.parametrize("case_id,query", BASELINE_COMPARISON_CASES)
def test_baseline_comparison_case(case_id: str, query: str):
    """Executes baseline comparison test case ($0 API cost, deterministic)."""
    res = run_offline_tool_pipeline({"name": case_id, "query": query})
    assert res["status"] in ("success", "refusal", "no_data_refusal")
    assert len(res["response"]) > 0


@pytest.mark.skipif(
    os.getenv("LIVE_LLM") != "1",
    reason="Live LLM tests skipped by default to prevent API costs. Set LIVE_LLM=1 to run.",
)
@pytest.mark.asyncio
async def test_baseline_comparison_live():
    """Executes live ADK agent evaluation for baseline comparison cases against live LLM API."""
    from tests.test_harness import evaluate_adk_live_suite
    await evaluate_adk_live_suite("tests/baseline_comparison_tests/baseline_comparison_evalset.json")
