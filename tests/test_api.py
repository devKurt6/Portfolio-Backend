from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.models import WallMessage, WallLike, ContactMessage

WALL = '/api/freedom-wall/messages'
def post(client, **kwargs):
    return client.post(WALL, json=dict(name='Visitor', text='Hello everyone', emoji='👋', **kwargs))

def test_projects(client):
    rows = client.get('/api/projects').json()
    assert len(rows) == 7
    assert rows[0]['slug'] == 'embedded-plate-recognition'
    assert client.get('/api/projects/' + rows[0]['slug']).json() == rows[0]
    assert len(client.get('/api/projects', params={'q':'Flask'}).json()) > 0
    assert client.get('/api/projects/missing').status_code == 404
    assert client.get('/api/health').json() == {'status':'ok'}

def test_empty_wall(client):
    assert client.get(WALL).json() == {'items':[], 'total':0, 'nextOffset':0}

def test_validation(client):
    for payload in [{'name':'A','text':'abc'}, {'name':'Visitor','text':'x'*301}, {'name':'Visitor','text':'hi'}, {'name':'Visitor','text':'hello','emoji':'<script>'}]:
        response = client.post(WALL,json=payload)
        assert response.status_code == 422
        assert 'error' in response.json()

def test_honeypot(client, app):
    assert client.post(WALL, json={'website':'spam'}).status_code == 200
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(WallMessage)) == 0

def test_profanity(client):
    response = client.post(WALL,json={'name':'Visitor','text':'You are an idiot'})
    assert response.status_code == 422
    assert 'respectful' in response.json()['error']['message']

def test_pending_ownership(client, app):
    row = client.post(WALL,json={'name':'Visitor','text':'Look at example.com'}).json()
    assert row['status'] == 'pending'
    assert client.get(WALL).json()['total'] == 1
    with TestClient(app, headers={'X-Visitor-Id':str(uuid4())}) as other:
        assert other.get(WALL).json()['total'] == 0
        assert other.post(WALL+'/'+row['id']+'/like').status_code == 404
    assert client.post('/api/admin/wall/'+row['id']+'/approve', headers={'Authorization':'Bearer '+'a'*48}).status_code == 200
    assert client.get(WALL).json()['items'][0]['status'] == 'published'

def test_normalize_and_ip_privacy(client, app):
    row = client.post(WALL,json={'name':'  Kurt\tDecena ','text':' Hello\n world\u0000! '}).json()
    assert row['text'] == 'Hello world!'
    with app.state.sessions() as db:
        stored = db.get(WallMessage,int(row['id']))
        assert len(stored.ip_hash) == 64
        assert '192.0.2.1' not in stored.ip_hash

def test_cooldown_and_daily(client, app):
    assert post(client).status_code == 200
    response = post(client)
    assert response.status_code == 429 and 1 <= int(response.headers['Retry-After']) <= 15
    app.state.settings.wall_post_seconds = 1
    app.state.settings.wall_daily_cap = 1
    from datetime import timedelta
    with app.state.sessions() as db:
        row=db.scalar(select(WallMessage)); row.created_at -= timedelta(seconds=16); db.commit()
    assert post(client).status_code == 429

def test_like_toggle_unique(client, app):
    row=post(client).json(); path=WALL+'/'+row['id']+'/like'
    assert client.post(path).json()['likes'] == 1
    assert client.post(path).json()['likes'] == 0
    assert client.post(path).json()['likes'] == 1
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(WallLike)) == 1

def test_concurrent_likes(client, app):
    row=post(client).json(); path=WALL+'/'+row['id']+'/like'
    def like(i):
        with TestClient(app, client=(f'192.0.2.{i+10}',5000), headers={'X-Visitor-Id':str(uuid4())}) as c:
            return c.post(path).status_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(like,range(8))) == [200]*8
    assert client.get(WALL).json()['items'][0]['likes'] == 8

def test_reports_unique_and_threshold(client, app):
    row=post(client).json(); path=WALL+'/'+row['id']+'/report'
    assert client.post(path,json={}).status_code == 200
    assert client.post(path,json={}).status_code == 200
    assert client.get(WALL).json()['total'] == 0
    with app.state.sessions() as db:
        assert db.get(WallMessage,int(row['id'])).report_count == 1
    for ip in ['192.0.2.2','192.0.2.3']:
        with TestClient(app, client=(ip,5000), headers={'X-Visitor-Id':str(uuid4())}) as other:
            assert other.post(path,json={}).status_code == 200
    with app.state.sessions() as db:
        assert db.get(WallMessage,int(row['id'])).status == 'hidden'

def test_contact(client, app):
    assert client.post('/api/contact',json={'name':'Kurt','email':'invalid','message':'short'}).status_code == 422
    payload={'name':'Kurt','email':'kurt@example.com','message':'Hello from a test.'}
    for _ in range(3):
        assert client.post('/api/contact',json=payload).status_code == 200
    assert client.post('/api/contact',json=payload).status_code == 429
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(ContactMessage)) == 3

def test_admin(client):
    for path in ['/api/admin/wall/pending','/api/admin/contact']:
        assert client.get(path).status_code == 401
        assert client.get(path,headers={'Authorization':'Bearer wrong'}).status_code == 401
        assert client.get(path,headers={'Authorization':'Bearer '+'a'*48}).status_code == 200

def test_cors_and_security(client):
    for origin in ['https://kurt-profile.netlify.app','https://deploy-preview-12--kurt-profile.netlify.app']:
        response=client.options(WALL,headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'X-Visitor-Id,Content-Type'})
        assert response.headers['Access-Control-Allow-Origin'] == origin
    assert 'Access-Control-Allow-Origin' not in client.get(WALL,headers={'Origin':'https://evil.example'}).headers
    assert client.get(WALL).headers['X-Content-Type-Options'] == 'nosniff'
    assert client.post(WALL,content='x'*17000).status_code == 413

def test_chat(client, app):
    response=client.post('/api/chat',json={'message':'What projects has Kurt built?'})
    assert response.status_code == 200 and 'Embedded System' in response.json()['reply']
    assert client.post('/api/chat',json={'message':'x'*1001}).status_code == 422
