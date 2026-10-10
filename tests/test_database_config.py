from unittest.mock import patch
from app.db.session import database

def test_neon_url_uses_psycopg_and_preserves_tls():
    for prefix in ['postgres://', 'postgresql://', 'postgresql+psycopg://']:
        url = prefix + 'user:placeholder@ep-example-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
        with patch('app.db.session.create_engine') as create:
            database(url)
            args, options = create.call_args
            assert args[0].startswith('postgresql+psycopg://')
            assert args[0].endswith('?sslmode=require&channel_binding=require')
            assert options['connect_args']['prepare_threshold'] is None
            assert options['connect_args']['connect_timeout'] == 10
            assert options['pool_pre_ping'] is True
            assert options['pool_size'] == 2
