"""Read-only connection check. Never prints database credentials."""
from pathlib import Path
import os
from sqlalchemy import text
from app.core.config import Settings
from app.db.session import database

if __name__ == '__main__':
    os.chdir(Path(__file__).parent)
    engine = None
    try:
        engine, _ = database(Settings().database_url)
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        print('Database connection OK (' + engine.dialect.name + ').')
    except Exception as exc:
        print('Database check failed (' + type(exc).__name__ + '). Check your private DATABASE_URL, credentials, TLS parameters, and network access.')
        raise SystemExit(1)
    finally:
        if engine is not None:
            engine.dispose()
