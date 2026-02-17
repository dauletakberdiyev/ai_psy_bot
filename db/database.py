"""Database connection and session management."""
import asyncpg
from typing import Optional
from contextlib import asynccontextmanager

from config import config
from utils.logger import logger


class Database:
    """PostgreSQL database connection manager."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create database connection pool."""
        try:
            # Use DATABASE_URL if available (Railway), otherwise use individual params
            if config.DATABASE_URL_ENV:
                self.pool = await asyncpg.create_pool(
                    dsn=config.DATABASE_URL,
                    min_size=5,
                    max_size=20,
                    command_timeout=60
                )
                logger.info(f"Database pool created using DATABASE_URL")
            else:
                self.pool = await asyncpg.create_pool(
                    host=config.DB_HOST,
                    port=config.DB_PORT,
                    database=config.DB_NAME,
                    user=config.DB_USER,
                    password=config.DB_PASSWORD,
                    min_size=5,
                    max_size=20,
                    command_timeout=60
                )
                logger.info(f"Database pool created: {config.DB_NAME}@{config.DB_HOST}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args):
        """Execute a query that doesn't return results."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Fetch a single row."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch a single value."""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)


# Global database instance
db = Database()
