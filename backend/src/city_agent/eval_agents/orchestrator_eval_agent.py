from city_agent.agent import orchestrator_agent


class _AgentContainer:
    root_agent = orchestrator_agent


agent = _AgentContainer()
