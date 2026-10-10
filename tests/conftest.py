import sys
from pathlib import Path
from uuid import uuid4
import pytest
sys.path.insert(0, str(Path(__file__).parents[1]))
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings
from app.core.security import limiter
from app.db.base import Base
from seed import seed

@pytest.fixture
def app(tmp_path):
    limiter._storage.reset()
    application = create_app(Settings(_env_file=None, database_url='sqlite:///' + (tmp_path/'test.db').as_posix(), admin_token='a'*48, ip_hash_salt='s'*48,
                                     allowed_origins='https://kurt-profile.netlify.app', preview_origin_regex=r'^https://deploy-preview-[0-9]+--kurt-profile\.netlify\.app$'))
    Base.metadata.create_all(application.state.engine)
    seed(application.state.sessions)
    yield application
    application.state.engine.dispose()

@pytest.fixture
def client(app):
    with TestClient(app, client=('192.0.2.1', 5000), headers={'X-Visitor-Id': str(uuid4())}) as c:
        yield c
