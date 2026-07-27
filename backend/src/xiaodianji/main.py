from typing import Any

from fastapi import FastAPI

from xiaodianji.api.confirmations import router as confirmations_router
from xiaodianji.api.customers import router as customers_router
from xiaodianji.api.evidences import router as evidences_router
from xiaodianji.api.ledger import router as ledger_router
from xiaodianji.api.queries import router as queries_router
from xiaodianji.api.records import router as records_router
from xiaodianji.api.reminders import router as reminders_router
from xiaodianji.config import Settings
from xiaodianji.customers.repository import SQLAlchemyCustomerRepository
from xiaodianji.customers.service import CustomerService
from xiaodianji.db import async_session_factory
from xiaodianji.evidences.service import EvidenceService
from xiaodianji.evidences.storage import Boto3ObjectStorage
from xiaodianji.ledger.reader import ledger_reader_from
from xiaodianji.ledger.workflow import SQLAlchemyLedgerWorkflow
from xiaodianji.middleware import RequestBodyLimitMiddleware
from xiaodianji.providers.factory import asr_provider_from, extraction_provider_from
from xiaodianji.queries.service import QueryService
from xiaodianji.records.extraction import RecordWorkflow
from xiaodianji.reminders.service import ReminderService


DEFAULT_MAX_REQUEST_BODY_BYTES = 21 * 1024 * 1024


def create_app(
    *,
    customer_service: Any | None = None,
    manual_record_service: Any | None = None,
    confirmation_service: Any | None = None,
    ledger_service: Any | None = None,
    evidence_service: Any | None = None,
    record_workflow: Any | None = None,
    query_service: Any | None = None,
    reminder_service: Any | None = None,
    max_request_body_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES,
) -> FastAPI:
    workflow = SQLAlchemyLedgerWorkflow(async_session_factory)
    ledger_backend = ledger_service or workflow
    settings = Settings()
    if evidence_service is None:
        storage = Boto3ObjectStorage(
            endpoint_url=settings.object_storage_endpoint,
            access_key=settings.object_storage_access_key,
            secret_key=settings.object_storage_secret_key,
            bucket=settings.object_storage_bucket,
        )
        evidence_service = EvidenceService(async_session_factory, storage)
    app = FastAPI(title="小店记 API", version="0.1.0")
    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=max_request_body_bytes)
    customer_backend = customer_service or CustomerService(
        SQLAlchemyCustomerRepository(async_session_factory)
    )
    app.state.customer_service = customer_backend
    app.state.manual_record_service = manual_record_service or workflow
    app.state.confirmation_service = confirmation_service or workflow
    app.state.ledger_service = ledger_reader_from(ledger_backend)
    app.state.evidence_service = evidence_service
    app.state.query_service = query_service or QueryService(
        async_session_factory,
        customer_backend,
    )
    app.state.reminder_service = reminder_service or ReminderService(
        async_session_factory,
        overdue_days=settings.overdue_days,
    )
    app.state.record_workflow = record_workflow or RecordWorkflow(
        confirmation_workflow=workflow,
        extraction_provider=extraction_provider_from(settings),
        asr_provider=asr_provider_from(settings),
        evidence_service=evidence_service,
        customer_service=customer_backend,
    )
    app.include_router(customers_router)
    app.include_router(records_router)
    app.include_router(confirmations_router)
    app.include_router(ledger_router)
    app.include_router(evidences_router)
    app.include_router(queries_router)
    app.include_router(reminders_router)

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "xiaodianji"}

    return app


app = create_app()
