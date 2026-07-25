import os
from pathlib import Path
from unittest.mock import patch

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


def _is_transient_eval_failure(exc: Exception) -> bool:
    message = str(exc)
    return (
        "RateLimitError" in message
        or "Rate limit" in message
        or ("NoneType" in message and "len()" in message)
    )


@pytest.mark.skipif(
    os.getenv("LIVE_LLM") != "1",
    reason="Live LLM tests skipped by default to prevent API costs. Set LIVE_LLM=1 to run.",
)
@pytest.mark.asyncio
async def test_root_agent_flow():
    fixture_csv = (
        Path(__file__).resolve().parent.parent
        / "vectorize_tests"
        / "fixtures"
        / "sample_roads.csv"
    )

    def _mock_download_supabase_file(storage_location: str, bucket: str | None):
        return str(fixture_csv), bucket or "documents", storage_location

    with patch(
        "city_agent.agent_tools.spreadsheet_analysis_tools.download_supabase_file",
        side_effect=_mock_download_supabase_file,
    ):
        try:
            await AgentEvaluator.evaluate(
                agent_module="city_agent.eval_agents.root_eval_agent",
                eval_dataset_file_path_or_dir="tests/root_tests/root_evalset.json",
                num_runs=1,
                print_detailed_results=True,
            )
        except Exception as exc:
            if _is_transient_eval_failure(exc):
                pytest.skip(
                    "Transient external eval failure (rate limit / ADK null inference)."
                )
            raise
