from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import List, Optional, AsyncGenerator
import httpx # For async HTTP requests
import openai
import os
import uvicorn
import json
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------
# Data Model Definitions
# ------------------
class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class SearchSource(BaseModel): # Will be used within the data part of an SSE event
    title: str
    url: str

class Settings(BaseSettings):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "your_openai_api_key")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "your_tavily_api_key")
    OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
openai_client = openai.AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None,
)

# ------------------
# Call Tavily Search API (Async)
# ------------------
async def search_web_async(query: str, top_k: int = 5) -> List[dict]:
    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": settings.TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": top_k
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Tavily service request failed: {exc}")
        except httpx.HTTPStatusError as exc:
            error_detail = f"Tavily search failed with status {exc.response.status_code}"
            try:
                error_content = exc.response.json()
                error_detail += f": {error_content.get('error', 'Unknown error')}"
            except json.JSONDecodeError:
                error_detail += f": {exc.response.text}"
            raise HTTPException(status_code=exc.response.status_code, detail=error_detail)
    return response.json().get("results", [])

# ------------------
# Use OpenAI to generate and stream summary (Async Generator)
# This generator now raises exceptions on API error to be caught by its caller.
# ------------------

async def generate_summary_stream_content(query: str, snippets: List[str]) -> AsyncGenerator[str, None]:
    numbered_snippets = [
        f"[[citation:{i + 1}]] {snippet}" for i, snippet in enumerate(snippets)
    ]

    prompt = f"""
You are a large language AI assistant. You are given a user question, and please write clean, concise and accurate answer to the question. You will be given a set of related contexts to the question, each starting with a reference number like [[citation:x]], where x is a number. Please use the context and cite the context at the end of each sentence if applicable.
Your answer must be correct, accurate and written by an expert using an unbiased and professional tone. Please limit to 1024 tokens. Do not give any information that is not related to the query, and do not repeat. Say "information is missing on" followed by the related topic, if the given context do not provide sufficient information.
Please cite the contexts with the reference numbers, in the format [citation:x].
If a sentence comes from multiple contexts, please list all applicable citations, like [citation:3][citation:5]. Other than code and specific names and citations, your answer must be written in the same language as the query.
Here are the set of contexts:

Query: {query}

Snippets:
{chr(10).join(numbered_snippets)}

Answer in 3-5 bullet points, with clarity. Only provide the answer to the query based on the snippets. Do not add any conversational filler before or after the answer.
Remember, don't blindly repeat the contexts verbatim. And here is the user question:
"""
    stream = await openai_client.chat.completions.create(
        model=settings.OPENAI_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=512,
        stream=True
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


# ------------------
# Main Streaming Endpoint /search/summary (SSE Formatted)
# ------------------
async def stream_response_generator(query: str, top_k: int) -> AsyncGenerator[str, None]:
    # Helper to format SSE messages
    def format_sse_event(event_name: str, data: any) -> str:
        json_data = json.dumps(data)
        return f"event: {event_name}\ndata: {json_data}\n\n"

    # 1. Get search results
    try:
        results = await search_web_async(query, top_k)
    except HTTPException as e:
        yield format_sse_event("error", {"message": f"Search failed: {e.detail}", "status_code": e.status_code})
        return
    except Exception as e: # Catch any other unexpected error during search
        yield format_sse_event("error", {"message": f"An unexpected error occurred during search: {str(e)}"})
        return


    if not results:
        yield format_sse_event("error", {"message": "No search results found"})
        return

    # 2. Prepare and yield sources
    print(f"Found {len(results)} results.")
    """
    result example:
    [{'title': '特斯拉到底好在哪里？ - 懂车帝', 'url': 'https://www.dongchedi.com/article/7267539877166694968', 'content': '特斯拉的平台. 电池：特斯拉的电池是直接采购供应商的，之前采用的是松下和LG化学展自己的电池技术。 电机：虽然目前特斯拉也自研电机，特斯拉工程师认为永磁电机比感应电机没有太大优势，考虑到', 'score': 0.5920305, 'raw_content': None}, {'title': '不吹不黑，特斯拉用车5个月的客观感受 - 知乎',换成了 特斯拉 ，油换电还是有些忐忑，买之前纠结了很久，各种网上找电车车评。 甚至在街上看到特斯拉车主主动去问用车感受。这样看了一个多月果断入手特斯拉标续 model Y ，没有考虑model3，考虑到空间直接入手model Y。3 是真的很好看!', 'score': 0.52071625, 'raw_content': None}, {'title': '特斯拉到底值不值得买？ - 知乎', 'url': 'https://www.zhihu.com/question/444719467', 'content': '值不值看你怎么想. 一部分人认为早买早享a之后感觉还是很香：1、在家里安装充电桩省下一大笔油费开销，晚上回家充电，白天出门，方便得很；2、高速自动驾驶；3、百米提速，油车还才起步，特斯拉已不见踪影；4、和大家', 'score': 0.50915486, 'raw_content': Non.smzdm.com/p/admgdd9k/', 'content': '过去半年以来，特斯拉Model Y的用户体验得到了大量车主的分享和反馈。 特斯拉作为电动汽车领域的先锋，其Model Y车型因其独特的设计、强大的功能以及出色的驾驶体验备受用户瞩目。' 'raw_content': None}, {'title': '给准备买特斯拉的五个忠告! - 知乎 - 知乎专栏', 'url': 'https://zhuanlan.zhihu.com/p/105702853', 'content': '大家好，我是特斯拉小V，显而易见我是一名TESLA的销售，别别别滑走!!Model 3 内容我大致做了精简节省各位宝贵的时…', 'score': 0.25411126, 'raw_content': None}]
    """
    sources_data = [SearchSource(title=r.get("title", ""), url=r.get("url", "")).model_dump() for r in results]
    yield format_sse_event("sources", sources_data)

    # 3. Prepare snippets and stream summary
    snippets = [r.get("content", r.get("snippet", "")) for r in results if r.get("content") or r.get("snippet")]
    if not snippets:
        # Send as an answer_chunk or a specific event like "info"
        yield format_sse_event("answer_chunk", "Could not extract snippets from search results to generate a summary.")
        yield format_sse_event("done", {"message": "Stream completed due to no snippets."})
        return

    try:
        async for summary_chunk_content in generate_summary_stream_content(query, snippets):
            # The data for answer_chunk is the text string itself
            yield format_sse_event("answer_chunk", summary_chunk_content)
    except openai.APIStatusError as e:
        error_data = {
            "message": f"AI API status error: {e.status_code}",
            "type": e.type,
            "code": e.code,
            "param": e.param,
            "details": str(e.body) if e.body else str(e)
        }
        print(f"AI API Status Error: {e}")
        yield format_sse_event("error", error_data)
    except openai.APIError as e:
        error_data = {
            "message": "OpenAI API error during summary generation",
            "details": str(e.body) if e.body else str(e)
        }
        print(f"OpenAI API Error: {e}")
        yield format_sse_event("error", error_data)
    except Exception as e:
        print(f"An unexpected error occurred during OpenAI streaming: {e}")
        yield format_sse_event("error", {"message": f"Unexpected error during summary generation: {str(e)}"})
    else: # Only yield "done" if the stream completed without OpenAI errors
        yield format_sse_event("done", {"message": "Stream completed successfully."})


@app.post("/search/summary")
async def search_summary_sse_endpoint(request: SearchRequest):
    return StreamingResponse(
        stream_response_generator(request.query, request.top_k),
        media_type="text/event-stream" # SSE media type
    )
if __name__ == "__main__":
    uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=True, workers=1)
