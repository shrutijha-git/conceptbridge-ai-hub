# ConceptBridge frontend

A student-facing Next.js / React website for the existing ConceptBridge FastAPI backend. This is the first connected local interface: the application runs in your browser, with Python and MySQL behind it.

## What this package contains

Copy the **frontend** folder into your existing **conceptbridge-backend-starter** project. This package adds a frontend; it does not replace the backend, its `.env`, its uploaded notes, or your MySQL database.

You can reopen existing sessions, chat with a configured AI provider, upload notes, save a learning goal, answer practice questions, inspect your learning record, analyze the sample sales CSV, and save manually reviewed YouTube clips. All session records come from the existing backend.

## 1. Put the folder in the right place

1. Download `conceptbridge-frontend-addon.zip` and find it in Windows Downloads.
2. Right-click the ZIP and choose **Extract All**. Click **Extract**.
3. Open the extracted folder. Find the folder named **frontend**.
4. Copy that **frontend** folder into:

   `C:\Users\shrut\OneDrive\Desktop\conceptbridge-backend-starter`

5. Open that existing project in VS Code. It should now contain `app`, `docs`, `examples`, `tests`, and `frontend` alongside the existing backend files.
6. Expand `frontend` in the Explorer. You should see `package.json`, `package-lock.json`, `app`, `components`, and `lib` inside it.

The exact new path to the package file is:

`C:\Users\shrut\OneDrive\Desktop\conceptbridge-backend-starter\frontend\package.json`

Avoid nesting it as `frontend\frontend\package.json`. If a `frontend` folder already exists from different work, keep a backup before copying; do not overwrite unrelated code.

## 2. Check Node.js once

In VS Code, choose **Terminal → New Terminal**. Run these commands one at a time:

```powershell
node --version
```

```powershell
npm.cmd --version
```

Use Node.js **24 LTS** for this package. A supported Node.js 22 installation also satisfies its `>=22` requirement. This frontend was compiled with Node.js 24.19.0.

If Node is missing or older than version 22:

1. Open https://nodejs.org/en/download.
2. Select the **LTS** release, **Windows**, and the architecture appropriate to your laptop (normally x64).
3. Download the **Windows Installer (.msi)** and run it. Keep the default installation options, including npm and adding Node to PATH.
4. Close and reopen VS Code so a new terminal can find Node. This also stops any backend terminal, so start the backend again in step 3.
5. Run the version commands again. Do not install Node inside `.venv`; Python and Node have separate dependencies.

Official Next.js installation documentation: https://nextjs.org/docs/app/getting-started/installation.

## 3. Keep the Python backend running

If your backend terminal already shows `Application startup complete` and is still running on port 8000, leave it running and move to step 4.

Otherwise, make sure the MySQL server is running. Open **Terminal → New Terminal** in VS Code and run:

```powershell
cd "C:\Users\shrut\OneDrive\Desktop\conceptbridge-backend-starter"
```

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Wait for `Application startup complete`. Keep this terminal open. You do not need to activate `.venv` to use this command.

Keep your working backend `.env` settings, including `MYSQL_USER=root`, your private MySQL password, and the existing Gemini key. Ensure these two settings are saved in that backend `.env`:

```dotenv
DEFAULT_PROVIDER=auto
ENABLE_MOCK=false
```

Changing `.env` requires stopping the backend with Ctrl+C and running the startup command again. Editing it does not require creating another API key or database. Your working Gemini model setting can stay as it is.

## 4. Install the frontend packages once

Open a **second terminal** using **Terminal → New Terminal**. Keep the backend terminal running.

Run:

```powershell
cd "C:\Users\shrut\OneDrive\Desktop\conceptbridge-backend-starter\frontend"
```

Then run:

```powershell
npm.cmd ci
```

Wait until installation finishes and the PowerShell prompt returns. Internet access is needed to download the packages. `npm.cmd` avoids PowerShell's `npm.ps1` execution-policy issue.

You only need to install again after replacing this package or changing its dependencies. Do not run `npm audit fix --force` as part of setup; it can change package versions and introduce incompatibilities.

The included `package-lock.json` records the resolved dependency versions. `node_modules` is created by this command and is intentionally absent from the ZIP.

## 5. Start the website

In the second terminal, still inside **frontend**, run:

```powershell
npm.cmd run dev
```

Wait until Next.js reports that it is ready. Leave this terminal open too.

Open this address in Chrome or Edge:

**http://127.0.0.1:3000**

| Address                    | What it opens                          |
| -------------------------- | -------------------------------------- |
| http://127.0.0.1:3000      | The ConceptBridge student website      |
| http://127.0.0.1:8000/docs | The backend's Swagger API testing page |

