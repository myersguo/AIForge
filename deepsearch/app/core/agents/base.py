from langgraph.types import Command

from app.core.types import State


class BaseAgent:
    async def process(self, state: State) -> Command:
        raise NotImplementedError

    async def process_stream(self, state: State) -> Command:
        """
        Process the state with streaming support.
        By default, it calls the regular process method.
        Override this method in subclasses to implement custom streaming behavior.
        """
        return await self.process(state)
