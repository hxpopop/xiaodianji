from datetime import datetime
from typing import Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, Request

from xiaodianji.schemas.reminder import RefreshRemindersRequest, ReminderSummary


class ReminderActions(Protocol):
    async def refresh(self, shop_id: UUID, as_of): ...
    async def list_open(self, shop_id: UUID) -> ReminderSummary: ...


router = APIRouter(prefix="/api/v1/reminders", tags=["reminders"])


def get_reminder_service(request: Request) -> ReminderActions:
    return request.app.state.reminder_service


@router.get("", response_model=ReminderSummary)
async def list_reminders(
    request: Request,
    x_shop_id: UUID = Header(alias="X-Shop-Id"),
) -> ReminderSummary:
    return await get_reminder_service(request).list_open(x_shop_id)


@router.post("/refresh", response_model=ReminderSummary)
async def refresh_reminders(
    request: Request,
    payload: RefreshRemindersRequest,
    x_shop_id: UUID = Header(alias="X-Shop-Id"),
) -> ReminderSummary:
    as_of = payload.as_of or datetime.now(ZoneInfo("Asia/Shanghai")).date()
    return await get_reminder_service(request).refresh(x_shop_id, as_of)
