try:
    from hirelogic_agent.agents.hirelogic_agent import root_agent
except ModuleNotFoundError:  # pragma: no cover - local execution from hirelogic_agent/
    from .hirelogic_agent import root_agent

__all__ = ["root_agent"]
