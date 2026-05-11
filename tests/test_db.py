import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import DATABASE_URL

def _engine():
    """Fresh engine per test — no shared pool, no cross-loop issues."""
    return create_async_engine(DATABASE_URL, pool_pre_ping=False).begin()

@pytest.mark.anyio
async def test_1_database_connects():
    """Engine can open a connection and run a query."""
    async with _engine() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.anyio
async def test_2_string_expression_query():
    """Connection can return a string value."""
    async with _engine() as conn:
        result = await conn.execute(text("SELECT 'evenup'"))
        assert result.scalar() == "evenup"


@pytest.mark.anyio
async def test_3_arithmetic_query():
    """Connection correctly evaluates SQL arithmetic."""
    async with _engine() as conn:
        result = await conn.execute(text("SELECT 1 + 1"))
        assert result.scalar() == 2


@pytest.mark.anyio
async def test_4_multiple_queries_same_connection():
    """Multiple queries work within the same connection."""
    async with _engine() as conn:
        r1 = await conn.execute(text("SELECT 1"))
        r2 = await conn.execute(text("SELECT 2"))
        assert r1.scalar() == 1
        assert r2.scalar() == 2


@pytest.mark.anyio
async def test_5_current_timestamp_returns_value():
    """NOW() returns a non-null value."""
    async with _engine() as conn:
        result = await conn.execute(text("SELECT NOW()"))
        assert result.scalar() is not None

