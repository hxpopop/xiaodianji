import pytest
from pydantic import ValidationError

from xiaodianji.config import Settings


def test_overdue_days_defaults_to_thirty_and_must_be_positive() -> None:
    assert Settings().overdue_days == 30
    with pytest.raises(ValidationError):
        Settings(overdue_days=0)
