"""
conftest.py — shared test fixtures.

Uses SQLite in-memory database so tests run without a real PostgreSQL
instance. The same ORM models work on both SQLite (tests) and
PostgreSQL (production) via SQLAlchemy's dialect abstraction.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, MagicMock, patch

# SQLite in-memory — no Postgres required for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    from app.models.db_models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine):
    """Per-test DB session with auto-rollback to keep tests isolated."""
    async_session = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_db):
    """Test client with DB dependency overridden to use test SQLite session."""
    from app.main import app
    from app.db.database import get_db

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    # Mock ML engines so tests don't need model artifacts on disk
    mock_engine = MagicMock()
    mock_engine.loaded = False
    mock_engine.get_similar_products = MagicMock(return_value=[])
    mock_engine.search_by_text = MagicMock(return_value=[])
    mock_engine.get_recommendations = MagicMock(return_value=[])
    mock_engine.get_ab_variant = MagicMock(return_value="control")

    with patch("app.ml.collaborative.cf_engine.get_cf_engine", return_value=mock_engine), \
         patch("app.ml.content.cbf_engine.get_cbf_engine", return_value=mock_engine), \
         patch("app.ml.ranker.hybrid_ranker.get_ranker", return_value=mock_engine):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()
