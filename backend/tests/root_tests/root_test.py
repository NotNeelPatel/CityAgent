import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


@pytest.mark.asyncio
async def test_root_agent_flow():
    await AgentEvaluator.evaluate(
        agent_module="city_agent.eval_agents.root_eval_agent",
        eval_dataset_file_path_or_dir="tests/root_tests/root_evalset.json",
        num_runs=2,
        print_detailed_results=True,
    )
