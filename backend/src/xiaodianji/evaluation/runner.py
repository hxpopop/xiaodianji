import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from xiaodianji.evaluation.metrics import aggregate_scores, confirmation_rates, score_case
from xiaodianji.models import ConfirmationStatus, EvaluationCase, EvaluationResult, EvaluationRun, PendingConfirmation
from xiaodianji.providers.base import ExtractionProvider, ProviderUnavailable
from xiaodianji.schemas.evaluation import ConfirmationRates, EvaluationMetrics, EvaluationResultRead, EvaluationRunRead, FieldScores
from xiaodianji.schemas.record import record_draft_adapter


DEFAULT_CASES_PATH = Path(__file__).resolve().parents[4] / "evaluation" / "cases.jsonl"


class EvaluationRunner:
    def __init__(self, session_factory: async_sessionmaker, predictor: ExtractionProvider, *, cases: Iterable[dict[str, Any]] | None = None) -> None:
        self.session_factory, self.predictor = session_factory, predictor
        self.cases = list(cases) if cases is not None else None

    async def run(self, shop_id: UUID, model_name: str) -> EvaluationRunRead:
        async with self.session_factory.begin() as session:
            await self._import_cases(session, shop_id)
            cases = list((await session.scalars(select(EvaluationCase).where(EvaluationCase.shop_id == shop_id).order_by(EvaluationCase.stable_key))).all())
            run = EvaluationRun(shop_id=shop_id, model_name=model_name, started_at=datetime.now(timezone.utc))
            session.add(run)
            await session.flush()
            scores: list[FieldScores] = []
            failed, latency_total = 0, 0
            for case in cases:
                prediction, is_failed, latency = await self._predict(case)
                field_scores = score_case(case.expected_json, prediction)
                scores.append(field_scores)
                failed += int(is_failed)
                latency_total += latency
                session.add(EvaluationResult(run_id=run.id, case_id=case.id, predicted_json=prediction, field_scores=field_scores.model_dump(mode="json"), latency_ms=latency))
            metrics = aggregate_scores(scores)
            metrics.failed_case_count = failed
            metrics.average_latency_ms = self._average_latency(latency_total, len(cases))
            rates = await self._confirmation_rates(session, shop_id)
            run.finished_at = datetime.now(timezone.utc)
            run.summary_json = {
                "metrics": metrics.model_dump(mode="json"),
                "confirmation_rates": rates.model_dump(mode="json"),
                "case_count": metrics.case_count,
                "failed_case_count": metrics.failed_case_count,
                "average_latency_ms": str(metrics.average_latency_ms),
            }
            await session.flush()
            return await self._read(session, run, metrics, rates)

    async def get(self, shop_id: UUID, run_id: UUID) -> EvaluationRunRead | None:
        async with self.session_factory() as session:
            run = await session.scalar(select(EvaluationRun).where(EvaluationRun.id == run_id, EvaluationRun.shop_id == shop_id))
            if run is None:
                return None
            return await self._read(session, run, EvaluationMetrics.model_validate(run.summary_json["metrics"]), ConfirmationRates.model_validate(run.summary_json["confirmation_rates"]))

    async def _import_cases(self, session, shop_id: UUID) -> None:
        for payload in self._case_payloads():
            existing = await session.scalar(select(EvaluationCase).where(EvaluationCase.shop_id == shop_id, EvaluationCase.stable_key == payload["stable_key"]))
            if existing is None:
                session.add(EvaluationCase(shop_id=shop_id, stable_key=payload["stable_key"], input_type=payload["input_type"], input_payload=payload["input"], expected_json=payload["expected"], tags=payload["tags"]))
        await session.flush()

    async def _predict(self, case: EvaluationCase) -> tuple[dict, bool, int]:
        started = perf_counter()
        try:
            text = case.input_payload.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("invalid fixed evaluation input")
            extraction = await self.predictor.extract(text)
            return record_draft_adapter.validate_python(extraction.draft).model_dump(mode="json"), False, self._elapsed_ms(started)
        except (ProviderUnavailable, AttributeError, TypeError, ValueError, ValidationError):
            return {}, True, self._elapsed_ms(started)

    async def _confirmation_rates(self, session, shop_id: UUID) -> ConfirmationRates:
        statuses = list((await session.scalars(select(PendingConfirmation.status).where(PendingConfirmation.shop_id == shop_id))).all())
        return confirmation_rates(
            direct=sum(status is ConfirmationStatus.CONFIRMED for status in statuses),
            edited=sum(status is ConfirmationStatus.CONFIRMED_AFTER_EDIT for status in statuses),
            cancelled=sum(status is ConfirmationStatus.CANCELLED for status in statuses),
        )

    async def _read(self, session, run: EvaluationRun, metrics: EvaluationMetrics, rates: ConfirmationRates) -> EvaluationRunRead:
        rows = list((await session.execute(select(EvaluationResult, EvaluationCase.stable_key).join(EvaluationCase, EvaluationCase.id == EvaluationResult.case_id).where(EvaluationResult.run_id == run.id, EvaluationCase.shop_id == run.shop_id).order_by(EvaluationCase.stable_key))).all())
        return EvaluationRunRead(
            id=run.id, shop_id=run.shop_id, model_name=run.model_name,
            started_at=run.started_at.isoformat(), finished_at=run.finished_at.isoformat() if run.finished_at else None,
            metrics=metrics, confirmation_rates=rates, case_count=metrics.case_count,
            failed_case_count=metrics.failed_case_count, average_latency_ms=metrics.average_latency_ms,
            results=[EvaluationResultRead(case_id=result.case_id, stable_key=stable_key, predicted_json=result.predicted_json, field_scores=FieldScores.model_validate(result.field_scores), latency_ms=result.latency_ms) for result, stable_key in rows],
        )

    def _case_payloads(self) -> list[dict[str, Any]]:
        if self.cases is not None:
            return self.cases
        return [json.loads(line) for line in DEFAULT_CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, round((perf_counter() - started) * 1000))

    @staticmethod
    def _average_latency(total: int, count: int) -> Decimal:
        if count == 0:
            return Decimal("0.0000")
        return (Decimal(total) / Decimal(count)).quantize(Decimal("0.0001"))
