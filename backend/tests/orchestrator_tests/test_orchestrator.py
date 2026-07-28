import pytest
from tests.test_harness import run_offline_tool_pipeline

ORCHESTRATOR_CASES = [
    ("oc1_intent_surface_quality", "Tell me about road surface quality on WELLINGTON."),
    ("oc2_intent_crumbling_roads", "I am worried about crumbling roads in Ward 3."),
    ("oc3_intent_urgent_repair", "Show me infrastructure that needs urgent repair."),
    ("oc4_scope_tax_rate", "What is my tax rate in Ottawa?"),
    ("oc5_scope_pothole_report", "How do I report a pothole?"),
]


@pytest.mark.parametrize("case_id,query", ORCHESTRATOR_CASES)
def test_orchestrator_case(case_id: str, query: str):
    """Executes orchestrator intent expansion & scoping case ($0 API cost, deterministic)."""
    res = run_offline_tool_pipeline({"name": case_id, "query": query})
    assert res["status"] in ("success", "refusal", "no_data_refusal")
