from alembic import context
from app.core.config import Settings
from app.db.session import database
from app.db.base import Base
import app.models

engine, _ = database(Settings().database_url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
