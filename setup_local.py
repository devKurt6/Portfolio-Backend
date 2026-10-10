"""Generate ignored local secrets without printing them or overwriting .env."""
from pathlib import Path
import secrets
path = Path(__file__).with_name('.env')
if not path.exists():
    path.write_text('ADMIN_TOKEN=' + secrets.token_urlsafe(48) + '\nIP_HASH_SALT=' + secrets.token_urlsafe(48) + '\n', encoding='utf-8')
print('Local configuration ready. Run python start.py from backend/.')
