from city_agent.agent import root_agent


class _AgentContainer:
    root_agent = root_agent


agent = _AgentContainer()
