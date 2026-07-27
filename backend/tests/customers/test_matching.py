from uuid import UUID, uuid4

from xiaodianji.customers.normalization import normalize_customer_name
from xiaodianji.customers.service import (
    CustomerRecord,
    CustomerService,
)


class FakeCustomerRepository:
    def __init__(self, records: list[CustomerRecord]) -> None:
        self.records = records

    async def list_for_shop(self, shop_id: UUID) -> list[CustomerRecord]:
        return self.records


def test_normalize_customer_name_removes_spaces_width_and_title() -> None:
    assert normalize_customer_name("　王 老板 ") == "王"


async def test_exact_customer_name_is_selected_automatically() -> None:
    shop_id = uuid4()
    customer_id = uuid4()
    service = CustomerService(
        FakeCustomerRepository(
            [CustomerRecord(customer_id, "王建材", ("老王",))]
        )
    )

    result = await service.match(shop_id, "王建材")

    assert result.customer_id == customer_id
    assert result.confidence == 1
    assert result.requires_confirmation is False


async def test_exact_alias_is_selected_automatically() -> None:
    shop_id = uuid4()
    customer_id = uuid4()
    service = CustomerService(
        FakeCustomerRepository(
            [CustomerRecord(customer_id, "王建材", ("王老板",))]
        )
    )

    result = await service.match(shop_id, "王老板")

    assert result.customer_id == customer_id
    assert result.confidence == 1
    assert result.candidates[0].matched_on == "alias"


async def test_ambiguous_normalized_names_require_confirmation() -> None:
    shop_id = uuid4()
    service = CustomerService(
        FakeCustomerRepository(
            [
                CustomerRecord(uuid4(), "王老板", ()),
                CustomerRecord(uuid4(), "王师傅", ()),
            ]
        )
    )

    result = await service.match(shop_id, "王")

    assert result.customer_id is None
    assert result.requires_confirmation is True
    assert [candidate.name for candidate in result.candidates] == [
        "王老板",
        "王师傅",
    ]


async def test_fuzzy_match_is_a_candidate_not_an_automatic_merge() -> None:
    shop_id = uuid4()
    service = CustomerService(
        FakeCustomerRepository(
            [CustomerRecord(uuid4(), "张建国五金", ("张总",))]
        )
    )

    result = await service.match(shop_id, "张建国")

    assert result.customer_id is None
    assert result.requires_confirmation is True
    assert result.candidates[0].name == "张建国五金"
    assert result.candidates[0].matched_on == "fuzzy"

