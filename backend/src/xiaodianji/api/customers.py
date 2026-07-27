from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Header, Request

from xiaodianji.customers.repository import SQLAlchemyCustomerRepository
from xiaodianji.customers.service import CustomerService
from xiaodianji.db import async_session_factory
from xiaodianji.schemas.customer import CustomerSummary


class CustomerListService(Protocol):
    async def list_summaries(self, shop_id: UUID) -> list[CustomerSummary]: ...


router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


def get_customer_service(request: Request) -> CustomerListService:
    configured_service = request.app.state.customer_service
    if configured_service is not None:
        return configured_service
    return CustomerService(SQLAlchemyCustomerRepository(async_session_factory))


@router.get("", response_model=list[CustomerSummary])
async def list_customers(
    request: Request,
    x_shop_id: Annotated[UUID, Header(alias="X-Shop-Id")],
) -> list[CustomerSummary]:
    service = get_customer_service(request)
    return await service.list_summaries(x_shop_id)

