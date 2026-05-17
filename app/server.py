from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import __routers__

from dyresearch.factory.database import initialize_database
from dyresearch.tools.knowledge_base.ingestion import docling_executor
from dyresearch.utils.logger import get_logger


logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic ---
    try:
        await initialize_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        
    yield 
    # --- Shutdown Logic ---
    logger.info("Shutting down documents Process Pool...")
    docling_executor.shutdown(wait=True, cancel_futures=True)


app = FastAPI(
    title="DyResearch",
    description="API wrapper for DyResearch study project ",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS is REQUIRED for Obsidian to talk to localhost safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #NOTE Fine for local.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in __routers__:
    app.include_router(router)
    logger.debug(f"Included {router.__class__} Router")


if __name__ == "__main__":
    import uvicorn
    import sys

    logger.info("🚀 DyResearch Engine is starting on http://127.0.0.1:8000")
    
    try:
        uvicorn.run(
            "app.server:app", 
            host="127.0.0.1", 
            port=8000, 
            reload=False,     # MUST be False for PyInstaller
            # workers=1         # Keep it simple for local use
        )
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        input("Press Enter to exit...")
