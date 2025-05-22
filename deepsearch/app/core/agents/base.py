from langgraph.types import Command

from app.core.types import State


class BaseAgent:
    async def process(self, state: State) -> Command:
        raise NotImplementedError
