import pytest
from sqlalchemy import create_engine,event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.db.database import Base,get_db
from app.main import create_app
from app.core.config import get_settings

@pytest.fixture
def test_db(tmp_path,monkeypatch):
    # SQLite is a test double only. Application configuration always constructs a MySQL URL.
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    @event.listens_for(engine,'connect')
    def foreign_keys(connection,_): connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,expire_on_commit=False)
    s=get_settings()
    monkeypatch.setattr(s,'default_provider','mock')
    monkeypatch.setattr(s,'enable_mock',True)
    monkeypatch.setattr(s,'storage_dir',tmp_path/'storage')
    yield factory
    engine.dispose()

@pytest.fixture
def client(test_db):
    app=create_app(initialize_database=False)
    def override():
        with test_db() as db: yield db
    app.dependency_overrides[get_db]=override
    with TestClient(app) as client: yield client

@pytest.fixture
def session_id(client):
    r=client.post('/api/v1/demo/session',json={'degree':'MCA','subject':'DBMS','topic':'Third Normal Form'})
    assert r.status_code==201,r.text
    return r.json()['session_id']
