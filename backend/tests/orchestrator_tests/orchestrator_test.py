import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


def _is_transient_eval_failure(exc: Exception) -> bool:
    message = str(exc)
    return (
        "RateLimitError" in message
        or "Rate limit" in message
        or ("NoneType" in message and "len()" in message)
    )


@pytest.mark.asyncio
async def test_orchestrator_logic():
    try:
        await AgentEvaluator.evaluate(
            agent_module="city_agent.eval_agents.orchestrator_eval_agent",
            eval_dataset_file_path_or_dir="tests/orchestrator_tests/orches_evalset.json",
            num_runs=2,
            print_detailed_results=True,
        )
    except Exception as exc:
        if _is_transient_eval_failure(exc):
            pytest.skip(
                "Transient external eval failure (rate limit / ADK null inference)."
            )
        raise



