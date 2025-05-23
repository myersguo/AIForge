import os
import json
import jinja2
from langchain_core.messages import HumanMessage, SystemMessage, AIMessageChunk, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.types import Command

from app.core.agents.base import BaseAgent
from app.core.llm import get_llm
from app.core.types import State


class CoordinatorAgent(BaseAgent):
    def __init__(self):
        self.llm = get_llm()

        # Load prompt template
        template_path = os.path.join(os.path.dirname(__file__), "../prompts/coordinator.md")
        with open(template_path, "r") as f:
            template_content = f.read()

        self.prompt_template = jinja2.Template(template_content)

    async def process(self, state: State) -> Command:
        locale = state.get("locale", "en")
        prompt_content = self.prompt_template.render(query=state.get("query"), locale=locale, CURRENT_TIME=state.get("current_time"))
        chain = self.llm
        messages = [SystemMessage(content=prompt_content), HumanMessage(content=state.get("query"))]
        result = await chain.ainvoke(messages)

        # Use the detected locale from the LLM response, or fall back to the current locale
        detected_locale = result.get("locale", locale)

        return Command(
            goto="researcher_node" if result.get("coordinator") == "requires_research" else "END",
            update={"coordinator": result.get("coordinator"),
                    "response": result.get("response"),
                    "locale": detected_locale,
                    "search_keyword": result.get("search_keyword"),
                    }
        )

    async def process_stream(self, state: State):
        locale = state.get("locale", "en")
        prompt_content = self.prompt_template.render(query=state.get("query"), locale=locale, CURRENT_TIME=state.get("current_time"))
        chain = self.llm
        messages = [SystemMessage(content=prompt_content), HumanMessage(content=state.get("query"))]
        
        # 用于累积完整的流式输出内容
        full_content = "" 

        # Stream the response
        async for chunk in chain.astream(messages):
            if chunk:
                current_chunk_content = ""
                if isinstance(chunk, AIMessageChunk):
                    current_chunk_content = chunk.content
                elif isinstance(chunk, dict) and "response" in chunk: # Fallback for non-AIMessageChunk if chain returns dict
                    current_chunk_content = chunk.get("response", "")
                
                full_content += current_chunk_content # 累积所有分块的内容

                # 更新流式缓冲区，只发送当前 chunk 的内容
                state["stream_buffer"] = current_chunk_content 
                # 立即返回流式更新
                yield Command(
                    goto=None, # Stay on the same node for streaming updates
                    update={"stream_buffer": state.get("stream_buffer")}
                )

        # Get final result from the accumulated full_content
        # 尝试从累积的完整内容中解析 JSON
        try:
            # 清理 JSON 字符串，去除可能的 Markdown 标记
            result_str = full_content.replace("```json", "").replace("```", "").strip()
            result = json.loads(result_str)
        except json.JSONDecodeError:
            # 如果解析失败，回退到将整个内容作为响应
            print(f"Warning: Could not parse JSON from streamed content. Full content: {full_content}")
            result = {"response": full_content} # 确保 result 是一个字典以便后续访问

        detected_locale = result.get("locale", locale)

        # Update state with final result
        state["coordinator"] = result.get("coordinator")
        state["response"] = result.get("response")
        state["locale"] = detected_locale
        state["search_keyword"] = result.get("search_keyword")

        # Yield final command with all updates
        yield Command(
            goto="researcher_node" if result.get("coordinator") == "requires_research" else "END",
            update={
                "coordinator": result.get("coordinator"),
                "response": result.get("response"),
                "locale": detected_locale,
                "search_keyword": result.get("search_keyword"),
                "stream_buffer": None  # Clear the stream buffer
            }
        )
