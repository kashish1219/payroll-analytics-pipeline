import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import get_db
import models

TEST_DATABASE_URL = "sqlite:///:memory:"
@pytest.fixture(name="db_session", scope="function")
def db_session_fixture():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args = {"check_same_thread": False}, 
        poolclass = StaticPool
    )

    models.Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        models.Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client", scope="function")
def client_fixture(db_session):

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    

    app.dependency_overrides[get_db] = _override_get_db
    
    yield TestClient(app)

    app.dependency_overrides.clear()