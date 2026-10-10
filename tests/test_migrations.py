from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, func
from app.db.session import database
from app.models import Project, WallMessage, WallPostGate
from seed import seed

def test_real_migration_and_seed_idempotent(tmp_path, monkeypatch):
    url='sqlite:///'+(tmp_path/'migrations.db').as_posix()
    monkeypatch.setenv('DATABASE_URL',url)
    monkeypatch.setenv('ADMIN_TOKEN','a'*48)
    monkeypatch.setenv('IP_HASH_SALT','s'*48)
    config=Config(str(Path(__file__).parents[1]/'alembic.ini'))
    command.upgrade(config,'head')
    command.upgrade(config,'head')
    engine,sessions=database(url)
    seed(sessions);seed(sessions)
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Project))==7
        assert db.scalar(select(func.count()).select_from(WallMessage))==0
        assert db.get(WallPostGate,1) is not None
    assert 'alembic_version' in inspect(engine).get_table_names()
    engine.dispose()
