# 🧠 Research Brief Generator

A modular and intelligent research brief generator powered by LangGraph, Gemini LLM, and DuckDuckGo search. It creates well-structured research summaries using a multi-step reasoning pipeline designed to simulate human-like research behavior.

## 🚀 Overview

This project enables automated generation of in-depth research briefs on any topic. It uses a LangGraph-based workflow with specialized nodes for planning, web search, summarization, synthesis, and contextual post-processing. It supports both REST API and CLI interfaces for flexible usage.

---

## 🗂️ Project Structure

```
research-brief-generator/
├── app/
│   ├── main.py              # FastAPI app
│   ├── cli.py               # CLI interface
│   ├── schemas.py           # Pydantic models
│   ├── graph/
│   │   ├── state.py         # LangGraph state definition
│   │   ├── nodes.py         # Workflow nodes (context, planning, etc.)
│   │   └── workflow.py      # LangGraph workflow orchestration
│   └── services/
│       ├── llm_service.py   # LLM interaction with Gemini
│       ├── search_service.py # DuckDuckGo web search
│       └── context_service.py # Context management (memory-based)
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Features

### ✅ LangGraph-Based Modular Workflow

* The workflow is built using **LangGraph**, with nodes handling:

  * Context Retrieval
  * Research Planning
  * Web Search
  * Source Summarization
  * Brief Synthesis
  * Post-processing
* Transitions are conditionally managed with error fallbacks and retries.
* Uses a stateful memory-saving mechanism for context checkpointing.

### ✅ Gemini LLM Integration

* Uses **Gemini-1.5-Flash** for high-performance LLM tasks.
* Distinct prompt strategies are used for simple and complex subtasks.
* Handles structured outputs using schema enforcement and parsing.

### ✅ DuckDuckGo Search

* Integrates **DuckDuckGo** for real-time, no-cost web search.
* Extracts top URLs for each sub-topic and sends content for summarization.

### ✅ Context Awareness

* Maintains per-user research history and stores relevant context.
* Follows up on previous queries using prior briefs to enrich responses.

### ✅ Strong Typing & Validation

* Implements structured Pydantic models:

  * `ResearchPlan`
  * `SourceSummary`
  * `FinalBrief`
* Ensures end-to-end type safety and validation of every processing step.

### ✅ API and CLI Support

* FastAPI server with a single `/brief` POST endpoint.
* CLI interface for headless interaction via the terminal.

---

## 🧪 Example Usage

### 📦 Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create your .env file
cp .env.example .env

# Add your Gemini API Key
nano .env  # or use your favorite editor
```

### 🌐 Run API Server

```bash
uvicorn app.main:app --reload --port 8000
```

#### Example API Call

```bash
curl -X POST "http://localhost:8000/brief" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "artificial intelligence in healthcare",
    "depth": 3,
    "follow_up": false,
    "user_id": "user123"
  }'
```

### 💻 CLI Usage

```bash
# Generate a research brief
python -m app.cli generate "artificial intelligence in healthcare" --depth 3 --user-id user123

# Run a follow-up query
python -m app.cli generate "AI diagnostic tools" --depth 2 --user-id user123 --follow-up
```

---

## 🔍 Implementation Highlights

* **Modular Workflow**: Each processing step (node) is designed independently, making the pipeline highly extensible.
* **LLM Abstraction**: Gemini interactions are abstracted and optimized for various task complexities.
* **Web Search**: Integrates web search without external API dependencies.
* **Context Service**: In-memory context manager enabling multi-step research across sessions.
* **Error Handling**: Smart retry logic and fallback strategies in every node to avoid pipeline breakage.
* **LangChain & LangGraph**: Uses LangChain for tool/LLM integration and LangGraph for composable workflows.

---

## 🧩 Environment Variables

Create a `.env` file with:

