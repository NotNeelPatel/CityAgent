import os
import pytest
from tests.test_harness import run_offline_tool_pipeline

HALLUCINATION_CASES = [
    # HG-1: Known-Empty Entity Refusals (4 cases)
    ("hg1_ward99", "Do you have data for Ward 99?"),
    ("hg1_fake_street", "What is the PQI of Nonexistent Fake Street?"),
    ("hg1_year_1950", "What were road expenditures in 1950?"),
    ("hg1_year_1987", "What were road maintenance costs in 1987?"),

    # HG-2: Numeric Groundedness Spot Checks (4 cases)
    ("hg2_fergus_pqi", "What is the exact PQI of FERGUS CR from COBBLE HILL DR (N) to COBBLE HILL DR (S)?"),
    ("hg2_ages_pqi", "What is the exact PQI value for AGES DR?"),
    ("hg2_wellington_pqi", "What is the exact PQI value for WELLINGTON ST?"),
    ("hg2_mean_pqi", "What is the mean PQI across all roads in sample_roads.csv?"),

    # HG-3: Source Citation Integrity (3 cases)
    ("hg3_cite_fergus", "Provide source details for FERGUS CR."),
    ("hg3_cite_ages", "Provide source details for AGES DR."),
    ("hg3_cite_wellington", "Provide source details for WELLINGTON ST."),

    # HG-4: Aggregation Guardrails (3 cases)
    ("hg4_cost_1950", "What is the total expenditure for roads in 1950?"),
    ("hg4_cost_fake_ward", "What is the total replacement cost for Ward 99?"),
    ("hg4_cost_unknown_year", "Calculate total road repair budget for 1980."),
]


@pytest.mark.parametrize("case_id,query", HALLUCINATION_CASES)
def test_hallucination_case(case_id: str, query: str):
    """Executes hallucination guardrail test case ($0 API cost, deterministic)."""
    res = run_offline_tool_pipeline({"name": case_id, "query": query})
    
    if "ward 99" in query.lower() or "fake" in query.lower() or "1950" in query.lower() or "1987" in query.lower() or "1980" in query.lower():
        assert res["status"] in ("refusal", "no_data_refusal")
        assert "not find" in res["response"].lower() or "sorry" in res["response"].lower() or "records" in res["response"].lower()
    else:
        assert res["status"] == "success"
        assert len(res["response"]) > 0


@pytest.mark.skipif(
    os.getenv("LIVE_LLM") != "1",
    reason="Live LLM tests skipped by default to prevent API costs. Set LIVE_LLM=1 to run.",
)
@pytest.mark.asyncio
async def test_hallucination_live():
    """Executes live ADK agent evaluation for hallucination cases against live LLM API."""
    from tests.test_harness import evaluate_adk_live_suite
    await evaluate_adk_live_suite("tests/hallucination_tests/hallucination_evalset.json")
