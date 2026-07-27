from typing import Any

from fastapi import FastAPI

from xiaodianji.api.confirmations import router as confirmations_router
from xiaodianji.api.customers import router as customers_router
from xiaodianji.api.ledger import router as ledger_router
from xiaodianji.api.records import router as records_router
from xiaodianji.customers.repository import SQLAlchemyCustomerRepository
from xiaodianji.customers.service import CustomerService
from xiaodianji.db import async_session_factory
from xiaodianji.ledger.reader import ledger_reader_from
from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow


def create_app(
    *,
    customer_service: Any | None = None,
    manual_record_service: Any | None = None,
    confirmation_service: Any | None = None,
    ledger_service: Any | None = None,
) -> FastAPI:
    workflow = SQLAlchemyLedgerWorkflow(async_session_factory)
    ledger_backend = ledger_service or workflow
    app = FastAPI(title="小店记 API", version="0.1.0")
    app.state.customer_service = customer_service or CustomerService(
        SQLAlchemyCustomerRepository(async_session_factory)
    )
    app.state.manual_record_service = manual_record_service or workflow
    app.state.confirmation_service = confirmation_service or workflow
    app.state.ledger_service = ledger_reader_from(ledger_backend)
    app.include_router(customers_router)
    app.include_router(records_router)
    app.include_router(confirmations_router)
    app.include_router(ledger_router)

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "xiaodianji"}

    return app


app = create_app()