```bash
GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## 🧱 Key Dependencies

* `fastapi==0.104.1`
* `uvicorn==0.24.0`
* `langchain==0.1.0`
* `langchain-google-genai==1.0.1`
* `langchain-community==0.0.10`
* `langgraph==0.0.20`
* `pydantic==2.5.0`
* `duckduckgo-search==3.9.6`
* `python-dotenv==1.0.0`
* `typer==0.9.0`

---

## 📌 Future Improvements

* Persistent database storage for context instead of in-memory store.
* Enhanced summarization models with citation-aware capabilities.
* UI frontend for non-technical users.

---

## 🧠 Why This Project?

This system aims to replicate the research process of a human analyst—starting with understanding the query, planning research, performing web searches, evaluating sources, and generating structured, synthesized briefs.

Whether you're a student, analyst, or researcher—this tool helps you get concise, accurate, and well-organized insights on complex topics with minimal effort.

---

Let me know when you're ready for the **code-level documentation** generation or if you'd like to include badges, GitHub action workflows, or a demo GIF in the README.


Here’s a professional, clean, and developer-friendly `README.md` for your **Research Brief Generator** project:

---

# 🧠 Research Brief Generator

A LangGraph-powered research assistant that generates concise, structured research briefs on any topic using web search, summarization, planning, and synthesis — all guided by Gemini-1.5-flash. Accessible via FastAPI and a CLI.

---

## 🚀 Features

* **Graph-Based Architecture**: Modular LangGraph workflow with nodes for context, planning, search, summarization, synthesis, and post-processing.
* **Context-Aware**: Maintains user history and incorporates relevant past data into follow-up queries.
* **LLM-Driven**: Uses Google Gemini-1.5-flash for structured reasoning, summarization, and synthesis with robust fallback mechanisms.
* **Web Search Enabled**: Uses DuckDuckGo for free, API-less search integration.
* **Structured Output**: Returns structured, validated research plans, summaries, and briefs using Pydantic models.
* **Multi-Interface Support**: Available via both REST API and command-line interface (CLI).
* **Retry Logic & Error Handling**: Built-in retry, fallbacks, and graceful degradation ensure stability.

---

## 🧱 Project Structure

```
research-brief-generator/
├── app/
│   ├── main.py              # FastAPI API endpoints
│   ├── cli.py               # CLI tool for brief generation
│   ├── schemas.py           # Pydantic models for structured outputs
│   ├── graph/
│   │   ├── state.py         # LangGraph state management
│   │   ├── nodes.py         # LangGraph node definitions
│   │   └── workflow.py      # LangGraph workflow orchestration
│   └── services/
│       ├── llm_service.py   # Gemini LLM interaction logic
│       ├── search_service.py # DuckDuckGo search integration
│       └── context_service.py # Context history and relevance scoring
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/Bhargav4223/research-brief-generator.git
cd research-brief-generator

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your Gemini API key
```

---

## 🌐 Run the API Server

```bash
uvicorn app.main:app --reload --port 8000
```

### Example API Request

```bash
curl -X POST "http://localhost:8000/brief" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "artificial intelligence in healthcare",
    "depth": 3,
    "follow_up": false,
    "user_id": "user123"
  }'
```

---

## 💻 CLI Usage

```bash
# Generate a fresh research brief
python -m app.cli generate "artificial intelligence in healthcare" --depth 3 --user-id user123

# Generate a follow-up brief using previous context
python -m app.cli generate "AI diagnostic tools" --depth 2 --user-id user123 --follow-up
```

---

## 🧠 Core Concepts

### 🧩 LangGraph Workflow

The entire pipeline is modeled using LangGraph, with nodes for:

* **Context Management**: Retrieves and scores relevant past data for personalization.
* **Planning**: Decomposes the research topic into subtopics using the LLM.
* **Search**: Fetches relevant information using DuckDuckGo search.
* **Summarization**: Condenses search results using Gemini.
* **Synthesis**: Combines subtopic summaries into a coherent brief.
* **Post-Processing**: Final formatting and output cleanup.

All nodes operate on a shared typed state and use conditional transitions and error-handling logic.

### 🧾 Schemas & Validation

All data flowing through the system uses well-defined Pydantic models:

* `ResearchPlan`: Holds the LLM-generated research structure.
* `SourceSummary`: Stores condensed summaries of retrieved documents.
* `FinalBrief`: Structured, validated brief returned to the user.

### 🤖 LLM Strategy

* **Model**: Google Gemini-1.5-flash
* **Function**: Prompts optimized for structured outputs.
* **Error Handling**: Auto-retry with relaxed constraints on parsing failures.

### 🔍 Web Search Integration

* Uses the `duckduckgo-search` Python package.
* Avoids API costs and supports lightweight querying of live information.
* Retrieved documents are passed into the summarization node.

### 🧠 Context Awareness

* Tracks user interaction history in memory.
* Relevance scoring determines which past queries to reuse.
* Enables intelligent follow-up generation with evolving briefs.

---

## 📦 Dependencies

```
fastapi==0.104.1
uvicorn==0.24.0
langchain==0.1.0
langchain-google-genai==1.0.1
langchain-community==0.0.10
langgraph==0.0.20
pydantic==2.5.0
duckduckgo-search==3.9.6
python-dotenv==1.0.0
typer==0.9.0
```

---

## 🔐 Environment Variables

Set in `.env`:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## 🧪 Test Locally

After running the API or CLI:

* Try with different topics and `--depth` levels.
* Use the `--follow-up` flag with consistent `--user-id` to test context retention.
* Add logging or print statements to trace node transitions for debugging.

---

## 📈 Future Improvements

* Swap in vector DB for scalable context storage.
* Add PDF/CSV export for research briefs.
* Integrate citations or links to original sources.
* Enhance document chunking logic for better summary coverage.

