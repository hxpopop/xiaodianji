from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_seed_script_runs_in_backend_container() -> None:
    script = (ROOT / "scripts" / "seed-demo.ps1").read_text(encoding="utf-8")

    assert "docker compose exec -T backend python -m xiaodianji.demo.seed" in script


def test_evaluation_script_defaults_to_gateway_port() -> None:
    script = (ROOT / "scripts" / "run-evaluation.ps1").read_text(encoding="utf-8")

    assert "http://localhost:8080/api/v1" in script
