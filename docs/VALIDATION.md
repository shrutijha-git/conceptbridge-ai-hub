# Validation record — ConceptBridge v0.2

Validated on 5 September 2026 using Python 3.12.

## Completed checks

- **27 pytest cases passed.**
- Python compilation, API imports and OpenAPI generation passed.
- All 15 table definitions compiled with SQLAlchemy's MySQL dialect.
- Configuration round-tripped database passwords containing URL-special characters correctly.
- SDK classes and Gemini timeout/retry configuration imported successfully with the installed versions.

The tests cover recoverable fallback with the same context, refusing fallback for invalid requests and refusals, explicit provider selection, mock isolation, local sessions, message order, idempotent replay, rollback after failure, provider switching, bounded context/recap, legacy message preservation, note upload/retrieval, practice feedback, exact sample calculations, malformed CSV errors, and invalid video intervals.

## Limits of this evidence

- **No MySQL server was available in the build environment.** API tests used a SQLite test double with foreign-key checks enabled. MySQL DDL compilation passed, but live MySQL connection, row locks and actual persistence still need the supplied `python -m tests.mysql_smoke` check.
- **No live provider credentials were supplied.** Cross-provider success/failure was tested using mocked providers. The three SDK adapters are implemented; live account access, model access, billing and provider responses were not verified.
- Thunder Client's VS Code interface was not available. The manual request guide and generated OpenAPI schema are provided; no UI import or collection run is claimed.
- No student frontend or cloud deployment is included in this backend milestone.
- YouTube URLs are constructed from curator-supplied metadata. No real learning video was searched, timed or independently verified in this build.
- Notes use lexical retrieval, not embeddings. Recaps are extractive, not semantic AI summaries.
- Code is reviewed for limited mistake patterns; submitted Python/SQL is not executed.

One upstream Starlette/AnyIO deprecation warning remains in the test runner. It did not cause a test failure.

## Next verification on your machine

1. Configure local MySQL in `.env` and start FastAPI.
2. Confirm `/api/v1/ready` returns MySQL readiness.
3. Run `python -m tests.mysql_smoke` with local mock mode enabled.
4. Configure one real provider, restart, and send one tutoring request.
5. Configure a second provider and verify a same-session handoff using `docs/THUNDER_CLIENT.md`.
