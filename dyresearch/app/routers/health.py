import os

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from ...core.config import DBConfig
from ...core.factory.database import get_db_async
from ...core.utils.logger import get_logger

logger = get_logger(__name__)

db_config = DBConfig(
    password=os.getenv('POSTGRES_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    user=os.getenv('POSTGRES_USER'), 
    database=os.getenv('POSTGRES_DB')
)

DBDependencyAsync = Annotated[AsyncSession, Depends(lambda: get_db_async(db_config))]

health_router = APIRouter(prefix="/health",tags=["health"])

@health_router.get("/", tags=["health"])
async def healthcheck(db_async: DBDependencyAsync):
    try: 
        logger.info("✅ Application is healthy")
        return {"status": "OK"} 
    
    except Exception as e: 
        logger.error(f"❌ Healthcheck not passed: {e}")
        return {"status": "KO"}