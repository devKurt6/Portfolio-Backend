from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.models import WallMessage, ContactMessage, ChatLog

def test_concurrent_posts_enforce_interval(app):
    def post(_):
        with TestClient(app, client=('192.0.2.90',5000),headers={'X-Visitor-Id':str(uuid4())}) as c:
            return c.post('/api/freedom-wall/messages',json={'name':'Visitor','text':'Concurrent first post'}).status_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses=list(pool.map(post,range(4)))
    assert sorted(statuses) == [200,429,429,429]

def test_sort_and_pagination(client, app):
    with app.state.sessions() as db:
        for i in range(8):
            db.add(WallMessage(display_name='Visitor',content=f'Note {i}',emoji='',like_count=i,status='approved',ip_hash='a'*64,visitor_hash='b'*64))
        db.commit()
    first=client.get('/api/freedom-wall/messages?sort=top').json()
    assert first['total']==8 and first['nextOffset']==6
    assert first['items'][0]['likes']==7
    second=client.get('/api/freedom-wall/messages?sort=top&offset=6').json()
    assert len(second['items'])==2 and second['nextOffset']==8
    assert not set(x['id'] for x in first['items']) & set(x['id'] for x in second['items'])

def test_contact_honey_and_chat_logs_off(client, app):
    assert client.post('/api/contact',json={'name':'Visitor','email':'v@example.com','message':'Honeypot filled','website':'spam'}).status_code==200
    client.post('/api/chat',json={'message':'What are your skills?'})
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(ContactMessage)) == 0
        assert db.scalar(select(func.count()).select_from(ChatLog)) == 0

def test_invalid_visitor_and_sort(client):
    assert client.post('/api/freedom-wall/messages',headers={'X-Visitor-Id':'invalid'},json={'name':'Visitor','text':'Hello there'}).status_code==400
    assert client.get('/api/freedom-wall/messages?sort=invalid').status_code==422
