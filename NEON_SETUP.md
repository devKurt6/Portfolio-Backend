# Neon PostgreSQL Free — setup para sa portfolio

Frontend: Netlify. Backend API: Render. Database: Neon PostgreSQL. Hindi kailangang baguhin ang frontend framework, chatbot, o contact service. May SQLite pa rin para sa local development. Walang bagong Python dependency: installed na ang `psycopg` driver.

Hindi pa naka-connect ang live backend hangga't hindi mo nilalagay ang actual Neon connection URL sa Render. Walang account/database na nilikha, walang private URL na inilagay sa files, at walang commit/push/deployment na ginawa ng assistant.

## 1. Create your Neon database

1. Open [Neon Console](https://console.neon.tech) and sign up/login.
2. Create a project, for example `kurt-portfolio`, on the **Free** plan. The name is only an example.
3. Choose a region close to your existing Render backend region. Keep the default PostgreSQL version/database/role unless you have a reason to change them. Confirm the free plan before creating.
4. Open the project's **Connect** dialog. Select the main/production branch, database, and role for this portfolio. Keep using the same branch/database across deployments.
5. Copy the **connection string/URI only**, not a shell command such as `psql '...'`. A pooled connection URL has `-pooler` in its hostname and is suitable for the running API. Keep the complete TLS query parameters Neon provides, such as `sslmode=require&channel_binding=require`.

Placeholder example, NOT a working credential:

```text
postgresql://USER:PASSWORD@YOUR-HOST-pooler.REGION.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

Our code automatically selects `postgresql+psycopg` for Neon's `postgresql://` URLs. Do not manually decode/rebuild passwords; use Neon's complete encoded URL. Official [connection guide](https://neon.com/docs/get-started/connect-neon).

## 2. Protect any existing notes before switching

Changing DATABASE_URL does **not** move old SQLite data. Projects are synchronized from backend JSON automatically, but old wall notes/likes/reports/contact records need a separate transfer if you want to keep them.

If existing notes matter, stop here before redeploying/restarting the current SQLite backend and arrange an export while the original service still holds them. Render free storage may already have lost them; lost notes cannot be recovered from project JSON. The backend README describes migration requirements. There is no automatic SQLite-to-Neon transfer in this change.

If you are happy to start with an empty wall, proceed. New notes will be stored in Neon after successful configuration.

## 3. Push backend changes and configure Render

1. Push the updated backend code to its existing GitHub repository, including `app/db/session.py` and `render.yaml`. Do not upload `.env`, `.venv`, or `data/`.
2. Open the existing Render API service → **Environment**.
3. Edit **DATABASE_URL**: replace `sqlite:///./data/portfolio.db` with the complete Neon URI. In the dashboard's value field, paste only the URI: no `DATABASE_URL=` prefix, no `psql`, no surrounding quotes.
4. Retain your existing **ADMIN_TOKEN** and **IP_HASH_SALT** unchanged. Retain CORS settings for your actual Netlify URL. The current repository's Blueprint uses `https://devkurt.netlify.app`; if your live site differs, set `ALLOWED_ORIGINS` and its deploy-preview regex to that site's exact URL/pattern. Do not replace these secrets every deployment.
5. Verify build command `pip install -r requirements.lock`, start command `python start.py`, health check `/api/health`, and blank root directory for the separate backend repository.
6. Save the environment and deploy the latest backend commit. The startup script runs Alembic migrations against Neon, synchronizes projects by slug, and starts FastAPI. Do not run custom SQL to create the same tables manually.

The Blueprint now uses `DATABASE_URL: sync: false` so it does not hard-code SQLite or overwrite your external database choice. New Blueprint setup prompts you for the private URL. For an already existing service, set it directly in the Environment page.

If you use the pooled URL and encounter a migration-specific pooler error, use the **direct** URI from the same Neon branch/database for DATABASE_URL and retry. This portfolio has one small connection pool and can use a direct URI too. Do not switch to a different database/branch accidentally.

## 4. Keep frontend configuration pointing at Render

In Netlify, keep:

```dotenv
PORTFOLIO_API_MODE=live
PORTFOLIO_API_BASE_URL=https://YOUR-EXISTING-API.onrender.com
PORTFOLIO_CONTACT_MODE=legacy
PORTFOLIO_CHAT_MODE=legacy
```

Do not put the Neon URI/password in Netlify public variables, frontend JSON, or browser code. `PORTFOLIO_API_BASE_URL` stays the **Render API URL**, not a Neon URL. Groq remains a Netlify function; contact remains Netlify Forms. No frontend deploy is needed if these values already point at the correct backend.

## 5. Verify persistence

1. Open `https://YOUR-EXISTING-API.onrender.com/api/health`; expect `{"status":"ok"}` after startup.
2. Open `/api/projects`; verify your project list.
3. In Neon Console's Tables view or SQL Editor, inspect `projects`, `wall_messages`, and `alembic_version` in the same branch/database you selected in Connect. This confirms tables exist in Neon; health alone cannot distinguish SQLite from PostgreSQL.
4. Send a harmless test note through the live Freedom Wall. Check it appears in `wall_messages`. A note with a link is pending, so use plain text for this check.
5. Redeploy the Render backend without changing Neon DATABASE_URL. Reload the live wall; that note should still be present. Do not run this test on the old SQLite configuration if there is data to preserve.

Render may sleep and take time to wake; this can delay requests but does not remove separately hosted Neon data. Neon's compute may also scale to zero while its storage persists. Free plans have quotas and may change; this is not a guarantee of free service forever. Check your actual [Neon plan limits](https://neon.com/docs/introduction/plans) and usage in the dashboard. Keep backups for data you care about.

## 6. Optional PyCharm test

You may keep local SQLite while production uses Neon. For a local PostgreSQL test, preferably create a separate Neon development branch/database instead of pointing PyCharm at production wall data.

Put that development Neon URI into ignored `backend/.env`, retaining local admin/IP secrets and allowing your localhost frontend origin. Windows, from the backend folder:

```powershell
.venv/Scripts/python.exe check_database.py
.venv/Scripts/python.exe start.py
```

The read-only connection check reports `Database connection OK (postgresql).` without printing the URI. `start.py` creates/updates tables and synchronizes projects in the selected database, so use a development branch if you do not intend to modify production project content. On macOS/Linux, replace `.venv/Scripts/python.exe` with `.venv/bin/python`.

To return local development to SQLite, restore `DATABASE_URL=sqlite:///./data/portfolio.db` in your local `.env`. Do not change Render's Neon URL.

## Common problems

- Authentication failure: recopy the URI for the correct Neon role; rotate its password only if necessary and update Render afterward.
- SSL/channel binding error: preserve Neon TLS parameters and use the supplied psycopg dependency lock. Do not set `sslmode=disable`.
- Connection timeout: verify project availability, usage quotas, region, hostname, and any Neon IP/network restrictions. First requests can take longer when services wake.
- Empty wall: verify Render is connected to the same Neon branch/database where you saw the notes; old SQLite data is not auto-imported.
- Notes disappear after redeploy: verify Render DATABASE_URL is PostgreSQL and the Blueprint has not reset it to SQLite. Inspect Neon `wall_messages` before assuming deletion.
- CORS failure: allow the actual Netlify origin on Render; changing database providers does not fix a mismatched origin.

Never paste a private connection URI or password into chat or GitHub. Send only a redacted error if you need help.
