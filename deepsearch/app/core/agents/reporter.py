import os

import jinja2
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from app.core.agents.base import BaseAgent
from app.core.llm import get_llm
from app.core.types import State


class ReporterAgent(BaseAgent):
    def __init__(self):
        self.llm = get_llm()

        # Load prompt template
        template_path = os.path.join(
            os.path.dirname(__file__), "../prompts/reporter.md"
        )
        with open(template_path, "r") as f:
            template_content = f.read()

        self.prompt_template = jinja2.Template(template_content)

    async def process(self, state: State) -> Command:
        query = state.get("query")
        locale = state.get("locale", "en")
        search_result = state.get("search_result")
        prompt_content = self.prompt_template.render(
            query=query, search_results=search_result, locale=locale, CURRENT_TIME=state.get("current_time")
        )

        agent = create_react_agent(
            model=self.llm,
            prompt=prompt_content,
            tools=[],
        )
        messages = [SystemMessage(content=prompt_content)]

        report = await agent.ainvoke({"input": messages[0].content})
        ai_content = report.get("messages", [])[-1].content

        return Command(goto="END", update={"reporter_result": ai_content, "locale": locale})
