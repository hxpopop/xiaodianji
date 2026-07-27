# Task 7 report — LLM、ASR适配器和智能候选记录

## Implementation

- Added typed ASR and extraction provider protocols, deterministic fake providers, an OpenAI-compatible structured JSON candidate extractor, and HTTP ASR adapter.
- Added configuration for LLM/ASR URL, model, and timeout. URLs, models, and keys are blank by default; the default providers remain fakes.
- Added `RecordWorkflow.from_text()` and `from_voice()`. Extraction is always validated with production `RecordDraft`; line subtotals and totals are recalculated by the Pydantic schema. The fake candidate therefore produces the required `420.00`, despite supplying zero totals.
- Text and voice endpoints create only pending confirmations through `SQLAlchemyLedgerWorkflow.create()`. The workflow accepts candidate confidence, source evidence, and model metadata while preserving its existing three-argument call contract.
- Voice uploads evidence before ASR. Successful ASR transcripts are attached to that evidence; ASR/LLM failure returns HTTP 503 with `fallback: "manual_form"` and does not create a confirmation or a formal ledger row.

## Files

- Added `backend/src/xiaodianji/providers/{__init__,base,fake,openai_compatible,http_asr,factory}.py`.
- Added `backend/src/xiaodianji/records/{extraction,text,voice}.py`.
- Updated `backend/src/xiaodianji/api/records.py`, `backend/src/xiaodianji/config.py`, `backend/src/xiaodianji/main.py`, and `backend/src/xiaodianji/ledger/workflow.py`.
- Added `backend/tests/providers/test_fake_provider.py` and `backend/tests/records/{test_text_record,test_voice_record,test_fallback}.py`.

## TDD evidence

### RED

Command (after installing the declared test dependencies):

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/providers tests/records -v
```

Relevant output before implementation:

```text
collected 0 items / 4 errors
ModuleNotFoundError: No module named 'xiaodianji.providers'
```

This failed because the required provider and workflow modules did not exist.

### GREEN

Command:

```powershell
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m pytest tests/providers tests/records -v
```

Relevant output:

```text
collected 5 items
5 passed in 1.52s
```

The focused tests cover the fixed two-item text candidate, the `0.62` confidence, canonical total recalculation, text provider fallback, successful voice evidence/transcript attachment, and ASR fallback retaining the uploaded evidence.

### Full backend suite

Command:

```powershell
& 'C:\Users\ASUS\.codex\visualizations\2026\07\23\019f8dd1-c1a4-7042-85ff-2cf24cec564a\xdj-backend-venv\Scripts\python.exe' -m pytest -v
```

Relevant output:

```text
collected 53 items
53 passed in 6.02s
```

## Self-review

- Candidate flows only call pending-confirmation creation; the focused text test verifies one pending row and zero formal transaction rows.
- Candidate values are passed through `record_draft_adapter`, so provider subtotals and total cannot be trusted.
- Provider errors are translated to the required HTTP 503 manual-form response; no incomplete confirmation is made.
- Provider request settings do not include any credentials by default, and no keys are logged or added to source.
- `git diff --check` completed without whitespace errors.

## Local environment note

`backend/.venv` was created only to install development dependencies before the approved shared interpreter was supplied. It is untracked and deliberately excluded from the commit; all GREEN and full-suite verification used the supplied external `xdj-backend-venv` interpreter.
