from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Header, Request

from xiaodianji.schemas.query import QueryRequest, QueryResponse


class QueryActions(Protocol):
    async def query(self, shop_id: UUID, question: str) -> QueryResponse: ...


router = APIRouter(prefix="/api/v1/queries", tags=["queries"])


def get_query_service(request: Request) -> QueryActions:
    return request.app.state.query_service


@router.post("", response_model=QueryResponse)
async def query(
    request: Request,
    payload: QueryRequest,
    x_shop_id: UUID = Header(alias="X-Shop-Id"),
) -> QueryResponse:
    return await get_query_service(request).query(x_shop_id, payload.question)
