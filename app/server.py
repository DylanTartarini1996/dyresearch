from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import __routers__
from dyresearch.utils.logger import get_logger


logger = get_logger(__name__)

app = FastAPI(
    title="DyResearch",
    description="API wrapper for DyResearch study project ",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
