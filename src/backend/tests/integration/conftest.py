"""Shared fixtures for tests that need PostgreSQL.

Everything runs inside one transaction in a throwaway schema that is rolled back at the end, so
the target database is left exactly as it was. Tests are skipped if no database is reachable.
"""

import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core import model_registry  # noqa: F401  (registers every table on Base.metadata)
from app.core.config import get_settings
from app.core.database import Base


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    url = os.environ.get("KEYSTONE_TEST_DATABASE_URL") or get_settings().database_url
    if not url:
        pytest.skip("no database configured")

    engine = create_async_engine(url)
    try:
        conn = await engine.connect()
    except Exception as exc:  # pragma: no cover - depends on the environment
        await engine.dispose()
        pytest.skip(f"database unavailable: {type(exc).__name__}")

    trans = await conn.begin()
    # A fresh schema keeps us independent of whatever migrations the database has (or lacks).
    # Postgres DDL is transactional, so the rollback below drops it again.
    schema = f"test_{uuid.uuid4().hex}"
    await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    await conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    await conn.run_sync(Base.metadata.create_all)

    # create_savepoint turns any commit (or rollback) inside the code under test into a
    # savepoint release (or rollback to it), so nothing escapes the outer transaction.
    s = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield s
    finally:
        await s.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()
