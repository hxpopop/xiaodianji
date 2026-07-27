from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Body, Header, HTTPException, Request, status

from xiaodianji.confirmations.service import (
    ConfirmationConflict,
    ConfirmationNotFound,
    ConfirmationRecord,
)
from xiaodianji.schemas.confirmation import ConfirmationRead


class ConfirmationActions(Protocol):
    async def get(self, confirmation_id: UUID) -> ConfirmationRecord: ...
    async def update_draft(
        self,
        confirmation_id: UUID,
        edited_json: dict,
    ) -> ConfirmationRecord: ...
    async def confirm(
        self,
        confirmation_id: UUID,
        idempotency_key: str,
    ) -> ConfirmationRecord: ...
    async def cancel(
        self,
        confirmation_id: UUID,
        idempotency_key: str,
    ) -> ConfirmationRecord: ...


router = APIRouter(prefix="/api/v1/confirmations", tags=["confirmations"])


def get_confirmation_service(request: Request) -> ConfirmationActions:
    service = request.app.state.confirmation_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="confirmation service is not configured",
        )
    return service


def map_confirmation_error(error: Exception) -> HTTPException:
    if isinstance(error, ConfirmationNotFound):
        return HTTPException(status_code=404, detail="confirmation not found")
    if isinstance(error, ConfirmationConflict):
        return HTTPException(status_code=409, detail=str(error))
    raise error


@router.get("/{confirmation_id}", response_model=ConfirmationRead)
async def get_confirmation(
    request: Request,
    confirmation_id: UUID,
) -> ConfirmationRead:
    try:
        record = await get_confirmation_service(request).get(confirmation_id)
    except (ConfirmationNotFound, ConfirmationConflict) as error:
        raise map_confirmation_error(error) from error
    return ConfirmationRead.from_record(record)


@router.patch("/{confirmation_id}", response_model=ConfirmationRead)
async def update_confirmation(
    request: Request,
    confirmation_id: UUID,
    payload: Annotated[dict, Body()],
) -> ConfirmationRead:
    try:
        record = await get_confirmation_service(request).update_draft(
            confirmation_id,
            payload,
        )
    except (ConfirmationNotFound, ConfirmationConflict) as error:
        raise map_confirmation_error(error) from error
    return ConfirmationRead.from_record(record)


@router.post("/{confirmation_id}/confirm", response_model=ConfirmationRead)
async def confirm_confirmation(
    request: Request,
    confirmation_id: UUID,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ConfirmationRead:
    try:
        record = await get_confirmation_service(request).confirm(
            confirmation_id,
            idempotency_key,
        )
    except (ConfirmationNotFound, ConfirmationConflict) as error:
        raise map_confirmation_error(error) from error
    return ConfirmationRead.from_record(record)


@router.post("/{confirmation_id}/cancel", response_model=ConfirmationRead)
async def cancel_confirmation(
    request: Request,
    confirmation_id: UUID,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ConfirmationRead:
    try:
        record = await get_confirmation_service(request).cancel(
            confirmation_id,
            idempotency_key,
        )
    except (ConfirmationNotFound, ConfirmationConflict) as error:
        raise map_confirmation_error(error) from error
    return ConfirmationRead.from_record(record)

