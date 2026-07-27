from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_compose_declares_required_services() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for service in ("frontend", "backend", "postgres", "minio", "nginx"):
        assert f"  {service}:" in compose
    assert "healthcheck:" in compose
    assert "postgres_data:" in compose
    assert "minio_data:" in compose


def test_example_environment_contains_no_real_secret() -> None:
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "CHANGE_ME" in env_example
    assert "sk-" not in env_example


def test_nginx_exposes_frontend_and_api() -> None:
    nginx = (ROOT / "deployment" / "nginx.conf").read_text(encoding="utf-8")
    assert "proxy_pass http://backend:8000" in nginx
    assert "proxy_pass http://frontend:80" in nginx
