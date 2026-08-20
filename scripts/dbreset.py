import asyncio
from database.database import engine
from model.model import Base


async def drop():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✓ All tables dropped.")


asyncio.run(drop())
