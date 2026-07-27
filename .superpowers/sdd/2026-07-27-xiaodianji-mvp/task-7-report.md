# Task 7 report — LLM、ASR适配器和智能候选记录

## Implementation

- Added typed ASR and extraction provider protocols, deterministic fake providers, an OpenAI-compatible structured JSON candidate extractor, and HTTP ASR adapter.
- Added configuration for LLM/ASR URL, model, and timeout. URLs, models, and keys are blank by default; the default providers remain fakes.
- Added `RecordWorkflow.from_text()` and `from_voice()`. Extraction is validated with production `RecordDraft`; line subtotals and totals are recalculated by the Pydantic schema.
- Text and voice endpoints create only pending confirmations through `SQLAlchemyLedgerWorkflow.create()`.
- Voice uploads evidence before ASR. Successful ASR transcripts are attached to that evidence; ASR/LLM failure returns HTTP 503 with `fallback: "manual_form"`.

## Files

- Added `backend/src/xiaodianji/providers/{__init__,base,fake,openai_compatible,http_asr,factory}.py`.
- Added `backend/src/xiaodianji/records/{extraction,text,voice}.py`.
- Updated `backend/src/xiaodianji/api/records.py`, `backend/src/xiaodianji/config.py`, `backend/src/xiaodianji/main.py`, and `backend/src/xiaodianji/ledger/workflow.py`.
- Added `backend/tests/providers/test_fake_provider.py` and `backend/tests/records/{test_text_record,test_voice_record,test_fallback}.py`.

## TDD evidence

### Initial RED

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/providers tests/records -v
```

```text
collected 0 items / 4 errors
ModuleNotFoundError: No module named 'xiaodianji.providers'
```

### Initial GREEN

```powershell
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m pytest tests/providers tests/records -v
```

```text
collected 5 items
5 passed in 1.52s
```

### Initial full backend suite

```powershell
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m pytest -v
```

```text
collected 53 items
53 passed in 6.02s
```

## Initial self-review

- Candidate flows only call pending-confirmation creation; the focused text test verifies one pending row and zero formal transaction rows.
- Candidate values pass through `record_draft_adapter`, so provider subtotals and total cannot be trusted.
- Provider request settings do not include credentials by default, and no keys are logged or added to source.

## Local environment note

`backend/.venv` was created only to install development dependencies before the approved shared interpreter was supplied. It is untracked and deliberately excluded from the commit; all subsequent verification used the supplied external `xdj-backend-venv` interpreter.

## Fix round 1/5 — provider boundary fallback and voice idempotency

### Changes

- Added focused provider/record tests for non-object ASR JSON, semantically invalid `RecordDraft` candidates, malformed confidence values, and two same-key voice requests.
- `HTTPASRProvider` now rejects non-object JSON as `ProviderUnavailable`; the OpenAI-compatible adapter similarly normalizes malformed output and confidence conversion failures.
- `RecordWorkflow` converts malformed extraction and ASR response objects, Pydantic validation failures, and invalid confidence values into `ProviderUnavailable`, allowing the API to return the required manual-form fallback without calling confirmation creation.
- Added `SQLAlchemyLedgerWorkflow.run_creation_once()`. It takes a tenant-and-idempotency-key-derived PostgreSQL transaction advisory lock before upload/ASR/extraction, returns an existing pending confirmation if present, and otherwise performs the candidate operation. This uses the existing pending-confirmation unique key and needs no schema or migration change.

### RED

Command:

```powershell
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m pytest tests/providers tests/records -v
```

Relevant output:

```text
collected 8 items
4 failed, 4 passed
AttributeError: 'list' object has no attribute 'get'
ValidationError: transaction.customer_name / items / occurred_at / payment_status
ValueError: Unknown format code 'f' for object of type 'str'
assert 2 == 1
```

### GREEN

Command:

```powershell
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m pytest tests/providers tests/records -v
```

Relevant output:

```text
collected 8 items
8 passed in 1.69s
```

### Full backend suite

Command:

```powershell
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m pytest -v
```

Relevant output:

```text
collected 56 items
56 passed in 6.49s
```

### Fix-round self-review

- Invalid provider response paths are caught at the provider/validation boundary and never invoke `create()`; tests assert HTTP 503 plus `fallback: "manual_form"` and zero creator calls.
- The voice reservation occurs before evidence creation. PostgreSQL holds the advisory lock until the candidate confirmation exists, so a repeated or concurrent same-shop/key request returns that record without duplicate evidence, ASR, extraction, or pending rows.
- Lock keys include both tenant UUID and idempotency key; different tenants cannot share an idempotency result.
- No database schema or migration change was required. `git diff --check` was run before commit.
