# AI Search

A full-stack web application for AI-powered web search and summarization, featuring a FastAPI backend and a React + Vite frontend.

## Features

- **Web Search & Summarization**: Uses Tavily API for web search and OpenAI for generating concise, cited summaries.
- **Streaming Responses**: Real-time streaming of search results and AI-generated summaries.
- **Modern Frontend**: Built with React, TypeScript, and Vite for a fast and interactive user experience.
- **Citations**: Summaries include clickable citations linking to original sources.

---

## Backend

### Tech Stack

- Python 3.8+
- FastAPI
- OpenAI API
- Tavily API
- Uvicorn

### Installation

1. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2. **Set environment variables** (create a `.env` file or export in your shell):
    ```
    OPENAI_API_KEY=your_openai_api_key
    TAVILY_API_KEY=your_tavily_api_key
    OPENAI_BASE_URL=your_openai_base_url  # Optional, for custom OpenAI endpoints
    OPENAI_MODEL_NAME=gpt-3.5-turbo       # Or your preferred model
    ```

3. **Run the backend server**:
    ```bash
    python main.py
    ```
    The API will be available at `http://localhost:8000`.

### Main Endpoint

- `POST /search/summary`
    - **Request Body**: `{ "query": "your question", "top_k": 5 }`
    - **Response**: Server-Sent Events (SSE) streaming search sources and AI summary.

---

## Frontend

### Tech Stack

- React 19
- TypeScript
- Vite

### Installation

1. **Navigate to the frontend directory**:
    ```bash
    cd ai-search-fe
    ```

2. **Install dependencies**:
    ```bash
    pnpm install
    # or
    npm install
    ```

3. **Start the development server**:
    ```bash
    pnpm dev
    # or
    npm run dev
    ```
    The app will be available at `http://localhost:5173` by default.

### Configuration

- The frontend expects the backend API to be running at `http://localhost:8000`.
- You can change the API endpoint in the frontend code if needed.

---

## Project Structure

```
.
├── main.py              # FastAPI backend
├── requirements.txt     # Python dependencies
├── ai-search-fe/        # Frontend (React + Vite)
│   ├── src/
│   ├── package.json
│   └── ...
```

---

## License


MIT