import os
from typing import AsyncGenerator

from contextlib import asynccontextmanager
from urllib.parse import quote_plus
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from ..config import DBConfig
from ..entities import Base 
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Try to get config from environment
db_config = DBConfig(
    password=os.getenv('POSTGRES_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    user=os.getenv('POSTGRES_USER'), 
    database=os.getenv('POSTGRES_DB'),
    url=os.getenv('SESSION_SERVICE_URI')
)


class DatabaseFactory:
    def __init__(self, config: DBConfig):
        # Determine if we should use Postgres or SQLite
        self.config = config
        self.is_postgres = config.is_postgres
            
        logger.info(f"DB Init - host: {config.host}, url: {config.url}, is_postgres: {self.is_postgres}")
        
        # Engine parameters
        engine_kwargs = {
            "echo": False,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
        }
        
        if self.is_postgres:
            engine_kwargs["pool_size"] = 50
            engine_kwargs["max_overflow"] = 10
            
        self.engine = create_async_engine(
            self.get_db_url(), 
            **engine_kwargs
        )
            
        self.session_factory = async_sessionmaker(
                                autocommit=False,
                                autoflush=False,
                                bind=self.engine,
                                expire_on_commit=False
                            )

    async def init_models(self):
        """Initialize database models asynchronously"""
        async with self.engine.begin() as conn:
            if self.is_postgres:
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
                    logger.info("Verified pgvector existence")
                except Exception as e:
                    logger.warning(f"Could not create pgvector extension: {e}")
            
            await conn.run_sync(Base.metadata.create_all)
            logger.info(f"Created metadata (Postgres: {self.is_postgres})")


    def get_db_url(self) -> str:
        """Generate database URL with proper URL encoding and validation"""
        
        # Priority 1: Direct URL from config
        if self.config.url:
            return self.config.url

        # Priority 2: Build Postgres URL if is_postgres
        if self.is_postgres:
            if not all([self.config.user, self.config.password, self.config.host, self.config.port, self.config.database]):
                logger.error("❌ Invalid Postgres configuration - one or more fields are missing")
                raise ValueError("Missing database configuration environment variables for PostgreSQL")

            encoded_user = quote_plus(str(self.config.user))
            encoded_password = quote_plus(str(self.config.password))
            
            try:
                port = int(self.config.port)
            except (ValueError, TypeError):
                logger.error(f"❌ Invalid DB port: {self.config.port}")
                raise

            url = f"postgresql+asyncpg://{encoded_user}:{encoded_password}@{self.config.host}:{port}/{self.config.database}"
            logger.info(f"Connecting to Postgres at {self.config.host}:{port}")
            return url
        
        # Priority 3: Fallback to local SQLite
        default_db = "sqlite+aiosqlite:///./adk_history.db"
        logger.info(f"Using default local SQLite database: {default_db}")
        return default_db


database_factory = DatabaseFactory(db_config)

async def initialize_database():
    """Initialize the database and create all tables"""    
    await database_factory.init_models()


@asynccontextmanager
async def get_db_context(db_config: DBConfig):
    global database_factory
    try:
        session = database_factory.session_factory()
        # Check if connection is up
        await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Connection error: {e}")
        logger.info("Recreating factory")
        database_factory = DatabaseFactory(db_config)

        try:
            session = database_factory.session_factory()
            # Check if connection is up
            await session.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"❌ Error after connection refresh: {e}")
            raise Exception("Unable to connect to database")   
    try:
        yield session
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        await session.rollback()
        raise
    finally:
        await session.close()
        
        
async def get_db_async(db_config: DBConfig) -> AsyncGenerator[AsyncSession, None]:
    async with get_db_context(db_config) as session:
        yield session