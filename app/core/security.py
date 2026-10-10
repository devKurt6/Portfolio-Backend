import hashlib
import hmac
from uuid import UUID
from fastapi import HTTPException, Request
from slowapi import Limiter

def digest(request, value):
    return hmac.new(request.app.state.settings.ip_hash_salt.encode(), value.encode(), hashlib.sha256).hexdigest()

def ip_hash(request):
    return digest(request, 'ip:' + (request.client.host if request.client else 'unknown'))

limiter = Limiter(key_func=ip_hash, headers_enabled=False)

def visitor(request, required=True):
    value = request.headers.get('X-Visitor-Id', '')
    if not value and not required:
        return ''
    try:
        UUID(value)
    except ValueError:
        raise HTTPException(400, 'A valid anonymous visitor ID is required.')
    return digest(request, 'visitor:' + value)

def admin(request: Request):
    value = request.headers.get('Authorization', '')
    expected = 'Bearer ' + request.app.state.settings.admin_token
    if not hmac.compare_digest(value.encode(), expected.encode()):
        raise HTTPException(401, 'Admin authentication required.', headers={'WWW-Authenticate': 'Bearer'})
