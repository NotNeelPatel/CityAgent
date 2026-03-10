from pathlib import Path
from unittest.mock import patch

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


@pytest.mark.asyncio
async def test_data_analyst_logic():
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
        await AgentEvaluator.evaluate(
            agent_module="city_agent.eval_agents.data_analyst_eval_agent",
            eval_dataset_file_path_or_dir="tests/data_analyst_tests/data_analyst_evalset.json",
            num_runs=1,
            print_detailed_results=True,
        )
