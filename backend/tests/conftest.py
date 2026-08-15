import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock, patch

# Patch data ingestion and embeddings BEFORE importing app to prevent
# sentence-transformers / ChromaDB from loading during tests
with patch("src.data_ingestion.run_ingestion", return_value=None):
    from src.api.main import app

from src.auth.password import hash_password
from src.database import Base, get_db
from src.models.user import User, UserRole

# In-memory SQLite with StaticPool so all connections share the same DB
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_tables():
    """Truncate all tables before each test."""
    yield
    db = TestSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


@pytest.fixture
def db_session():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = override_get_db
    # Suppress lifespan data ingestion and embedding model loading during tests
    with patch("src.api.main.run_ingestion", return_value=None):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("Admin@123"),
        full_name="Test Admin",
        role=UserRole.admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def engineer_user(db_session):
    user = User(
        email="engineer@test.com",
        hashed_password=hash_password("Engineer@123"),
        full_name="Test Engineer",
        role=UserRole.engineer,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(client, admin_user):
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin@test.com", "password": "Admin@123"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def engineer_token(client, engineer_user):
    resp = client.post(
        "/api/auth/login",
        data={"username": "engineer@test.com", "password": "Engineer@123"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def mock_llm():
    """Mock LLM calls to avoid API costs during tests."""
    mock_response = MagicMock()
    mock_response.content = (
        '{"diagnosis": "Bearing wear detected", "root_cause": "Insufficient lubrication", '
        '"recommended_action": "Replace LP shaft bearing", "confidence_score": 0.92, '
        '"severity": "CRITICAL"}'
    )
    with patch("src.agents.nodes._get_llm") as mock_get_llm:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm_instance
        yield mock_llm_instance
