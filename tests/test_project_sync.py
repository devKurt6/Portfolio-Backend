import json
from pathlib import Path
import pytest
from sqlalchemy import select, func
from app.models import Project, WallMessage, ContactMessage, WallLike, WallReport
from seed import seed

def test_sync_add_update_idempotent_and_preserves_other_data(app, tmp_path):
    data=json.loads(Path(__file__).parents[1].joinpath('app/content/projects.json').read_text(encoding='utf-8'))
    source=tmp_path/'projects.json'
    with app.state.sessions() as db:
        original=db.scalar(select(Project).where(Project.slug==data[0]['slug']))
        original_id=original.id
        original.is_published=False
        wall=WallMessage(display_name='Visitor',content='Keep my comment',emoji='',ip_hash='a'*64,visitor_hash='b'*64)
        db.add(wall);db.flush()
        db.add_all([WallLike(message_id=wall.id,visitor_id='c'*64),WallReport(message_id=wall.id,reporter_hash='d'*64),ContactMessage(name='Visitor',email='v@example.com',message='Keep this contact',ip_hash='a'*64)])
        db.commit()
    data[0]['title']='Updated project title'
    data.append({**data[-1],'slug':'sync-test-project','title':'New project'})
    source.write_text(json.dumps(data),encoding='utf-8')
    assert seed(app.state.sessions,source)=={'added':1,'updated':1}
    assert seed(app.state.sessions,source)=={'added':0,'updated':0}
    with app.state.sessions() as db:
        row=db.get(Project,original_id)
        assert row.title=='Updated project title' and row.is_published is False
        assert db.scalar(select(Project).where(Project.slug=='sync-test-project')) is not None
        for model in [WallMessage,WallLike,WallReport,ContactMessage]:
            assert db.scalar(select(func.count()).select_from(model))==1
    source.write_text(json.dumps(data[:1]),encoding='utf-8')
    seed(app.state.sessions,source)
    with app.state.sessions() as db:
        assert db.scalar(select(Project).where(Project.slug=='sync-test-project')) is not None

def test_invalid_source_leaves_database_unchanged(app,tmp_path):
    data=json.loads(Path(__file__).parents[1].joinpath('app/content/projects.json').read_text(encoding='utf-8'))
    source=tmp_path/'projects.json'
    for invalid in [data+[data[0]], [{**data[0],'slug':'../unsafe'}], {}]:
        source.write_text(json.dumps(invalid),encoding='utf-8')
        with pytest.raises(ValueError):
            seed(app.state.sessions,source)
        with app.state.sessions() as db:
            assert db.scalar(select(Project).where(Project.slug==data[0]['slug'])).title==data[0]['title']
