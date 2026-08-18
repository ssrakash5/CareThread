import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import settings

# The default suite never touches AWS/Bedrock, regardless of what backend/.env
# has ai_provider set to; the opt-in @pytest.mark.bedrock tests switch it back.
settings.ai_provider = "local"

from app.db import SessionLocal, engine, Base, ensure_vector_support  # noqa: E402
from app.main import app  # noqa: E402

# FK-safe delete order (children before parents), mirrors seed.py's cleanup list.
TABLES = [
    "thread_events", "proposed_actions", "thread_evidence", "care_threads",
    "findings", "facts", "artifact_chunks", "artifacts",
    "family_chat_messages", "patient_chat_messages", "family_relationships",
    "patients", "family_groups",
]


@pytest.fixture(scope="session", autouse=True)
def _schema():
    ensure_vector_support()
    # Demo database, no migrations (mirrors seed.py): drop + recreate so model
    # changes (e.g. a new column) always match what the tests run against.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    session = SessionLocal()
    try:
        for table in TABLES:
            session.execute(text(f"DELETE FROM {table}"))
        session.commit()
    finally:
        session.close()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-User-Id": "dr_kapoor", "X-User-Role": "CLINICIAN"})
        yield c
