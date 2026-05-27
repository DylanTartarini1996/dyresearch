# 📚 DyResearch

> May, 2026

A Multi-Agent AI system designed to aid in studying, learning, and researching topics.  

Built with [Google ADK](https://google.github.io/adk-docs/) and served via a FastAPI backend, the system seamlessly interfaces with an [Obsidian plugin](https://github.com/DylanTartarini1996/dyresearch-obsidian) for automated knowledge management and note-taking workflows.

![settings](assets/obsidian_screen.png)

---

## 🛠 Tech Stack

- **Agent Framework:** [Google ADK](https://google.github.io/adk-docs/)
- **Backend:** [FastAPI](https://fastapi.tiangolo.com/)
- **Database & Vector Store:** [PostgreSQL](https://www.postgresql.org/) with [`pgvector`](https://github.com/pgvector/pgvector) or SQLlite with [`lancedb`](https://github.com/lancedb/lancedb)
- **LLM Integration:** LiteLLM (Google, Groq, local models) -> currently only Gemini is considered stable for this project
- **Document Processing:** [Docling](https://www.docling.ai/)

---

## 🤖 Agents 

A variety of specialized agents using configurable LLMs work together to process requests:

### 👮🏽‍♀️ Coordinator
The central manager that handles incoming requests from the user and delegates tasks to the appropriate specialized agent.

### 👨🏻‍🏫 Professor
Handles specific questions and tutoring queries by drawing from its core knowledge or fetching retrieved context directly from the vector store.

### 👩🏻‍🏫 Librarian
Manages the organization of knowledge within the system. As the owner of the vector store library, the Librarian can:
- Ingest documents and chunk them to organize information in the vector store.
- List available sources by title or index.
- Index different knowledge bases by subject and query them.
- Cleanup the library by deleting chunks of a single file or a complete index.

### 👩🏻‍🔬 Researcher
Autonomously navigates the web to find new information, discover fresh sources, and expand the knowledge base, providing up-to-date context to the rest of the system.

### 🧑🏻‍💻 Note Taker
Responsible for digesting complex information into structured, useful notes specifically formatted for [Obsidian](https://obsidian.md/) or other Markdown tools:
- Takes detailed notes in `.md` format.
- Generates graphs and mind maps using Mermaid.js syntax.

---

## 🧩 Getting Started with the Obsidian Plugin

To integrate DyResearch into Obsidian, download the latest release directly from Obsidian Community Plugins (**not yet available as an option**) or directly from its [Github page](https://github.com/dyresearch-obsidian).  


### 🚀 Starting the BackEnd 

> [!NOTE] 
>
> by default, DyResearch runs in local mode using SLQlite and LanceDB to store sessions and vectors. If you want to use PostgreSQL you can 
>   - run the docker compose as specified below (local run)
>  - point to a Postgres instance running anywhere (i.e. Supabase, Cloud providers..) using the connection string.


To run the backend locally using Docker Compose:  

```bash
docker-compose up -d
```
This will start the FastAPI server on port `8000` and the PostgreSQL database.


### ⚙️ Environment Configuration & Data:
You can set up the configuration for session storage and agents in two ways:

1. First road is to use the Obsidian's settings UI: 
   - Restart Obsidian.
   - Go to **Settings > Community Plugins** and enable **DyResearch AI Sidecar**.
   - Open the **DyResearch** settings page within Obsidian.
   - Configure the API endpoint and credentials provided by your hosting service.
   - *Note: For standalone use, the system will automatically instantiate a local SQLite instance coupled with LanceDB to manage your vector data and session history locally. -> if you rather use postgres on your machine, point to it via the settings page*

   ![restart](assets/obsidian_enable_plugin.png)

2. Ensure a local `config.env` file is correctly populated in the root directory with your API keys.

   ```env
   # Database Config
   POSTGRES_USER=adk_user
   POSTGRES_PASSWORD=adk_password
   POSTGRES_DB=adk_history

   # LLM Providers (Google, Groq, Ollama)
   GOOGLE_API_KEY=your_api_key
   GOOGLE_API_KEY=your_api_key
   GOOGLE_MODEL_NAME=gemini-3.1-flash-lite-preview

   # Embeddings
   EMBEDDINGS_TYPE=google
   EMBEDDINGS_MODEL_NAME=gemini-embedding-001
   ```

---

## 📍 Local Development
To run the app locally, make sure [uv]() is installed in your machine, create the environment using `uv sync ` and then run

```bash
uv run uvicorn dyresearch.app.server:app --host 0.0.0.0 --port 8000

```
