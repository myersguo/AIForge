import json
from datetime import datetime
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, ToolMessage
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.pregel.io import AddableUpdatesDict
from pydantic import BaseModel

from app.config.settings import settings
from app.core.agents.coordinator import CoordinatorAgent
from app.core.agents.reporter import ReporterAgent
from app.core.agents.researcher import ResearcherAgent
from app.core.types import State

app = FastAPI(title=settings.PROJECT_NAME)

# 修复跨域
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
coordinator_agent = CoordinatorAgent()
researcher_agent = ResearcherAgent()
reporter_agent = ReporterAgent()


class QueryInput(BaseModel):
    query: str
    stream: bool = False


class SearchRequest(BaseModel):
    query: str


from langchain_core.runnables import RunnableLambda


def route_coordinator(state: State):
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
    workflow.add_node("coordinator_node",
                      coordinator_agent.process_stream if settings.STREAMING else coordinator_agent.process)
    workflow.add_node("researcher_node",
                      researcher_agent.process_stream if settings.STREAMING else researcher_agent.process)
    workflow.add_node("reporter_node", reporter_agent.process_stream if settings.STREAMING else reporter_agent.process)

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


async def process_stream(state: State) -> AsyncGenerator[str, None]:
    """
    Process the query with streaming response.
    Returns an async generator that yields server-sent events.
    """

    def _make_event(data: any, event_type: str) -> str:
        if isinstance(data, dict) and data.get("content") == "":
            data.pop("content")
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    try:
        async for agent, _, chunk in graph.astream(state,
                                                   config={
                                                       "max_plan_iterations": 1,
                                                       "recursion_limit": 10,
                                                   },
                                                   stream_mode=["messages", "updates"],
                                                   subgraphs=True,
                                                   ):
            if isinstance(chunk, tuple) and len(chunk) >= 2:
                # 中间过程
                message_chunk = chunk[0]
                metadata = chunk[1] if len(chunk) > 1 else {}

                # 处理 AIMessageChunk
                if isinstance(message_chunk, AIMessageChunk):
                    data = {
                        'chunk': message_chunk.content,
                        'type': 'stream',
                        'done': False,
                        'node': metadata.get('langgraph_node', 'unknown')
                    }
                    yield _make_event(data=data, event_type="stream")

                # 处理 ToolMessage
                elif isinstance(message_chunk, ToolMessage):
                    continue
                    data = {
                        'chunk': message_chunk.content,
                        'type': 'tool_result',
                        'done': False,
                        'node': metadata.get('langgraph_node', 'unknown'),
                        'tool_call_id': getattr(message_chunk, 'tool_call_id', None)
                    }
                    yield _make_event(data=data, event_type="stream")

                continue

            # 处理嵌套的chunk结构
            elif isinstance(chunk, dict):
                if isinstance(chunk, AddableUpdatesDict):
                    for key, value in chunk.items():
                        # 处理各种类型的节点数据
                        if isinstance(value, dict):
                            if value.get("stream_buffer"):
                                data = {
                                    'chunk': value['stream_buffer'],
                                    'type': 'intermediate',
                                    'done': False,
                                    'node': key
                                }
                                yield _make_event(data=data, event_type="stream")

                            # 处理最终结果
                            elif value.get("reporter_result"):
                                data = {
                                    'chunk': value['reporter_result'],
                                    'type': 'reporter_result',
                                    'done': True,
                                    'node': key
                                }
                                yield _make_event(data=data, event_type="final")

                            elif value.get("search_result"):
                                data = {
                                    'chunk': value['search_result'],
                                    'type': 'search_result',
                                    'done': True,
                                    'node': key
                                }
                                yield _make_event(data=data, event_type="final")

                            elif value.get("response"):
                                data = {
                                    'chunk': value['response'],
                                    'type': 'final',
                                    'done': True,
                                    'node': key
                                }
                                yield _make_event(data=data, event_type="final")

                else:
                    # 处理常规字典
                    for node_name, node_data in chunk.items():
                        if not isinstance(node_data, dict):
                            continue

                        # 处理各种类型的节点数据
                        if node_data.get("stream_buffer"):
                            data = {
                                'chunk': node_data['stream_buffer'],
                                'type': 'intermediate',
                                'done': False,
                                'node': node_name
                            }
                            yield _make_event(data=data, event_type="stream")

                        elif node_data.get("reporter_result"):
                            data = {
                                'chunk': node_data['reporter_result'],
                                'type': 'reporter_result',
                                'done': True,
                                'node': node_name
                            }
                            yield _make_event(data=data, event_type="final")

                        elif node_data.get("search_result"):
                            data = {
                                'chunk': node_data['search_result'],
                                'type': 'search_result',
                                'done': True,
                                'node': node_name
                            }
                            yield _make_event(data=data, event_type="final")

                        elif node_data.get("response"):
                            data = {
                                'chunk': node_data['response'],
                                'type': 'final',
                                'done': True,
                                'node': node_name
                            }
                            yield _make_event(data=data, event_type="final")

            else:
                continue

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        import traceback
        traceback.print_exc()
        print(f"[mainDebug] Error in process_stream: {error_message}")
        yield _make_event(data={'error': error_message}, event_type="error")


@app.post("/api/query")
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
            is_streaming=input_data.stream
        )

        if input_data.stream:
            return StreamingResponse(
                process_stream(initial_state),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "Content-Type": "text/event-stream",
                    "Transfer-Encoding": "chunked"
                }
            )

        # Run the graph for non-streaming response
        result = await graph.ainvoke(initial_state, {"recursion_limit": 10})
        response = result.get("response", "No response generated.")
        reporter_result = result.get("reporter_result")
        return {
            "query": input_data.query,
            "response": reporter_result if reporter_result else response,
            "workflow_path": list(result.keys())
        }

    except Exception as e:
        print(f"[DEBUG] Error in process_query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.post("/api/query_stream")
async def process_query_stream(request: SearchRequest):
    """
    Process a user query through the agent workflow with streaming response.
    """
    try:
        # Initialize state with the query
        initial_state = State(
            query=request.query,
            messages=[HumanMessage(content=request.query)],
            coordinator=None,
            planner=None,
            researcher=None,
            reporter=None,
            current_time=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
            is_streaming=True
        )

        return StreamingResponse(
            process_stream(initial_state),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Type": "text/event-stream",
                "Transfer-Encoding": "chunked"
            }
        )

    except Exception as e:
        print(f"[DEBUG] Error in query_stream: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("__main__:app", host="0.0.0.0", port=8081, reload=True, workers=1)
