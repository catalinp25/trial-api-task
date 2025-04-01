from typing import Callable, AsyncGenerator
from src.db.models import db


async def get_database():
    """
    Database dependency that ensures the database is connected for the request.
    """
    if not db.is_connected:
        await db.connect()
    try:
        yield db
    finally:
        pass

Database = Callable[[], AsyncGenerator[db.__class__, None]]
