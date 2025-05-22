from typing import Dict, Any
from datetime import datetime


import langchain
import uvicorn
from fastapi import FastAPI, HTTPException, Body
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from app.config.settings import settings
from app.core.agents.coordinator import CoordinatorAgent
from app.core.agents.reporter import ReporterAgent
from app.core.agents.researcher import ResearcherAgent
from app.core.types import State

langchain.debug = True

app = FastAPI(title=settings.PROJECT_NAME)

# Initialize agents
coordinator_agent = CoordinatorAgent()
researcher_agent = ResearcherAgent()
reporter_agent = ReporterAgent()


class QueryInput(BaseModel):
    query: str


from langchain_core.runnables import RunnableLambda


def route_coordinator(state: State):
    print(f"State: {state}")
    if not state.get("coordinator"):
        return "casual"
    if state.get('coordinator') == "requires_research":
        return "research"
    elif state.get('coordinator') == "casual_conversation":
        return "casual"
    return "casual"


def route_planner(state):
    if state.get("planner", {}).get("needs_search"):
        return "researcher_node"
    return END


route_coordinator_runnable = RunnableLambda(route_coordinator)
route_planner_runnable = RunnableLambda(route_planner)


# Create workflow graph
def build_graph():
    workflow = StateGraph(State)

    # Define nodes with more specific names
    workflow.add_node("coordinator_node", coordinator_agent.process)
    workflow.add_node("researcher_node", researcher_agent.process)
    workflow.add_node("reporter_node", reporter_agent.process)

    # Define edges with separate routing functions
    workflow.add_conditional_edges(
        "coordinator_node",
        route_coordinator_runnable,
        {
            "research": "researcher_node",
            "casual": END
        }
    )

    workflow.add_edge("researcher_node", "reporter_node")
    workflow.add_edge("reporter_node", END)

    # Set entrypoint
    workflow.set_entry_point("coordinator_node")

    return workflow.compile()


graph = build_graph()


@app.post("/api/query", response_model=Dict[str, Any])
async def process_query(input_data: QueryInput = Body(...)):
    """
    Process a user query through the agent workflow.
    """
    try:
        # Initialize state with the query
        initial_state = State(
            query=input_data.query,
            messages=[HumanMessage(content=input_data.query)],
            coordinator=None,
            planner=None,
            researcher=None,
            reporter=None,
            current_time=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
        )

        # Run the graph
        result = await graph.ainvoke(initial_state, {"recursion_limit": 10})
        response = result.get("response", "No response generated.")
        reporter_result = result.get("reporter_result")
        return {
            "query": input_data.query,
            "response": reporter_result if reporter_result else response,
            "workflow_path": list(result.keys())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("__main__:app", host="0.0.0.0", port=8081, reload=True, workers=2)
    langchain.debug = True
