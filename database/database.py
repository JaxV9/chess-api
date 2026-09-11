import os
import re
from sqlalchemy import text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from dotenv import load_dotenv

load_dotenv()

raw_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('POSTGRES_PRISMA_URL')
if not raw_url:
    raise ValueError("DATABASE_URL environment variable is not set. Please set DATABASE_URL in Vercel environment variables.")

# Replace postgres:// or postgresql:// with postgresql+psycopg: for async driver compatibility (required by Neon)
if raw_url.startswith(('postgres://', 'postgresql://')):
    DATABASE_URL = re.sub(r'^postgres(ql)?://', 'postgresql+psycopg://', raw_url)
else:
    DATABASE_URL = raw_url

# Create the async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()