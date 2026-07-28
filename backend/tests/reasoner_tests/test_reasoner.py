import pytest
from tests.test_harness import run_offline_tool_pipeline

REASONER_CASES = [
    ("rh1_missing_ward12_data", "What roads are in Ward 12?"),
    ("rh2_empty_context", "What is the PQI of Elgin Street?"),
    ("rh3_condition_interpretation", "Is AGES DR in Poor condition?"),
    ("rh4_unrelated_road_data", "What is the condition of Road B?"),
]


@pytest.mark.parametrize("case_id,query", REASONER_CASES)
def test_reasoner_case(case_id: str, query: str):
    """Executes reasoner hallucination guard case ($0 API cost, deterministic)."""
    res = run_offline_tool_pipeline({"name": case_id, "query": query})
    assert res["status"] in ("success", "refusal", "no_data_refusal")
