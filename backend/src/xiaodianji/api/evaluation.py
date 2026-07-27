from typing import Protocol
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status

from xiaodianji.schemas.evaluation import EvaluationRunRead, EvaluationRunRequest


class EvaluationActions(Protocol):
    async def run(self, shop_id: UUID, model_name: str) -> EvaluationRunRead: ...
    async def get(self, shop_id: UUID, run_id: UUID) -> EvaluationRunRead | None: ...


router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


def get_evaluation_runner(request: Request) -> EvaluationActions:
    runner = request.app.state.evaluation_runner
    if runner is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="evaluation service is not configured")
    return runner


@router.post("/run", response_model=EvaluationRunRead, status_code=status.HTTP_201_CREATED)
async def run_evaluation(
    request: Request,
    payload: EvaluationRunRequest,
    x_shop_id: UUID = Header(alias="X-Shop-Id"),
) -> EvaluationRunRead:
    return await get_evaluation_runner(request).run(x_shop_id, payload.model_name)


@router.get("/{run_id}", response_model=EvaluationRunRead)
async def get_evaluation(
    request: Request,
    run_id: UUID,
    x_shop_id: UUID = Header(alias="X-Shop-Id"),
) -> EvaluationRunRead:
    result = await get_evaluation_runner(request).get(x_shop_id, run_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evaluation run not found")
    return result
