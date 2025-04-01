import datetime, databases
from sqlalchemy import (
    Column, Integer, String, Float, 
    DateTime, Text, Boolean, 
    MetaData, Table
)
from sqlalchemy.ext.asyncio import create_async_engine
from src.core.config import settings

# Initialize database connection with proper pool configuration
DATABASE_URL = settings.DATABASE_URL
db = databases.Database(
    DATABASE_URL,
    min_size=5,
    max_size=20
)


metadata = MetaData()

#  tables
stake_transactions = Table(
    "stake_transactions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("netuid", Integer, nullable=False),
    Column("hotkey", String(255), nullable=False),
    Column("sentiment_score", Integer, nullable=False),
    Column("amount", Float, nullable=False),
    Column("action", String(50), nullable=False),  # 'stake' or 'unstake'
    Column("status", String(50), nullable=False),  # 'pending', 'completed', 'failed'
    Column("tx_hash", String(255), nullable=True),
    Column("error", Text, nullable=True),
    Column("created_at", DateTime, default=datetime.datetime.now()),
    Column("updated_at", DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now())
)

dividend_queries = Table(
    "dividend_queries",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("netuid", Integer, nullable=False),
    Column("hotkey", String(255), nullable=False),
    Column("dividend", Float, nullable=False),
    Column("cached", Boolean, nullable=False, default=False),
    Column("query_time", DateTime, default=datetime.datetime.now())
)

# Helper classess
class StakeTransaction:
    @classmethod
    async def create(cls, **kwargs):
        async with db.transaction():
            query = stake_transactions.insert().values(**kwargs)
            return await db.execute(query)
    
    @classmethod
    async def get(cls, tx_id: int):
        query = stake_transactions.select().where(stake_transactions.c.id == tx_id)
        return await db.fetch_one(query)
    
    @classmethod
    async def list(cls, limit: int = 100, offset: int = 0):
        query = stake_transactions.select().order_by(stake_transactions.c.created_at.desc()).limit(limit).offset(offset)
        return await db.fetch_all(query)
    
    @classmethod
    async def list_by_hotkey(cls, hotkey: str, limit: int = 100, offset: int = 0):
        query = stake_transactions.select().where(stake_transactions.c.hotkey == hotkey).order_by(stake_transactions.c.created_at.desc()).limit(limit).offset(offset)
        return await db.fetch_all(query)


class DividendQuery:
    @classmethod
    async def create(cls, **kwargs):
        async with db.transaction():
            query = dividend_queries.insert().values(**kwargs)
            return await db.execute(query)
    
    @classmethod
    async def list_recent(cls, limit: int = 100):
        query = dividend_queries.select().order_by(dividend_queries.c.query_time.desc()).limit(limit)
        return await db.fetch_all(query)
    
    @classmethod
    async def list_by_hotkey(cls, hotkey: str, limit: int = 100):
        query = dividend_queries.select().where(dividend_queries.c.hotkey == hotkey).order_by(dividend_queries.c.query_time.desc()).limit(limit)
        return await db.fetch_all(query)



# Create tables if they don't exist - using async pattern
async def create_tables():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)