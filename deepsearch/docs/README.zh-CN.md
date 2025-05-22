# DeepSearch

DeepSearch 是一个基于 FastAPI 和 LangChain 构建的智能搜索和问答系统。该系统采用多智能体架构，通过协调器、研究者和报告者三个智能体的协作，为用户提供高质量的搜索结果和回答。

## 功能特点

- 🤖 多智能体协作系统
  - 协调器智能体：负责理解用户意图并协调其他智能体
  - 研究者智能体：负责深入研究和信息收集
  - 报告者智能体：负责整理和呈现最终结果
- 🔄 基于 LangGraph 的工作流管理
- 🚀 高性能 FastAPI 后端
- 📝 结构化的响应格式

## 技术栈

- FastAPI
- LangChain
- LangGraph
- OpenAI
- Tavily Search API
- Pydantic
- Uvicorn

## 安装说明

1. 克隆项目并进入项目目录：
```bash
git clone https://github.com/myersguo/deepsearch.git
cd deepsearch
```

2. 创建并激活虚拟环境：
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置环境变量：
创建 `.env` 文件并设置必要的环境变量：
```
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

5. 安装前端依赖：
```bash
cd web
pnpm install
```

## 使用方法

1. 启动后端服务器：
```bash
python main.py
```

2. 在新的终端窗口中，启动前端应用：
```bash
cd web
pnpm dev
```

3. 后端服务器将在 `http://localhost:8081` 运行
4. 前端界面将在 `http://localhost:5173` 运行

5. API 端点：
- POST `/api/query`
  - 请求体：
    ```json
    {
        "query": "你的问题"
    }
    ```
  - 响应示例：
    ```json
    {
        "query": "原始问题",
        "response": "智能体生成的回答",
        "workflow_path": ["经过的工作流节点"]
    }
    ```

## 项目结构


```
.
├── README.md
├── app
│   ├── __init__.py
│   ├── api
│   │   └── __init__.py
│   ├── config
│   │   └── settings.py
│   └── core
│       ├── __init__.py
│       ├── agents
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── coordinator.py
│       │   ├── reporter.py
│       │   └── researcher.py
│       ├── llm.py
│       ├── prompts
│       │   ├── __init__.py
│       │   ├── coordinator.md
│       │   ├── reporter.md
│       │   └── researcher.md
│       ├── search_engine.py
│       └── types.py
├── docs
├── main.py
├── requirements.txt
└── web
    ├── package.json
    ├── pnpm-lock.yaml
    ├── public
    │   └── index.html
    ├── src
    │   ├── App.css
    │   ├── App.tsx
    │   ├── components
    │   │   ├── ChatInterface.css
    │   │   ├── ChatInterface.tsx
    │   │   ├── InputArea.css
    │   │   ├── InputArea.tsx
    │   │   ├── MarkdownRenderer.css
    │   │   ├── MarkdownRenderer.tsx
    │   │   ├── Message.css
    │   │   ├── Message.tsx
    │   │   ├── MessageList.css
    │   │   └── MessageList.tsx
    │   ├── index.css
    │   └── index.tsx
    └── tsconfig.json
```

## 开发说明

- 项目使用 FastAPI 作为 Web 框架
- 使用 LangGraph 管理工作流
- 采用 Pydantic 进行数据验证
- 支持异步处理请求

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证

[待定]

## 文档

- [English](README.md)
- [中文](docs/README.zh-CN.md) 