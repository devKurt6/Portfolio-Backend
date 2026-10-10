# Portfolio API

For persistent notes using Neon PostgreSQL Free, follow [NEON_SETUP.md](NEON_SETUP.md). Render's DATABASE_URL is now supplied privately in the dashboard/Blueprint prompt; local development still defaults to SQLite.

Upload **the contents of this folder** into your backend GitHub repository. `render.yaml`, `requirements.lock`, `start.py`, and this README must be at the repository root. The backend is self-contained; it does not read files from the separate frontend repository.

Windows PowerShell, from this folder:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock
.venv/Scripts/python.exe setup_local.py
.venv/Scripts/python.exe start.py
```

macOS/Linux:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python setup_local.py
.venv/bin/python start.py
```

`setup_local.py` creates ignored random local secrets without overwriting existing configuration. **`python start.py`** performs migrations, synchronizes projects by slug, and serves port 8000 (or `PORT`). Project seed snapshots in `app/content/` originate from the frontend's real content; update these copies separately when changing content. Each startup adds new slugs and updates listed project fields for existing slugs. Existing IDs, publication status, year, unlisted projects, and all wall/contact records are preserved. No sample wall messages are added.

## Render Git deployment

Connect **this backend repository** to Render. Create a Blueprint using `render.yaml` at the repository root; its root directory is intentionally blank. For manual web-service setup: runtime Python, root directory **blank**, build `pip install -r requirements.lock`, start `python start.py`, health check `/api/health`. The Blueprint generates private admin/IP secrets. Keep `ALLOWED_ORIGINS=https://kurt-profile.netlify.app` and the supplied site-specific deploy-preview regex. Copy the service's HTTPS URL into the frontend repository's Netlify `PORTFOLIO_API_BASE_URL` build variable.

