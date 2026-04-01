# 📚 dyresearch

> March, 2026

Multi-Agent system able to help studying, learning and researching topics. 

## 🤖 Agents 

A variety of agents using configurable LLM is employed in this project. Currently, the chosen agentic framework is [Google ADK](https://google.github.io/adk-docs/). 

### 👮🏽‍♀️ Coordinator
Handles incoming request from the user and decides which agent is responsible for actions / answers

### 👨🏻‍🏫 Professor
Handles specific queries from the user using its knowledge or information obtained from chunks available in the vector store or 

### 👩🏻‍🏫 Librarian
Handles the organization of knowledge in the system. It's the owner of the library (the vector store) and is able to 
- ingest chunks and query them to organize information into the vector store
- list available sources, by title or index
- index different knowledge bases by subject, query the index and list them 
- delete a single file's chunks or delete a whole index's chunks to cleanup the library

### 👩🏻‍🔬 Researcher
Navigates the Web in search of new information and sources to increment the knowledge base or handle fresh information to the rest of the system. 

### 🧑🏻‍💻 Note Taker
Is responsible to digest complex information into useful notes that could be rendered by [Obsidian](https://obsidian.md/) or other Markdown visualizers tools
- takes notes in .md format
- draws graphs / mind maps in mermaid.js


## 📍Run Locally

````
uv run adk web --session_service_uri postgresql+asyncpg://adk_user:adk_password@localhost:5432/adk_history
````


## 🐳 Run with Docker Compose

To run the whole project in a containerized environment
```
docker-compose up
```

### 🧩 What is Included?
In the `docker-compose.yml` file there are a couple of services available from the get-go
* **ADK Web**: frontend spawned by the container at the initialization of the project. Will be probably replaced 
* **PostGRE SQL**: Memory for agents sessions + vector store thanks to the `pgvector` extension


### ❌ What's NOT Included
Currently, what's missing is configuration to
* visualize notes with Obsidian
* access PostGRE via a DBMS like [DBvear](https://dbeaver.io/)

