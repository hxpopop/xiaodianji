from typing import Any

from fastapi import FastAPI

from xiaodianji.api.customers import router as customers_router


def create_app(*, customer_service: Any | None = None) -> FastAPI:
    app = FastAPI(title="小店记 API", version="0.1.0")
    app.state.customer_service = customer_service
    app.include_router(customers_router)

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "xiaodianji"}

    return app


app = create_app()
