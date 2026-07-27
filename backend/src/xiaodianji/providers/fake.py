from decimal import Decimal

from xiaodianji.providers.base import ASRResult, ExtractionResult


DEMO_TEXT = "王老板拿十个插座每个十二块，两卷电线每卷一百五，先欠着"


class FakeExtractionProvider:
    async def extract(self, text: str) -> ExtractionResult:
        return ExtractionResult(
            draft={
                "target_type": "transaction", "customer_name": "王老板",
                "occurred_at": "2026-07-27T10:00:00+08:00", "payment_status": "unpaid",
                "items": [
                    {"product": "插座", "quantity": "10", "unit": "个", "unit_price": "12.00", "subtotal": "0.00"},
                    {"product": "电线", "quantity": "2", "unit": "卷", "unit_price": "150.00", "subtotal": "0.00"},
                ], "total_amount": "0.00",
            },
            field_confidences={"items.1.quantity": Decimal("0.62")},
            model_name="fake-extraction",
        )


class FakeASRProvider:
    async def transcribe(self, audio: bytes, mime_type: str) -> ASRResult:
        return ASRResult(transcript=DEMO_TEXT, model_name="fake-asr")
