from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="小店记 API", version="0.1.0")

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "xiaodianji"}

    return app


app = create_app()