The frontend already defaults to `http://127.0.0.1:8000/api/v1`. You do not need to create another `.env` to use these standard ports. If your backend address changes later, copy `frontend/.env.example` to `frontend/.env.local`, update only `NEXT_PUBLIC_API_BASE_URL`, and restart the frontend. Anything prefixed `NEXT_PUBLIC_` is visible to the browser; never put an API key or database password there.

## 6. Continue your existing Third Normal Form session

1. In the website's left sidebar, click your existing **Third Normal Form** session. Sessions are loaded from MySQL; there is no need to create another one to continue.
2. Check that your old messages load. Older messages labelled **Mock demo** are your previous tests; that label does not mean the new Gemini configuration is broken.
3. In **Your notes**, look for `dbms-notes.txt`. It should already be listed if you opened the same session used for the successful upload.
4. Stay on **Understand → Tutor**. Leave the AI provider set to **Auto**, or select **Gemini** explicitly.
5. Type this and press **Send**:

   ```text
   Using my uploaded notes, give me a new example of a transitive dependency and cite the relevant note chunk. Then ask me one short question.
   ```

6. The answer should show a **Gemini** label. Markdown, formulas, and code are formatted for reading.
7. Expand **Reply details** if you want to inspect the actual provider and source chunk IDs supplied for that new reply. Historical messages have provider labels; the backend does not return historical per-turn source metadata through its messages endpoint.
8. To upload another file, use **Choose notes**, select an actual PDF/TXT/MD file from your laptop, then click **Add to this session**. You can use `examples/dbms-notes.txt`. Upload only when needed; existing notes do not need to be uploaded on every startup.

The browser handles multipart upload formatting automatically. You do not need Thunder Client for these student actions.

## 7. Try the other learning activities

- **Understand → Try a question:** choose a DBMS or business question, select an answer, and click **Check my answer**. Feedback includes a related follow-up. If you make a mistake, discuss it with the tutor.
- **Practise → Try a question:** work through a built-in profit-margin exercise. These numerical answers are checked by the backend.
- **Code → Try a question:** submit a Python or SQL attempt. The backend offers limited static review cues. It does not execute your code or prove that the solution passes tests.
- **Data lab:** select `examples/sales.csv`, keep the column names `date`, `sales`, `region`, and choose your grouping, aggregation, and chart. Click **Check my approach**. Feedback, settings, filename, and exact calculated totals are saved in MySQL for the current session. Reopening Data lab loads its newest analysis; **Saved analyses** reopens any of the latest 20 results. The original CSV is not retained, so choose it again to calculate new results. Data analyses are separate from the practice-question count. Requires the September 12 backend update, which adds `data_analyses` without changing existing tables.
- **Video clips:** click **Add a clip**, enter an actual YouTube video's ID, reviewed timestamps, and a useful explanation. **Play saved segment** opens an embedded player with both start and end boundaries; press Play inside it. **Open on YouTube** is a fallback that starts at the saved time and continues beyond the endpoint. Some video owners disallow embedding. These clips are manually curated; the system does not automatically search for or verify video segments.
- **Learning record:** inspect saved attempts, concepts, and chat turn counts. The counts are records, not mastery percentages.
- **My learning goal:** save an objective and explanation preference. The backend includes these in later tutor context.

Only configured providers can be selected. Configuration means that a key is present; a successful chat is what confirms that a provider actually works. Gemini is the provider you have already tested. An OpenAI or Anthropic option without a key remains unavailable.

## Restarting on another day

You need the MySQL server plus **two running terminals**:

1. Backend terminal, in the project root: run the Python/Uvicorn command in step 3.
2. Frontend terminal, in `frontend`: run `npm.cmd run dev`.
3. Open http://127.0.0.1:3000 and select your saved session.

Do not recreate the database, reinstall Python packages, make another key, or run `npm.cmd ci` every day. Stop each development server with Ctrl+C when you finish. Your saved backend records remain in MySQL.

## Troubleshooting

