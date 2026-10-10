import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from app.core.config import Settings
from app.core.security import limiter
from app.db.session import database
from app.routers import projects, freedom_wall, contact, chat, admin, health

def create_app(settings=None):
    settings = settings or Settings()
    app = FastAPI(title='Kurt Portfolio API', docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.engine, app.state.sessions = database(settings.database_url)
    app.state.limiter = limiter
    for module in (projects, freedom_wall, contact, chat, admin, health):
        app.include_router(module.router)

    def error(status, code, message, headers=None):
        return JSONResponse({'error': {'code': code, 'message': message}}, status_code=status, headers=headers)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return error(exc.status_code, f'http_{exc.status_code}', str(exc.detail), exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        message = '; '.join(e['msg'].removeprefix('Value error, ') for e in exc.errors())
        return error(422, 'validation_error', message)

    @app.exception_handler(RateLimitExceeded)
    async def rate_error(request, exc):
        return error(429, 'rate_limited', 'Too many requests. Please try again later.', {'Retry-After': '3600' if 'hour' in exc.detail else '60'})

    @app.exception_handler(Exception)
    async def server_error(request, exc):
        logging.error('API request failed: %s', type(exc).__name__)
        return error(500, 'server_error', 'The service could not complete your request. Please try again.')

    @app.middleware('http')
    async def security(request: Request, call_next):
        # Buffer at most MAX_BODY_BYTES, including chunked requests.
        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > settings.max_body_bytes:
                return error(413, 'body_too_large', 'Request body is too large.')
            chunks.append(chunk)
        body = b''.join(chunks)
        request._body = body
        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        request._receive = receive
        try:
            response = await call_next(request)
        except Exception as exc:
            logging.error('API request failed: %s', type(exc).__name__)
            response = error(500, 'server_error', 'The service could not complete your request. Please try again.')
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        return response

    app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.allowed_origins.split(',') if x.strip()],
                       allow_origin_regex=settings.preview_origin_regex, allow_methods=['GET', 'POST'],
                       allow_headers=['Content-Type', 'X-Visitor-Id', 'Authorization'], expose_headers=['Retry-After'])
    return app

# Factory used by uvicorn: app.main:create_app --factory
