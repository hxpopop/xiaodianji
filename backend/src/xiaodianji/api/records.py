from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Body, File, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from xiaodianji.confirmations.service import ConfirmationRecord
from xiaodianji.providers.base import ProviderUnavailable
from xiaodianji.schemas.confirmation import ConfirmationRead
from xiaodianji.schemas.record import RecordDraft, record_draft_adapter


class ManualRecordCreator(Protocol):
    async def create(self, shop_id: UUID, draft: RecordDraft, idempotency_key: str) -> ConfirmationRecord: ...


router = APIRouter(prefix="/api/v1/records", tags=["records"])


def get_manual_record_service(request: Request) -> ManualRecordCreator:
    service = request.app.state.manual_record_service
    if service is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="manual record service is not configured")
    return service


def get_record_workflow(request: Request):
    service = request.app.state.record_workflow
    if service is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="record workflow is not configured")
    return service


def manual_fallback() -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": "AI service is unavailable", "fallback": "manual_form"})


@router.post("/manual", response_model=ConfirmationRead, status_code=status.HTTP_201_CREATED)
async def create_manual_record(request: Request, payload: Annotated[dict, Body()], x_shop_id: Annotated[UUID, Header(alias="X-Shop-Id")], idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]) -> ConfirmationRead:
    draft = record_draft_adapter.validate_python(payload)
    record = await get_manual_record_service(request).create(x_shop_id, draft, idempotency_key)
    return ConfirmationRead.from_record(record)


@router.post("/text", response_model=ConfirmationRead, status_code=status.HTTP_201_CREATED)
async def create_text_record(request: Request, payload: Annotated[dict, Body()], x_shop_id: Annotated[UUID, Header(alias="X-Shop-Id")], idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]) -> ConfirmationRead | JSONResponse:
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=422, detail="text is required")
    try:
        record = await get_record_workflow(request).from_text(x_shop_id, text.strip(), idempotency_key)
    except ProviderUnavailable:
        return manual_fallback()
    return ConfirmationRead.from_record(record)


@router.post("/voice", response_model=ConfirmationRead, status_code=status.HTTP_201_CREATED)
async def create_voice_record(request: Request, file: Annotated[UploadFile, File()], x_shop_id: Annotated[UUID, Header(alias="X-Shop-Id")], idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]) -> ConfirmationRead | JSONResponse:
    try:
        record = await get_record_workflow(request).from_voice(x_shop_id, await file.read(), file.content_type or "", file.filename, idempotency_key)
    except ProviderUnavailable:
        return manual_fallback()
    finally:
        await file.close()
    return ConfirmationRead.from_record(record)