| What you see                                              | What to do                                                                                                                                                                                      |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `node` or `npm.cmd` is not recognized                     | Install Node LTS, reopen VS Code, then use a new terminal.                                                                                                                                      |
| npm cannot find `package.json`                            | Your terminal must be in the `frontend` folder from step 4.                                                                                                                                     |
| Port 3000 already in use                                  | Stop the earlier frontend terminal with Ctrl+C. Run only one frontend instance.                                                                                                                 |
| Port 8000 already in use                                  | Your backend may already be running. Use its existing terminal and avoid starting another copy.                                                                                                 |
| Website says the backend is offline                       | Check the backend terminal and MySQL. Open `/api/v1/ready` on port 8000, then click the website's reconnect icon.                                                                               |
| Browser cannot reach backend although `/ready` works      | Check backend `ALLOWED_ORIGINS` includes `http://127.0.0.1:3000` and `http://localhost:3000`. Restart the backend after editing `.env`. Use port 3000 for this frontend.                        |
| Provider returns an API error                             | Read the exact message in the website. Keep the key only in the backend `.env`; do not paste it into screenshots. Explicit retries preserve the chat request ID to avoid duplicate saved turns. |
| Reply was saved but the learning record could not refresh | Click **Reload session**. Do not resend the successful question.                                                                                                                                |
| PDF upload is rejected                                    | Use an unencrypted text-based PDF with at most 30 pages, or UTF-8 TXT/MD. Maximum 5 MB and 60,000 extracted characters; at least 30 readable characters.                                        |
| Expected note file is missing                             | Select the session to which it was uploaded. Notes are attached per session.                                                                                                                    |
| A file upload or practice submission loses its connection | These endpoints do not have chat's request-ID protection. Reconnect and inspect notes or the learning record before submitting again.                                                           |

## Understand the code

| File/folder inside frontend      | Its job                                                                                |
| -------------------------------- | -------------------------------------------------------------------------------------- |
| `app/page.tsx`                   | Opens the learning workspace.                                                          |
| `app/layout.tsx`                 | Sets the page title and loads the styles and math fonts.                               |
| `app/globals.css`                | Controls the layout, typography, colors, and smaller-screen layout using ordinary CSS. |
| `components/study-workspace.tsx` | Manages sessions, modes, chat, notes uploads, and learning goals.                      |
| `components/practice-panel.tsx`  | Displays built-in questions, feedback, follow-ups, and progress.                       |
| `components/resources.tsx`       | Implements the sales CSV exercise and manually curated video clips.                    |
| `components/markdown.tsx`        | Renders AI Markdown and formulas with raw HTML disabled.                               |
| `components/ui.tsx`              | Shares loading and error messages.                                                     |
| `lib/api.ts`                     | Makes HTTP requests to FastAPI and turns API errors into readable messages.            |
| `lib/types.ts`                   | Documents the request and response shapes with TypeScript types.                       |
| `package.json`                   | Lists scripts and dependencies.                                                        |
| `package-lock.json`              | Records the resolved package versions for installation.                                |

Trace a chat by reading `send()` in `study-workspace.tsx`, `postJson()` in `lib/api.ts`, and then your existing backend's `app/api/routes.py`, `app/ai/context_builder.py`, and `app/ai/router.py`. The frontend sends the question and session ID. The backend retrieves context, calls the provider, saves the turn, and returns the answer. React then displays it.

Business data is stored by the backend. The browser stores only the last-selected session ID as an optional device preference. There is no second database in this frontend.

## GitHub and competition preparation

Keep the backend and the new `frontend` directory in the same project repository. Include both source trees, the documentation, safe samples, dependency manifests, and lockfiles.

The frontend has its own `.gitignore` for `node_modules`, `.next`, and `.env` files. Your existing root `.gitignore` must also exclude backend `.env`, `.venv`, caches, and runtime uploads. Git ignore rules do not remove a secret that was already committed. Before publishing, inspect the files to be committed with `git status` and the staged diff. Do not drag a working folder containing secrets directly into GitHub.

For a local demo, show opening a session, asking Gemini about uploaded notes, receiving a cited answer, answering a practice question, and seeing feedback in the learning record. Explain that the code was developed with AI assistance if the competition requires that disclosure. Check the actual competition rules and upload form for the permitted tools, required repository visibility, video length, and submission fields; those rules have not been verified here.

This is a **local development prototype**. The existing backend has no student authentication/authorization and intentionally limits itself to development mode. It is not ready to be placed on the public internet as a multi-user service. Authentication, ownership checks, deployment configuration, stronger evaluation, and additional live provider tests remain future work.

## Validation and limits

The frontend passed TypeScript and a Next.js production build. Additional checks passed for actual multipart file encoding, validation/provider error messages, and the absence of automatic chat retries; these used local request/response objects, not a live AI service. Its route and payload bindings were reviewed against the existing backend source and OpenAPI file. It has not been exercised in a browser against your laptop's running MySQL/Gemini service from this workspace; steps 5–7 are your local integration checkpoint.

To repeat build checks in the frontend terminal after stopping the frontend server:

```powershell
npm.cmd run typecheck
npm.cmd run build
```

Then start your normal development website with `npm.cmd run dev`.

Current limits: the UI displays up to 100 saved sessions and the latest 200 messages per session. Practice is a small built-in question bank. Retrieval uses keyword matching, not embeddings. Provider selection and retry controls reuse the backend's routing and transaction behavior; the UI does not add fake fallback answers or scores.
