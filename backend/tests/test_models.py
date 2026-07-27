from xiaodianji.models import Base, ConfirmationStatus


def test_initial_schema_contains_all_mvp_tables() -> None:
    assert set(Base.metadata.tables) == {
        "shops", "customers", "customer_aliases", "evidences", "quotes", "quote_items", "transactions", "transaction_items", "payments", "pending_confirmations", "confirmation_events", "record_creation_reservations", "reminders", "anomalies", "evaluation_cases", "evaluation_runs", "evaluation_results",
    }


def test_money_columns_use_fixed_precision() -> None:
    transaction_amount = Base.metadata.tables["transactions"].c.total_amount.type
    payment_amount = Base.metadata.tables["payments"].c.amount.type
    assert transaction_amount.precision == 18
    assert transaction_amount.scale == 2
    assert payment_amount.precision == 18
    assert payment_amount.scale == 2


def test_customer_alias_is_unique_per_shop() -> None:
    constraint_names = {constraint.name for constraint in Base.metadata.tables["customer_aliases"].constraints if constraint.name is not None}
    assert "uq_customer_alias_shop_normalized" in constraint_names


def test_confirmation_idempotency_is_unique_per_shop() -> None:
    constraint_names = {constraint.name for constraint in Base.metadata.tables["pending_confirmations"].constraints if constraint.name is not None}
    assert "uq_confirmation_shop_idempotency" in constraint_names


def test_confirmation_statuses_match_the_audit_contract() -> None:
    assert {status.value for status in ConfirmationStatus} == {"pending", "confirmed", "confirmed_after_edit", "cancelled"}


def test_every_shop_owned_table_has_shop_id() -> None:
    shared_child_tables = {"quote_items", "transaction_items", "confirmation_events", "evaluation_results"}
    for table_name, table in Base.metadata.tables.items():
        if table_name == "shops" or table_name in shared_child_tables:
            continue
        assert "shop_id" in table.c, f"{table_name} must be scoped by shop_id"
