# ConceptBridge Backend — v0.2

This updates the existing starter for the expanded ConceptBridge plan. It is a **local backend development milestone**, not a finished student-facing application.

**Our stack:** Next.js/React/Tailwind for the future frontend; **FastAPI/Python + MySQL + SQLAlchemy** for the backend; **Thunder Client in VS Code** for API testing. All four audiences remain in scope: MBA, BBA, MCA and BCA.

ConceptBridge owns each conversation and its learning state. OpenAI, Gemini and Anthropic are replaceable engines behind one API. The application does not sign students into their consumer chatbot accounts.

## What works in this package

| Capability | Implementation |
|---|---|
| Learning sessions | MySQL-backed sessions, messages and explicit turn order |
| AI routing | Auto, GPT/OpenAI, Gemini and Claude/Anthropic adapters |
| Continuity | Shared recent messages, pinned learning state, extractive recap and relevant note chunks |
| Fallback | Rate/quota errors, timeouts and selected temporary service failures; no fallback on refusals, invalid input or invalid credentials |
| Retry protection | Repeating the same successful `request_id` returns the same stored response without adding messages or a usage row |
| Development mode | Explicit, visibly labelled mock mode with zero AI calls |
| Notes | Text-based PDF/TXT/Markdown upload and page-aware chunks; lexical retrieval baseline |
| Practice | Business/DBMS MCQs, calculated profit-margin answers, CSV totals, conservative Python/SQL review cues |
| Learning evidence | Stored attempts, misconceptions and fresh follow-up questions; no invented mastery scores |
| YouTube segments | Store curator-supplied video IDs, evidence and start/end seconds; construct watch/embed URLs |
| Developer workflow | VS Code recommendations, OpenAPI schema, Thunder Client request guide, samples and tests |

Not implemented yet: final frontend, automatic YouTube discovery/transcript alignment, embeddings/FAISS/Chroma, semantic AI summarization, authentication, billing/credits, encrypted per-student BYOK, arbitrary code execution, or Power BI project evaluation. See `docs/BLUEPRINT.md` for the connected product roadmap.

## Start here on Windows

Prerequisites: Python 3.11+, MySQL 8.x, VS Code and Thunder Client.

1. Extract this ZIP. Open the **conceptbridge-backend-starter** folder in VS Code.
2. In MySQL Workbench, run `create_database.sql`.
3. In VS Code's PowerShell terminal, run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

4. Edit `.env` locally. Set your actual MySQL host, port, username, password and database. Keep the mock settings for the first test:

```dotenv
DEFAULT_PROVIDER=mock
ENABLE_MOCK=true
AUTO_PROVIDER_ORDER=gemini,openai,anthropic
```

5. Start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

6. In **Thunder Client → New Request**, send these two requests:

```text
GET http://127.0.0.1:8000/api/v1/health
GET http://127.0.0.1:8000/api/v1/ready
```

Health confirms the API is alive. **Ready must return `{"status":"ready","database":"mysql"}` to confirm the database connection.** A health response alone does not prove MySQL is connected.

Open `http://127.0.0.1:8000/docs` for interactive endpoint documentation. The first run creates missing tables. If MySQL is unavailable at startup, fix the connection and restart the backend so missing tables can be created.

The development application has no student authentication yet and lists local demo sessions. Keep it on `127.0.0.1`. The application refuses non-development mode until proper authentication/authorization is implemented.

## Test the first saved conversation

Use Thunder Client, with Body → JSON for POST requests.

**Create a session:** `POST http://127.0.0.1:8000/api/v1/demo/session`

```json
{"degree":"MCA","subject":"DBMS","topic":"Third Normal Form"}
```

Copy its real `session_id`.

**Send a question:** `POST http://127.0.0.1:8000/api/v1/chat`

```json
{
  "session_id": "PASTE_THE_RETURNED_SESSION_ID",
  "message": "Why is StudentID -> DeptID -> DeptName a transitive dependency?",
  "provider": "auto"
}
```

In mock mode, expect `provider_used: "mock"`, `is_mock: true`, and `fallback_used: false`. The reply is explicitly a test response, not real AI tutoring.

**Inspect memory:** `GET http://127.0.0.1:8000/api/v1/sessions/YOUR_SESSION_ID/messages`

The same session will later hold responses from different real providers.

For a repeatable client retry, supply a UUID as `request_id` when first sending a request. Reuse that UUID only for retrying that exact body. Use a new UUID for a new message. Server-generated IDs are returned for reference, but clients should pre-generate IDs when network retry protection is needed.

## Connect the first real provider

Edit `.env`, add your Gemini developer API key, and change:

```dotenv
DEFAULT_PROVIDER=auto
GEMINI_API_KEY=YOUR_KEY_STORED_LOCALLY
```

Restart FastAPI. Call `/api/v1/providers` to see which credentials are configured, then send `/chat` with `provider: "gemini"` or `"auto"`. Configuration status is not a live account/quota check.

OpenAI and Anthropic keys use `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`. Model IDs remain configurable in `.env`. The starter's model choices have been retained; availability depends on each API account.

An explicit provider request uses that provider only. Set `allow_fallback: true` to authorize another configured provider if the selected one is unavailable. `auto` routes among the configured real providers whenever `DEFAULT_PROVIDER=auto`; it never silently falls back to mock. Skipping a provider without a configured key is reported as `skipped`, not as an attempted API call.

API credentials stay on the backend. Consumer ChatGPT/Gemini/Claude account linking, purchased AI credits, and student BYOK are separate later features. Do not send real credentials in chat or commit `.env`.

## Development checks

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m tests.mysql_smoke
```

The pytest suite uses SQLite **only as a test double** and mocked AI responses. The application uses MySQL; it has no SQLite runtime fallback. `tests.mysql_smoke` explicitly checks your configured real MySQL database with a mock provider, creates isolated test data, and removes only that test data afterwards.

Live MySQL, real AI requests and Thunder Client's UI could not be exercised in the build environment. See `docs/VALIDATION.md` for exact evidence and remaining checks.

## Updating from the previous starter

Back up your existing project and database first. Apply the updated source and compare `.env.example` with your local `.env`; remove `mock` from `AUTO_PROVIDER_ORDER`. Keep your real credentials local.

The v0.2 data model adds tables without changing or deleting the original eight tables. Existing `messages` and other starter data remain present. New chat turns use explicit ordinals; the old starter did not record enough ordering information to reconstruct some same-second historical ties exactly.

The original `ai_usage` table is retained for compatibility. New usage records live in `provider_calls`; unknown real-provider monetary costs are stored as `null`, not as zero. This local MVP uses `create_all` for missing tables only; adopt Alembic before further production schema evolution.
