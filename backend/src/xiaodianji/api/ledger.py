from decimal import Decimal
from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status

from xiaodianji.ledger.service import LedgerNotFound
from xiaodianji.models import Quote, Transaction
from xiaodianji.schemas.ledger import (
    CustomerBalanceRead,
    QuoteRead,
    TransactionRead,
)


class LedgerReader(Protocol):
    async def get_transaction(
        self,
        shop_id: UUID,
        transaction_id: UUID,
    ) -> Transaction: ...

    async def get_quote(self, shop_id: UUID, quote_id: UUID) -> Quote: ...

    async def customer_balance(
        self,
        shop_id: UUID,
        customer_id: UUID,
    ) -> Decimal: ...


router = APIRouter(tags=["ledger"])


def get_ledger_service(request: Request) -> LedgerReader:
    service = request.app.state.ledger_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ledger service is not configured",
        )
    return service


@router.get(
    "/api/v1/ledger/transactions/{transaction_id}",
    response_model=TransactionRead,
)
async def get_transaction(
    request: Request,
    transaction_id: UUID,
    x_shop_id: UUID = Header(alias="X-Shop-Id"),
) -> TransactionRead:
    try:
        transaction = await get_ledger_service(request).get_transaction(
            x_shop_id,
            transaction_id,
        )
    except LedgerNotFound as error:
        raise HTTPException(status_code=404, detail="transaction not found") from error
    return TransactionRead.from_model(transaction)


@router.get(
    "/api/v1/ledger/quotes/{quote_id}",
    response_model=QuoteRead,
)
async def get_quote(
    request: Request,
    quote_id: UUID,
    x_shop_id: UUID = Header(alias="X-Shop-Id"),
) -> QuoteRead:
    try:
        quote = await get_ledger_service(request).get_quote(x_shop_id, quote_id)
    except LedgerNotFound as error:
        raise HTTPException(status_code=404, detail="quote not found") from error
    return QuoteRead.from_model(quote)


@router.get(
    "/api/v1/customers/{customer_id}/balance",
    response_model=CustomerBalanceRead,
)
async def get_customer_balance(
    request: Request,
    customer_id: UUID,
    x_shop_id: UUID = Header(alias="X-Shop-Id"),
) -> CustomerBalanceRead:
    try:
        balance = await get_ledger_service(request).customer_balance(
            x_shop_id,
            customer_id,
        )
    except LedgerNotFound as error:
        raise HTTPException(status_code=404, detail="customer not found") from error
    return CustomerBalanceRead(customer_id=customer_id, balance=balance)

