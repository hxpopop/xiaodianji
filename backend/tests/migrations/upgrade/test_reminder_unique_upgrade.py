from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


BACKEND_ROOT = Path(__file__).resolve().parents[5] / "xiaodianji" / "backend"
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
            # Revision 0001 uses live model metadata, which now includes the
            # 0003 constraint. Remove it to reproduce a deployed 0002 schema.
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


def test_upgrade_0002_to_0003_deduplicates_reminders_deterministically(
    migration_database,
):
    config, engine = migration_database
    shop_one = UUID("00000000-0000-0000-0000-000000000001")
    shop_two = UUID("00000000-0000-0000-0000-000000000002")
    customer_one = UUID("00000000-0000-0000-0000-000000000011")
    customer_two = UUID("00000000-0000-0000-0000-000000000012")
    customer_three = UUID("00000000-0000-0000-0000-000000000013")
    open_tie_winner = UUID(
        "10000000-0000-0000-0000-000000000003"
    )
    open_over_resolved = UUID(
        "20000000-0000-0000-0000-000000000001"
    )
    other_type_control = UUID(
        "30000000-0000-0000-0000-000000000001"
    )
    other_shop_control = UUID(
        "40000000-0000-0000-0000-000000000001"
    )

    shops = [
        {
            "id": shop_one,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "name": "Shop One",
            "timezone": "Asia/Shanghai",
        },
        {
            "id": shop_two,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "name": "Shop Two",
            "timezone": "Asia/Shanghai",
        },
    ]
    customers = [
        {
            "id": customer_one,
            "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "shop_id": shop_one,
            "name": "Customer One",
            "normalized_name": "customer one",
        },
        {
            "id": customer_two,
            "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "shop_id": shop_one,
            "name": "Customer Two",
            "normalized_name": "customer two",
        },
        {
            "id": customer_three,
            "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "shop_id": shop_two,
            "name": "Customer Three",
            "normalized_name": "customer three",
        },
    ]
    reminders = [
        {
            "id": UUID("10000000-0000-0000-0000-000000000001"),
            "created_at": datetime(2026, 2, 1, tzinfo=timezone.utc),
            "shop_id": shop_one,
            "customer_id": customer_one,
            "type": "overdue",
            "due_at": datetime(2026, 2, 10, tzinfo=timezone.utc),
            "status": "OPEN",
            "payload": '{"marker": "older-open"}',
        },
        {
            "id": UUID("10000000-0000-0000-0000-000000000002"),
            "created_at": datetime(2026, 2, 2, tzinfo=timezone.utc),
            "shop_id": shop_one,
            "customer_id": customer_one,
            "type": "overdue",
            "due_at": datetime(2026, 2, 11, tzinfo=timezone.utc),
            "status": "OPEN",
            "payload": '{"marker": "same-time-lower-uuid"}',
        },
        {
            "id": open_tie_winner,
            "created_at": datetime(2026, 2, 2, tzinfo=timezone.utc),
            "shop_id": shop_one,
            "customer_id": customer_one,
            "type": "overdue",
            "due_at": datetime(2026, 2, 12, tzinfo=timezone.utc),
            "status": "OPEN",
            "payload": '{"marker": "same-time-higher-uuid"}',
        },
        {
            "id": open_over_resolved,
            "created_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "shop_id": shop_one,
            "customer_id": customer_two,
            "type": "overdue",
            "due_at": datetime(2026, 3, 10, tzinfo=timezone.utc),
            "status": "OPEN",
            "payload": '{"marker": "open-priority"}',
        },
        {
            "id": UUID("20000000-0000-0000-0000-000000000002"),
            "created_at": datetime(2026, 3, 2, tzinfo=timezone.utc),
            "shop_id": shop_one,
            "customer_id": customer_two,
            "type": "overdue",
            "due_at": datetime(2026, 3, 11, tzinfo=timezone.utc),
            "status": "RESOLVED",
            "payload": '{"marker": "newer-resolved"}',
        },
        {
            "id": other_type_control,
            "created_at": datetime(2026, 4, 1, tzinfo=timezone.utc),
            "shop_id": shop_one,
            "customer_id": customer_one,
            "type": "follow_up",
            "due_at": datetime(2026, 4, 10, tzinfo=timezone.utc),
            "status": "OPEN",
            "payload": '{"marker": "other-type"}',
        },
        {
            "id": other_shop_control,
            "created_at": datetime(2026, 4, 1, tzinfo=timezone.utc),
            "shop_id": shop_two,
            "customer_id": customer_three,
            "type": "overdue",
            "due_at": datetime(2026, 4, 10, tzinfo=timezone.utc),
            "status": "OPEN",
            "payload": '{"marker": "other-shop"}',
        },
    ]

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO shops (id, created_at, name, timezone)
                VALUES (:id, :created_at, :name, :timezone)
                """
            ),
            shops,
        )
        connection.execute(
            text(
                """
                INSERT INTO customers (
                    id, created_at, shop_id, name, normalized_name
                )
                VALUES (
                    :id, :created_at, :shop_id, :name, :normalized_name
                )
                """
            ),
            customers,
        )
        connection.execute(
            text(
                """
                INSERT INTO reminders (
                    id, created_at, shop_id, customer_id, type,
                    due_at, status, payload
                )
                VALUES (
                    :id, :created_at, :shop_id, :customer_id, :type,
                    :due_at, :status, CAST(:payload AS jsonb)
                )
                """
            ),
            reminders,
        )

    command.upgrade(config, "0003")

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, shop_id, customer_id, type, due_at, status, payload
                FROM reminders
                ORDER BY id
                """
            )
        ).mappings().all()
        constraint_names = {
            constraint["name"]
            for constraint in inspect(connection).get_unique_constraints(
                "reminders"
            )
        }

    assert {row["id"] for row in rows} == {
        open_tie_winner,
        open_over_resolved,
        other_type_control,
        other_shop_control,
    }
    kept_by_id = {row["id"]: row for row in rows}
    assert kept_by_id[open_tie_winner]["status"] == "OPEN"
    assert kept_by_id[open_tie_winner]["due_at"] == datetime(
        2026, 2, 12, tzinfo=timezone.utc
    )
    assert kept_by_id[open_tie_winner]["payload"] == {
        "marker": "same-time-higher-uuid"
    }
    assert kept_by_id[open_over_resolved]["status"] == "OPEN"
    assert kept_by_id[open_over_resolved]["payload"] == {
        "marker": "open-priority"
    }
    assert kept_by_id[other_type_control]["type"] == "follow_up"
    assert kept_by_id[other_shop_control]["shop_id"] == shop_two
    assert CONSTRAINT_NAME in constraint_names

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO reminders (
                        id, created_at, shop_id, customer_id, type,
                        due_at, status, payload
                    )
                    VALUES (
                        :id, :created_at, :shop_id, :customer_id, :type,
                        :due_at, :status, CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "created_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
                    "shop_id": shop_one,
                    "customer_id": customer_one,
                    "type": "overdue",
                    "due_at": datetime(2026, 5, 10, tzinfo=timezone.utc),
                    "status": "OPEN",
                    "payload": "{}",
                },
            )
