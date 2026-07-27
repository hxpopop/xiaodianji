from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Body, Header, HTTPException, Request, status

from xiaodianji.confirmations.service import ConfirmationRecord
from xiaodianji.schemas.confirmation import ConfirmationRead
from xiaodianji.schemas.record import RecordDraft, record_draft_adapter


class ManualRecordCreator(Protocol):
    async def create(
        self,
        shop_id: UUID,
        draft: RecordDraft,
        idempotency_key: str,
    ) -> ConfirmationRecord: ...


router = APIRouter(prefix="/api/v1/records", tags=["records"])


def get_manual_record_service(request: Request) -> ManualRecordCreator:
    service = request.app.state.manual_record_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="manual record service is not configured",
        )
    return service


@router.post(
    "/manual",
    response_model=ConfirmationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_record(
    request: Request,
    payload: Annotated[dict, Body()],
    x_shop_id: Annotated[UUID, Header(alias="X-Shop-Id")],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ConfirmationRead:
    draft = record_draft_adapter.validate_python(payload)
    record = await get_manual_record_service(request).create(
        x_shop_id,
        draft,
        idempotency_key,
    )
    return ConfirmationRead.from_record(record)

