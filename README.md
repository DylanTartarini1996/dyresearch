# 📚 DyResearch

> May, 2026

A Multi-Agent AI system designed to aid in studying, learning, and researching topics. Built with [Google ADK](https://google.github.io/adk-docs/) and served via a FastAPI backend, the system seamlessly interfaces with an Obsidian sidecar plugin for automated knowledge management and note-taking workflows.


![settings](assets/obsidian_screen.png)

---

## 🛠 Tech Stack

- **Agent Framework:** [Google ADK](https://google.github.io/adk-docs/)
- **Backend:** FastAPI (Python)
- **Database & Vector Store:** PostgreSQL with `pgvector`
- **LLM Integration:** LiteLLM (Google, Groq, local models)
- **Document Processing:** Docling

---

## 🧩 Getting Started with the Obsidian Plugin

You can integrate DyResearch into your Obsidian workflow in two ways:

### Option 1: Non-Technical User (Quick Install)
*Best for users who want to get started quickly without managing infrastructure.*

1. **Prerequisites:** Ensure you have [Obsidian](https://obsidian.md/) installed.
2. **Installation:**
   - Download the latest plugin release from the [GitHub Actions page](https://github.com/dyresearch/dyresearch/actions) (look for the artifact containing `main.js`, `manifest.json`, and `styles.css`).
   - Locate your Obsidian vault's plugin directory: `<your-vault-folder>/.obsidian/plugins/`.
   - Create a folder named `dyresearch-ai` and extract the downloaded files into it.
3. **Configuration & Data:**
   - Restart Obsidian.
   - Go to **Settings > Community Plugins** and enable **DyResearch AI Sidecar**.
   - Open the **DyResearch** settings page within Obsidian.
   - Configure the API endpoint and credentials provided by your hosting service.
   - *Note: For standalone use, the system will automatically instantiate a local SQLite instance coupled with LanceDB to manage your vector data and session history locally.*

   ![settings](assets/obsidian_settings.png)

   ![restart](assets/obsidian_enable_plugin.png)

### Option 2: Developer (Self-Hosted)
*Best for developers who want full control over the backend, database, and agent logic.*

1. **Infrastructure:** Run the backend locally using Docker Compose:
   ```bash
   docker-compose up -d
   ```
   This will start the FastAPI server on port `8000` and the PostgreSQL database.
2. **Plugin Setup:**
   - Navigate to the `dyresearch-sidecar` directory in this project.
   - Install dependencies and build the plugin:
     ```bash
     npm install
     npx tsup main.ts --format cjs --external obsidian
     ```
   - Follow the installation steps in Option 1 to link this built version into your vault.
3. **Configuration:**
   - Ensure your local `config.env` is correctly populated with your API keys.
   - Set the Obsidian plugin's API URL to `http://localhost:8000`.

---

## 🚀 Obsidian Plugin Functionalities

The DyResearch Obsidian plugin bridges your knowledge base with the intelligent backend, providing:

*   **Intelligent Chat:** Engage in multi-turn conversations with specialized agents (Professor, Librarian, Researcher) via a chat interface.
*   **Knowledge Management:** Seamlessly ingest local markdown files or documents into the vector store for RAG-powered retrieval.
*   **Session Management:** Create, rename, delete, and search through your AI chat sessions directly from Obsidian.
*   **History Sync:** Review previous chat history and retrieve context from past interactions.
*   **Note Taking:** Automatically digest information into structured notes with support for Mermaid.js diagrams.

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

## ⚙️ Environment Configuration

If you are running the backend yourself, ensure your `config.env` is configured in the root directory:

```env
# Database Config
POSTGRES_USER=adk_user
POSTGRES_PASSWORD=adk_password
POSTGRES_DB=adk_history

# LLM Providers (Google, Groq, Ollama)
GOOGLE_API_KEY=your_api_key
GROQ_API_KEY=your_api_key
GOOGLE_MODEL_NAME=gemini-3.1-flash-lite-preview

# Embeddings
EMBEDDINGS_TYPE=google
EMBEDDINGS_MODEL_NAME=gemini-embedding-001
```

---

## 📍 Developer: Running Locally Without Docker

If you prefer to run the API server directly on your host machine:

1. Ensure you have **Python >= 3.12** and the [`uv`](https://github.com/astral-sh/uv) package manager installed.
2. Ensure your Postgres database is running.
3. Start the FastAPI server:
   ```bash
   uv run uvicorn app.server:app --host 127.0.0.1 --port 8000 --reload
   ```