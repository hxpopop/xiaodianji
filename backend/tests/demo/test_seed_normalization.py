from xiaodianji.customers.normalization import normalize_customer_name
from xiaodianji.demo.seed import _records
from xiaodianji.models import Customer


def test_seed_customer_uses_production_name_normalization() -> None:
    customer = next(record for record in _records() if isinstance(record, Customer))
    assert customer.normalized_name == normalize_customer_name(customer.name)
