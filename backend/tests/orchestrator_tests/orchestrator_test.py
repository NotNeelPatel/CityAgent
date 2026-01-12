import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


@pytest.mark.asyncio
async def test_orchestrator_logic():
    await AgentEvaluator.evaluate(
        agent_name="CityAgent_Orchestrator",
        agent_module="city_agent.agent",
        eval_dataset_file_path_or_dir="tests/orchestrator_tests/orches_evalset.json",
        num_runs=1,
        print_detailed_results=True
    )



