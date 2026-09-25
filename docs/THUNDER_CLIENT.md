# Test ConceptBridge in Thunder Client

Use the Thunder Client extension inside VS Code. No Postman is required.

Start the backend, choose **New Request**, select the method, paste the URL, and use **Body → JSON** where shown. Replace `SESSION_ID` with the ID returned by session creation.

Thunder Client's current documentation lists collection import/export as paid functionality. The manual steps below need no imported collection. If your edition supports imports, `openapi.json` is included, or use `http://127.0.0.1:8000/openapi.json`.

## 1. Health and real database readiness

| Method | URL | Expected result |
|---|---|---|
| GET | `http://127.0.0.1:8000/api/v1/health` | 200, API is alive |
| GET | `http://127.0.0.1:8000/api/v1/ready` | 200, `database: mysql` |
| GET | `http://127.0.0.1:8000/api/v1/providers` | Provider configuration; never API keys |

## 2. Create a learning session

`POST http://127.0.0.1:8000/api/v1/demo/session`

```json
{"degree":"MCA","subject":"DBMS","topic":"Third Normal Form"}
```

Expected: 201 with `session_id`, `course_id`, `user_id`.

## 3. Store what the tutor must remember

`PATCH http://127.0.0.1:8000/api/v1/sessions/SESSION_ID/memory`

```json
{
  "learning_objective":"Identify transitive dependencies and decompose into 3NF",
  "known_concepts":["Functional dependency","1NF"],
  "weak_concepts":["Transitive dependency"],
  "misconceptions":["Confused partial and transitive dependency"],
  "current_question":"How would you split Student(StudentID, DeptID, DeptName)?",
  "explanation_preference":"Worked examples"
}
```

These fields are explicit learning notes, not a calibrated assessment of mastery.

## 4. Send a message

`POST http://127.0.0.1:8000/api/v1/chat`

```json
{
  "session_id":"SESSION_ID",
  "message":"Why is StudentID -> DeptID -> DeptName a transitive dependency?",
  "provider":"auto",
  "mode":"understand"
}
```

With the default `.env`, expect a labelled mock response. A real answer requires a configured provider key and real mode.

## 5. Test a provider change after connecting two real APIs

Send the first request with `provider: "anthropic"`. Send a follow-up with the same `session_id`, `provider: "openai"`, and `message: "Which table should I split first?"`.

Expected: the second reply has `provider_changed: true`, `previous_provider: "anthropic"`, `provider_used: "openai"`. Inspect the history and memory endpoints. Do not intentionally exhaust paid quota to test fallback; the automated tests simulate a rate-limit failure.

Optional explicit fallback:

```json
{"session_id":"SESSION_ID","message":"Help me take the next step.","provider":"anthropic","allow_fallback":true}
```

Fallback applies to recoverable availability errors. It does not work around a refusal, invalid input or an invalid API key.

## 6. Check idempotency

Generate a UUID in PowerShell:

```powershell
[guid]::NewGuid().ToString()
```

Add it to the first request as `request_id`. Send the same body twice. Expect the same response, one conversation turn, two messages, and one usage record. Change the message while retaining the ID; expect 409. Use a new ID for each new message.

## 7. Read saved state

| Method | Path after `http://127.0.0.1:8000/api/v1` |
|---|---|
| GET | `/sessions/SESSION_ID/messages` |
| GET | `/sessions/SESSION_ID/memory` |
| GET | `/sessions/SESSION_ID/usage` |
| GET | `/sessions/SESSION_ID/progress` |

## 8. Upload notes

`POST http://127.0.0.1:8000/api/v1/documents`

Use **Body → Form** with these fields; let Thunder Client set the multipart boundary.

| Field | Type | Value |
|---|---|---|
| `session_id` | Text | Your session ID |
| `file` | File | `examples/dbms-notes.txt`, or your text-based PDF |

Expected: 201, `retrieval: lexical`, `embeddings_created: false`. A later chat request on 3NF should return matching chunk IDs in `context.source_chunks`.

## 9. Attempt a practice question

`GET http://127.0.0.1:8000/api/v1/practice/questions?mode=understand`

`POST http://127.0.0.1:8000/api/v1/practice/attempts`

```json
{"session_id":"SESSION_ID","question_id":"buyer-power","answer":"Supplier power"}
```

Expected: a specific correction and a fresh supplier-power scenario. For numerical practice, use `margin-1`; for code review, `python-distinct` or `sql-groups`. Code review never claims execution.

## 10. Data practice

`POST http://127.0.0.1:8000/api/v1/practice/data`

Use multipart form:

| Field | Type | Value |
|---|---|---|
| `file` | File | `examples/sales.csv` |
| `grouping` | Text | `month` |
| `aggregation` | Text | `sum` |
| `chart` | Text | `line` |

Expected monthly totals: January **31000**, February **33600**, March **35500**. Overall total **100100**. The backend supplies chart-ready data; this package does not yet draw a frontend chart. Change aggregation to `average` to get corrective feedback on the chart plan.

## 11. Add a real video segment after reviewing it

`POST http://127.0.0.1:8000/api/v1/videos/segments`

Supply a real video ID, title, topic, start/end in seconds, and a short explanation of what that interval covers. The schema is in `/docs`. No invented learning video is seeded in this package. `verification` stays `user_supplied`; saving a link does not independently verify the video's content or availability.

`GET http://127.0.0.1:8000/api/v1/sessions/SESSION_ID/videos?topic=3NF`

Returns the saved matching segments. The normal watch URL starts at the chosen timestamp; the embedded player URL includes both start and end.

Official references checked for this workflow:
- https://docs.thunderclient.com/features/import
- https://developers.google.com/youtube/player_parameters
