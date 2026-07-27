from xiaodianji.models import Base


def test_confirmation_stores_resolution_idempotency_key() -> None:
    assert (
        "resolution_idempotency_key"
        in Base.metadata.tables["pending_confirmations"].c
    )
