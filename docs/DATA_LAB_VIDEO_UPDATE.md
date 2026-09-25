# Saved Data lab analyses and segment playback — 12 September 2026

This update adds database-backed Data lab results and an embedded clip player to the existing local ConceptBridge app.

## Resulting behavior

- **Check my approach** calculates and saves filename, selected columns, grouping, aggregation, chart choice, feedback, and exact decimal totals in the current learning session.
- Opening **Data lab** after refreshing, switching tabs, or restarting the server loads the newest saved analysis. **Saved analyses** reopens the latest 20 results for that session.
- Viewing saved results needs no CSV upload. Recalculating needs the original CSV selected again. Original CSV bytes are not stored.
- Results created before this update cannot be recovered; run that exercise once after installing.
- Data lab history is separate from the **Learning record** practice-question count. The chart remains a monthly-sum reference regardless of the proposed chart type.
- **Play saved segment** opens YouTube inside the clip card with both `start` and `end` parameters. Press Play inside the player. **Open on YouTube** remains available, but its watch link does not enforce an endpoint.
- Only one clip player is open at a time. Closing it or switching tabs removes the player.
- Clips with embedding disabled by their owner require the external YouTube link and a manual stop. Times and relevance are user supplied.

YouTube's documented end parameter is an absolute timestamp measured from the beginning of the video: https://developers.google.com/youtube/player_parameters#end.

## Database and API

New table: `data_analyses`, with a session foreign key, filename, settings JSON, calculated-result JSON, and UTC timestamp. SQLAlchemy JSON supports payloads larger than MySQL TEXT's 64 KB limit. Decimal totals remain strings in JSON.

Startup uses the existing additive `Base.metadata.create_all` path. No existing table, row, credential, or uploaded-note file is replaced by this update. A live MySQL server and CREATE TABLE privileges are required; the user's existing local root account provides those privileges.

- `POST /api/v1/practice/data`: accepts the existing multipart fields plus optional `session_id`. Supplying it saves results and adds `analysis_id`, `session_id`, `filename`, `choices`, and `created_at` to the response. Omitting it preserves the previous calculation-only API.
- `GET /api/v1/sessions/{session_id}/data-analyses?limit=20`: saved analyses ordered newest first, limited to 1–100 results. Session IDs must exist.
- No new package dependencies are required. The generated `openapi.json` includes the changes.
- Existing authentication/development restrictions remain in effect. Session-specific filtering is not student authorization; this build still needs authentication and ownership checks before public deployment.

## Validation

On 12 September 2026, all **32 pytest tests passed**, including five added cases covering:

1. Persistence across a new FastAPI app instance and database session, including exact 0.1 + 0.2 totals.
2. Session-specific histories, newest-first order, limits, and feedback retention.
3. Rejected requests creating no saved analyses.
4. Compatibility with the original sessionless calculation endpoint.
5. Creating the new table while keeping an existing learning session.

The suite also compiled every table definition for MySQL. API tests used a SQLite test double with foreign keys enabled; this does not substitute for the laptop MySQL checkpoint below. No live AI calls or credentials were used. One existing upstream Starlette/AnyIO deprecation warning remains.

The Next.js production build and its TypeScript checks passed. Browser automation could not run because the browser download was unavailable in the build environment. Embedded YouTube playback has not been watched from this environment; the laptop checkpoint verifies it.

## Laptop checkpoint

1. Start both servers using the existing commands and open http://127.0.0.1:3000.
2. Select your Business Analytics session, then **Data lab**. Choose `examples/sales.csv`; keep `date`, `sales`, and `region`. Select **Month**, **Sum**, **Bar chart**, then **Check my approach**.
3. Expect **Saved to this session**, **Your approach fits the task**, and monthly reference totals 31,000; 33,600; 35,500. Total: 100,100, with 9 rows read and none excluded.
4. Refresh, select the same session, and reopen **Data lab**. The saved feedback and totals should return while the file picker says no file selected. That is expected.
5. In the session with your saved 0–60 second clip, open **Video clips**, click **Play saved segment**, and press Play inside the player. Check it reaches the saved end and stops. The external YouTube link continues past that point.

If Data lab reports a table error, inspect the backend startup message and MySQL readiness. Do not delete or recreate the database. If the installer reports a changed source file, keep it and adapt the update to that file before retrying.
