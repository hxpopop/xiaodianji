from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text


BACKEND_ROOT = Path(__file__).resolve().parents[3]
BASE_DATABASE_URL = (
    "postgresql+psycopg://xiaodianji:xiaodianji_test"
    "@127.0.0.1:55432/xiaodianji_test"
)
CONSTRAINT_NAME = "uq_reminder_shop_customer_type"


def _alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config


@pytest.fixture
def migration_database(monkeypatch):
    schema = f"migration_{uuid4().hex}"
    admin_engine = create_engine(BASE_DATABASE_URL)
    engine = None
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    try:
        database_url = f"{BASE_DATABASE_URL}?options=-csearch_path={schema}"
        monkeypatch.setenv("XDJ_DATABASE_URL", database_url)
        config = _alembic_config()
        command.upgrade(config, "0002")

        engine = create_engine(database_url)
        with engine.begin() as connection:
            # Live 0001 metadata contains the later 0003 constraint.
            connection.execute(
                text(
                    f'ALTER TABLE reminders '
                    f'DROP CONSTRAINT IF EXISTS "{CONSTRAINT_NAME}"'
                )
            )
        yield config, engine
    finally:
        if engine is not None:
            engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def test_upgrade_preserves_multiple_null_customer_reminders(
    migration_database,
):
    config, engine = migration_database
    shop_id = UUID("00000000-0000-0000-0000-000000000001")
    first_id = UUID("50000000-0000-0000-0000-000000000001")
    second_id = UUID("50000000-0000-0000-0000-000000000002")
    third_id = UUID("50000000-0000-0000-0000-000000000003")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO shops (id, created_at, name, timezone)
                VALUES (:id, :created_at, :name, :timezone)
                """
            ),
            {
                "id": shop_id,
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "name": "Shop One",
                "timezone": "Asia/Shanghai",
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO reminders (
                    id, created_at, shop_id, customer_id, type,
                    due_at, status, payload
                )
                VALUES (
                    :id, :created_at, :shop_id, NULL, :type,
                    :due_at, :status, CAST(:payload AS jsonb)
                )
                """
            ),
            [
                {
                    "id": first_id,
                    "created_at": datetime(
                        2026, 2, 1, tzinfo=timezone.utc
                    ),
                    "shop_id": shop_id,
                    "type": "store_notice",
                    "due_at": datetime(
                        2026, 2, 10, tzinfo=timezone.utc
                    ),
                    "status": "OPEN",
                    "payload": '{"marker": "first"}',
                },
                {
                    "id": second_id,
                    "created_at": datetime(
                        2026, 2, 2, tzinfo=timezone.utc
                    ),
                    "shop_id": shop_id,
                    "type": "store_notice",
                    "due_at": datetime(
                        2026, 2, 11, tzinfo=timezone.utc
                    ),
                    "status": "OPEN",
                    "payload": '{"marker": "second"}',
                },
            ],
        )

    command.upgrade(config, "0003")

    with engine.begin() as connection:
        preserved_ids = set(
            connection.execute(
                text(
                    """
                    SELECT id
                    FROM reminders
                    WHERE shop_id = :shop_id
                      AND customer_id IS NULL
                      AND type = :type
                    """
                ),
                {"shop_id": shop_id, "type": "store_notice"},
            ).scalars()
        )
        connection.execute(
            text(
                """
                INSERT INTO reminders (
                    id, created_at, shop_id, customer_id, type,
                    due_at, status, payload
                )
                VALUES (
                    :id, :created_at, :shop_id, NULL, :type,
                    :due_at, :status, CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "id": third_id,
                "created_at": datetime(2026, 2, 3, tzinfo=timezone.utc),
                "shop_id": shop_id,
                "type": "store_notice",
                "due_at": datetime(2026, 2, 12, tzinfo=timezone.utc),
                "status": "OPEN",
                "payload": '{"marker": "third"}',
            },
        )
        all_ids = set(
            connection.execute(
                text(
                    """
                    SELECT id
                    FROM reminders
                    WHERE shop_id = :shop_id
                      AND customer_id IS NULL
                      AND type = :type
                    """
                ),
                {"shop_id": shop_id, "type": "store_notice"},
            ).scalars()
        )

    assert preserved_ids == {first_id, second_id}
    assert all_ids == {first_id, second_id, third_id}
