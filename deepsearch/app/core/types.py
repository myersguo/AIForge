from typing import Dict, Any, Optional

from langgraph.graph import MessagesState


class State(MessagesState):
    next_node: Optional[str] = None
    query: str
    locale: str = 'en'
    response: Optional[str] = None
    coordinator: Optional[Dict[str, Any]] = None
    search_result: Optional[Dict[str, Any]] = None
    reporter_result: Optional[Dict[str, Any]] = None
    current_time: Optional[str] = None
    search_keyword: Optional[str] = None
