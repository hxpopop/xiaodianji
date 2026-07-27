from datetime import datetime, timezone
from uuid import uuid4

from alembic import command
from sqlalchemy import inspect, text

from tests.migrations.upgrade.test_reminder_unique_upgrade import (
    migration_database,
)


def test_downgrade_preserves_duplicate_shop_cases_and_rewrites_all_keys(
    migration_database,
) -> None:
    config, engine = migration_database
    command.upgrade(config, "0003")
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE evaluation_cases "
                "DROP CONSTRAINT IF EXISTS uq_evaluation_case_shop_stable_key"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE evaluation_cases "
                "ADD CONSTRAINT uq_evaluation_case_stable_key "
                "UNIQUE (stable_key)"
            )
        )
    command.upgrade(config, "0004")

    shop_ids = [uuid4(), uuid4()]
    case_ids = [uuid4(), uuid4()]
    run_ids = [uuid4(), uuid4()]
    result_ids = [uuid4(), uuid4()]
    created_at = datetime(2026, 7, 27, tzinfo=timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO shops (id, created_at, name, timezone) "
                "VALUES (:id, :created_at, :name, 'Asia/Shanghai')"
            ),
            [
                {"id": shop_ids[0], "created_at": created_at, "name": "甲店"},
                {"id": shop_ids[1], "created_at": created_at, "name": "乙店"},
            ],
        )
        connection.execute(
            text(
                "INSERT INTO evaluation_cases "
                "(id, created_at, shop_id, stable_key, input_type, "
                "input_payload, expected_json, tags) "
                "VALUES (:id, :created_at, :shop_id, 'shared-fixed-case', "
                "'text', '{}'::jsonb, '{}'::jsonb, '[]'::jsonb)"
            ),
            [
                {
                    "id": case_ids[0],
                    "created_at": created_at,
                    "shop_id": shop_ids[0],
                },
                {
                    "id": case_ids[1],
                    "created_at": created_at,
                    "shop_id": shop_ids[1],
                },
            ],
        )
        connection.execute(
            text(
                "INSERT INTO evaluation_runs "
                "(id, created_at, shop_id, model_name, started_at, summary_json) "
                "VALUES (:id, :created_at, :shop_id, 'test', "
                ":created_at, '{}'::jsonb)"
            ),
            [
                {
                    "id": run_ids[0],
                    "created_at": created_at,
                    "shop_id": shop_ids[0],
                },
                {
                    "id": run_ids[1],
                    "created_at": created_at,
                    "shop_id": shop_ids[1],
                },
            ],
        )
        connection.execute(
            text(
                "INSERT INTO evaluation_results "
                "(id, created_at, run_id, case_id, predicted_json, "
                "field_scores, latency_ms) "
                "VALUES (:id, :created_at, :run_id, :case_id, "
                "'{}'::jsonb, '{}'::jsonb, 1)"
            ),
            [
                {
                    "id": result_ids[0],
                    "created_at": created_at,
                    "run_id": run_ids[0],
                    "case_id": case_ids[0],
                },
                {
                    "id": result_ids[1],
                    "created_at": created_at,
                    "run_id": run_ids[1],
                    "case_id": case_ids[1],
                },
            ],
        )

    command.downgrade(config, "0003")

    with engine.connect() as connection:
        cases = connection.execute(
            text("SELECT id, stable_key FROM evaluation_cases ORDER BY id")
        ).mappings().all()
        results = connection.execute(
            text("SELECT run_id, case_id FROM evaluation_results ORDER BY id")
        ).mappings().all()
        constraint_columns = [
            constraint["column_names"]
            for constraint in inspect(connection).get_unique_constraints(
                "evaluation_cases"
            )
        ]

    assert len(cases) == len(run_ids) == len(results) == 2
    assert {case["id"] for case in cases} == set(case_ids)
    assert {result["run_id"] for result in results} == set(run_ids)
    assert {result["case_id"] for result in results} == set(case_ids)
    assert {case["stable_key"] for case in cases} == {
        f"legacy-{case_ids[0]}",
        f"legacy-{case_ids[1]}",
    }
    assert all(len(case["stable_key"]) < 120 for case in cases)
    assert ["stable_key"] in constraint_columns
