from decimal import Decimal

from xiaodianji.reminders.rules import duplicate_idempotency_finding, validate_amounts


def test_amount_mismatch_has_only_calculated_stated_and_difference() -> None:
    finding = validate_amounts(
        item_subtotals=[Decimal("120.00"), Decimal("300.00")],
        stated_total=Decimal("400.00"),
    )

    assert finding is not None
    assert finding.type == "amount_mismatch"
    assert finding.message == "金额不一致"
    assert finding.details == {
        "calculated_total": Decimal("420.00"),
        "stated_total": Decimal("400.00"),
        "difference": Decimal("20.00"),
    }


def test_matching_amounts_return_no_anomaly() -> None:
    assert validate_amounts([Decimal("420.00")], Decimal("420.00")) is None


def test_duplicate_idempotency_finding_never_exposes_request_data() -> None:
    finding = duplicate_idempotency_finding()

    assert finding.type == "duplicate_idempotency"
    assert finding.message == "重复提交异常"
    assert finding.details == {}
