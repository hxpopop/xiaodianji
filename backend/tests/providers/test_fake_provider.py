from decimal import Decimal

from xiaodianji.providers.fake import FakeExtractionProvider


async def test_fake_provider_returns_fixed_two_item_candidate() -> None:
    result = await FakeExtractionProvider().extract(
        "王老板拿十个插座每个十二块，两卷电线每卷一百五，先欠着"
    )

    assert result.draft["customer_name"] == "王老板"
    assert len(result.draft["items"]) == 2
    assert result.field_confidences["items.1.quantity"] == Decimal("0.62")