Free Render SQLite storage is ephemeral: wall/comments/contact data can disappear on restart/redeploy, and only real projects are reseeded. For lasting data, use a paid persistent disk mounted at `/var/data` with `DATABASE_URL=sqlite:////var/data/portfolio.db`, or PostgreSQL. Keep one worker and configure trusted proxy addresses for real-client IP throttling. See [Render free limits](https://render.com/docs/free), [persistent disks](https://render.com/docs/disks), and configuration below.

The `.gitignore` excludes `.env`, `.venv`, local database data, Python caches, and test caches. Use Git so exclusions apply; omit these manually if uploading through GitHub's browser. Keep `.env.example` and the project/bio seed snapshots in the upload.

Tests: `.venv/Scripts/python.exe -m pytest tests -q` on Windows, or `.venv/bin/python -m pytest tests -q` on macOS/Linux. Tests use disposable databases.

Dependencies: FastAPI for REST routing; SQLAlchemy for the portable ORM; Alembic for migrations; Pydantic and pydantic-settings for validation/environment configuration; SlowAPI for throttling; uvicorn for serving; psycopg binary for PostgreSQL; email-validator for email checks; pytest and httpx for tests. `requirements.lock` freezes the tested versions. No dependency was added for separating repositories.

## Configuration

`DATABASE_URL` defaults to `sqlite:///./data/portfolio.db`. `ADMIN_TOKEN` and `IP_HASH_SALT` are required separate private secrets, minimum 32 characters; placeholder secrets fail startup. `ALLOWED_ORIGINS` is a comma-separated exact-origin list without wildcard. `PREVIEW_ORIGIN_REGEX` is optional and should stay anchored to your own site. Limits: `WALL_POST_SECONDS=15`, `WALL_DAILY_CAP=30` (UTC calendar day), `WALL_REPORT_THRESHOLD=3`, `MAX_BODY_BYTES=16384`. Optional chat logging defaults off (`ENABLE_CHAT_LOGS=false`). `LLM_ENABLED=false`, `LLM_API_KEY`, and `LLM_MODEL` reserve a future provider interface; enabling an unimplemented provider fails configuration rather than silently sending requests.

Rate limits use salted IP hashes, never raw addresses in tables. Only trust forwarded client headers from configured proxy addresses. `FORWARDED_ALLOW_IPS` defaults to loopback; `PORT` defaults 8000. In-memory request throttles require one worker/instance; before scaling, add a shared SlowAPI storage backend and test on PostgreSQL. A portable singleton `wall_post_gate` write lock serializes posting-quota checks even before an IP's first message. SQLite transactions serialize the tested post/like/report operations; PostgreSQL like/report parent rows are locked. Do not deploy multiple workers with the current in-memory request limiter.

## Contracts

All API responses are JSON. Errors: `{"error":{"code":"validation_error","message":"..."}}`; HTTP 400/401/404/413/422/429/500 use the same shape. 429 includes exposed `Retry-After`. Public endpoints:

| Method/path | Behavior |
| --- | --- |
| GET `/api/health` | Database health |
| GET `/api/projects?category=&q=` | Published projects matching frontend `Project` fields |
| GET `/api/projects/{slug}` | Project or JSON 404 |
| GET `/api/freedom-wall/messages?sort=new&limit=6&offset=0` | `{items,total,nextOffset}`; sort `new` or `top`, limit 1–50 |
| POST `/api/freedom-wall/messages` | `{name,text,emoji?,website?}` → frontend wall message |
| POST `/api/freedom-wall/messages/{id}/like` | Toggle once per visitor per call; returns updated wall message |
| POST `/api/freedom-wall/messages/{id}/report` | `{reason?}` → `{ok:true}` |
| POST `/api/contact` | `{name,email,message,website?}` → `{ok:true}`; store only, no email |
| POST `/api/chat` | `{message,session_id?}` → `{reply}`; deterministic project/bio grounding |

Wall writes require `X-Visitor-Id` with a UUID. Browser localStorage persists it, falling back to memory if unavailable. The server stores a salted hash of the visitor ID. Public reads include only approved messages plus that visitor's pending ones; rejected/hidden records never leak through public writes. Plain text stays plain text; the UI uses textContent for wall content. Name 2–24 and message 3–300 normalized characters; emoji uses the existing frontend allow-list. Configurable profanity list: `app/services/profanity.json`. Links in names/messages require moderation. Filled honeypot returns fake success without storing. Post interval and daily quotas are enforced against stored records in addition to request throttles. Contact 3/hour, chat 20/minute, likes 60/minute, reports 10/hour.

Reports are unique by salted **IP**, protecting against trivial anonymous-ID rotation. The reporting IP no longer sees the note, and three distinct reporting IPs auto-hide it. Shared NAT users count as one reporter and share post quotas. Anonymous UUIDs are pseudonymous ownership, not authenticated identity: clearing storage loses pending-note visibility and like identity, and anyone knowing the UUID can impersonate it. This is an anonymous wall, not an account system. Admin review includes hidden messages.

## Admin

Use a private terminal, never browser/public config. Every admin request needs `Authorization: Bearer <ADMIN_TOKEN>`; comparison is constant time. GET `/api/admin/wall/pending` returns up to 100 pending/hidden notes. POST `/api/admin/wall/{id}/approve`, `/reject`, `/hide` moderates one. GET `/api/admin/contact` returns latest 100 stored contact records. No email is sent: `services/chat_service.py:notify_contact` is the future provider hook. With the selected legacy contact mode, new site contact submissions go to Netlify Forms rather than this table.

Example (replace placeholders privately):

```sh
curl -H 'Authorization: Bearer YOUR_PRIVATE_TOKEN' https://YOUR-SERVICE.onrender.com/api/admin/wall/pending
curl -X POST -H 'Authorization: Bearer YOUR_PRIVATE_TOKEN' https://YOUR-SERVICE.onrender.com/api/admin/wall/123/approve
```

Keep the IP salt stable; rotating it changes ownership/report hashes and resets IP quota associations. Avoid storing chat logs unless needed. Back up persistent data before changes.

## PostgreSQL migration

1. Stop writes and back up SQLite. Provision PostgreSQL and preserve the old database until verification.
2. psycopg binary is already installed. Set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require` privately. Render's `postgres://`/`postgresql://` forms are normalized automatically. URL credentials must be percent-encoded.
3. Run `python -m alembic upgrade head` against the empty PostgreSQL database. Run `python seed.py` only if you want fresh project seeds. **Changing the URL does not copy existing records.**
4. To preserve existing data, export and import every table with a reviewed data-transfer script/tool in foreign-key order: projects, wall_messages, contact_messages, chat_logs, wall_likes, wall_reports. Preserve IDs, JSON arrays, UTC timestamps, status/counters, salts, and ownership hashes. Reset PostgreSQL sequences after importing IDs. Compare row counts, foreign keys, likes/report counts, and project content before enabling writes. No automatic cross-database data transfer is included.
5. Update Render's private URL, deploy one worker, verify health/admin/wall, then resume writes. For multiple workers/instances, add shared limiter storage and verify quota transactions first.

The frozen initial Alembic migration uses portable types and explicit tables. For future schema changes, add new migration revisions; do not edit the already-deployed initial revision. SQLite free-tier data loss and paid disk options are described in the root README.


## Add or update a project

1. Add a project object to `app/content/projects.json`, inside the array. Use a unique lowercase slug such as `face-recognition`. Keep the same slug to update the same project; changing the slug creates a separate record.
2. Push the updated JSON **and the new seed.py implementation** to your backend repository. Render must successfully redeploy/start using `python start.py`; startup now imports additions and updates automatically. A push alone does not change a currently running process if auto-deploy is disabled.
3. Add the matching project to the separate frontend repository's `data/projects.json`, including its image, and deploy Netlify to generate the detail page. Keep the slug/title/details consistent.
4. Check `/api/projects/your-slug`, then open the frontend project page.

For an immediate local database sync from this folder: `python seed.py` (with your configured interpreter). It prints counts like `{'added': 1, 'updated': 0}`. Existing database data is not cleared. Missing projects are not deleted; removing a JSON object does not unpublish a previously imported project. Set publication status in the database deliberately if needed.

Invalid source data or duplicate slugs fail before database changes are committed. JSON is authoritative for the listed project's content fields on subsequent startup; direct database edits to those fields are overwritten by the JSON. Publication status and year remain database-managed. Render free-tier storage loss is still a platform limitation, independent of this sync change.
