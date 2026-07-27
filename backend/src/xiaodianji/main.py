from typing import Any

from fastapi import FastAPI

from xiaodianji.api.confirmations import router as confirmations_router
from xiaodianji.api.customers import router as customers_router
from xiaodianji.api.records import router as records_router


def create_app(
    *,
    customer_service: Any | None = None,
    manual_record_service: Any | None = None,
    confirmation_service: Any | None = None,
) -> FastAPI:
    app = FastAPI(title="小店记 API", version="0.1.0")
    app.state.customer_service = customer_service
    app.state.manual_record_service = manual_record_service
    app.state.confirmation_service = confirmation_service
    app.include_router(customers_router)
    app.include_router(records_router)
    app.include_router(confirmations_router)

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "xiaodianji"}

    return app


app = create_app()

