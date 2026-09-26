import os

os.environ.setdefault("SECAI_ENV", "test")
os.environ.setdefault("SECAI_WEB_ORIGIN", "http://localhost:3000")

from collections.abc import AsyncIterator

import fakeredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.scanning.queue import get_enqueue

ORIGIN = "http://localhost:3000"
# Set SECAI_TEST_DATABASE_URL to run the suite against Postgres (CI does).
TEST_DB_URL = os.environ.get("SECAI_TEST_DATABASE_URL", "sqlite+aiosqlite://")


@pytest.fixture
async def app():
    engine_kwargs = {"poolclass": StaticPool} if TEST_DB_URL.startswith("sqlite") else {}
    engine = create_async_engine(TEST_DB_URL, **engine_kwargs)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_db() -> AsyncIterator:
        async with sessionmaker() as session:
            yield session

    application = create_app()
    application.state.redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    application.dependency_overrides[get_db] = _get_db
    application.state.sessionmaker = sessionmaker
    application.state.enqueued = []

    def _get_enqueue():
        async def enqueue(name, *args):
            application.state.enqueued.append((name, *args))

        return enqueue

    application.dependency_overrides[get_enqueue] = _get_enqueue
    yield application
    await engine.dispose()


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"Origin": ORIGIN}
    ) as c:
        yield c


@pytest.fixture
def make_client(app):
    """Build extra independent clients (separate cookie jars)."""

    def _make() -> AsyncClient:
        return AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers={"Origin": ORIGIN}
        )

    return _make
