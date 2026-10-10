from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from fastapi import Request

def database(url):
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    parsed = make_url(url)
    sqlite = parsed.get_backend_name() == 'sqlite'
    if sqlite and parsed.database and parsed.database != ':memory:':
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    options = {'pool_pre_ping': True}
    if sqlite:
        options['connect_args'] = {'check_same_thread': False, 'timeout': 30}
    elif parsed.get_backend_name() == 'postgresql':
        # Small pool for the portfolio; disable automatic prepared statements
        # for compatibility with transaction-pooling connection URLs.
        options.update(connect_args={'connect_timeout': 10, 'prepare_threshold': None},
                       pool_size=2, max_overflow=3, pool_timeout=15, pool_recycle=300)
    engine = create_engine(url, **options)
    if sqlite:
        @event.listens_for(engine, 'connect')
        def pragmas(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return engine, sessionmaker(engine, expire_on_commit=False)

def get_db(request: Request):
    with request.app.state.sessions() as session:
        yield session
