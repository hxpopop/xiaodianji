# Task 7 — Fix round 2/5 report

## Scope

- Normalize `TranscriptInvalid` from voice transcript attachment to the existing `ProviderUnavailable`/manual-form fallback.
- Replace the long-lived advisory-lock transaction with a durable PostgreSQL reservation row, so external evidence, ASR, and extraction calls do not hold a database connection.

## RED evidence

Command:

```powershell
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m pytest tests/providers tests/records -v
```

Output:

```text
collected 10 items
2 failed, 8 passed
tests/records/test_fallback.py::test_overlong_transcript_returns_manual_fallback_without_record
TranscriptInvalid: transcript is blank or too long
tests/records/test_voice_concurrency.py::test_distinct_voice_keys_complete_with_single_connection_pool
sqlalchemy.exc.TimeoutError: QueuePool limit of size 1 overflow 0 reached, connection timed out, timeout 0.20
```

## Implementation

- Added `RecordCreationReservation` with tenant-scoped unique `(shop_id, idempotency_key)`.
- Added Alembic revision `0002_record_creation_reservations`.
- Reservation checks, inserts, and deletes occur in independent short transactions. The evidence upload, ASR call, transcript attachment, and extraction happen after the claiming transaction releases its connection.
- A failed candidate operation releases its reservation, allowing a subsequent retry while preserving the failed uploaded evidence.
- `RecordWorkflow` catches `TranscriptInvalid` and raises `ProviderUnavailable`, which the API maps to HTTP 503 with `fallback: "manual_form"`.
- Updated Alembic environment configuration to retain the configured `postgresql+psycopg` driver rather than requiring unavailable `psycopg2`.

## GREEN evidence

Focused command:

```powershell
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m pytest tests/providers tests/records -v
```

Output:

```text
collected 10 items
10 passed in 3.75s
```

Migration command:

```powershell
$env:XDJ_DATABASE_URL='postgresql+psycopg://xiaodianji:xiaodianji_test@127.0.0.1:55432/xiaodianji_test'
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m alembic upgrade head
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m alembic current
```

Output:

```text
Running upgrade  -> 0001, Create the initial 小店记 MVP schema.
Running upgrade 0001 -> 0002, Add durable record creation reservations.
0002 (head)
```

Full suite command:

```powershell
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m pytest -v
```

Output:

```text
58 passed, 1 warning in 7.44s
```

The warning was a Windows permission denial while pytest attempted to update its cache; it did not affect test outcomes.

## Files changed

- `backend/alembic/env.py`
- `backend/alembic/versions/0002_record_creation_reservations.py`
- `backend/src/xiaodianji/models/{__init__,record_reservation}.py`
- `backend/src/xiaodianji/records/extraction.py`
- `backend/tests/records/{test_fallback,test_voice_concurrency}.py`
- `backend/tests/test_models.py`

## Self-review

- The reservation key includes `shop_id`, so tenants cannot share idempotency results.
- A successful same-key request returns the single pending confirmation and its one evidence record; distinct-key operations complete with a one-connection pool.
- No in-process lock is relied on for cross-worker safety.
- `git diff --check` passed before commit `3eac2d72ca890fda8182f31d9ccee1a59d122e44`.
