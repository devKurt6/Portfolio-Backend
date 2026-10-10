import os
from pathlib import Path
from alembic.config import Config
from alembic import command
from app.core.config import Settings
from app.db.session import database
from seed import seed

if __name__ == '__main__':
    os.chdir(Path(__file__).parent)
    settings = Settings()
    command.upgrade(Config('alembic.ini'), 'head')
    engine, sessions = database(settings.database_url)
    seed(sessions)
    engine.dispose()
    import uvicorn
    uvicorn.run('app.main:create_app', factory=True, host='0.0.0.0', port=int(os.environ.get('PORT', '8000')),
                access_log=False, proxy_headers=True, forwarded_allow_ips=os.environ.get('FORWARDED_ALLOW_IPS', '127.0.0.1'))
