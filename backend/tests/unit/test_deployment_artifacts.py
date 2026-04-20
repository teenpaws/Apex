"""Tests that all deployment configuration files exist and contain required content."""
from pathlib import Path

# backend/tests/unit/ → backend/tests/ → backend/ → repo root
REPO_ROOT = Path(__file__).parent.parent.parent.parent


# ── Task 4: Backend Dockerfile ────────────────────────────────────────────────

def test_backend_dockerfile_exists():
    df = REPO_ROOT / "backend" / "Dockerfile"
    assert df.exists(), "backend/Dockerfile must exist"


def test_backend_dockerfile_uses_gunicorn():
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "gunicorn" in content.lower()


def test_backend_dockerfile_uses_nonroot_user():
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "USER" in content


def test_backend_dockerfile_exposes_8000():
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "8000" in content


# ── Task 5: Frontend Dockerfile + Next.js standalone ─────────────────────────

def test_frontend_dockerfile_exists():
    df = REPO_ROOT / "frontend" / "Dockerfile"
    assert df.exists(), "frontend/Dockerfile must exist"


def test_frontend_dockerfile_has_standalone_reference():
    content = (REPO_ROOT / "frontend" / "Dockerfile").read_text()
    assert "standalone" in content


def test_frontend_dockerfile_exposes_3000():
    content = (REPO_ROOT / "frontend" / "Dockerfile").read_text()
    assert "3000" in content


def test_nextconfig_has_standalone_output():
    content = (REPO_ROOT / "frontend" / "next.config.ts").read_text()
    assert "standalone" in content


# ── Task 6: Nginx config ──────────────────────────────────────────────────────

def test_nginx_conf_exists():
    conf = REPO_ROOT / "nginx" / "nginx.conf"
    assert conf.exists(), "nginx/nginx.conf must exist"


def test_nginx_conf_proxies_api_to_backend():
    content = (REPO_ROOT / "nginx" / "nginx.conf").read_text()
    assert "proxy_pass" in content
    assert "/api/" in content


def test_nginx_conf_proxies_root_to_frontend():
    content = (REPO_ROOT / "nginx" / "nginx.conf").read_text()
    found_root_location = any(
        "location /" in line and "/api" not in line
        for line in content.split("\n")
    )
    assert found_root_location, "nginx.conf must have a root location / block"


def test_nginx_conf_listens_on_80():
    content = (REPO_ROOT / "nginx" / "nginx.conf").read_text()
    assert "listen 80" in content


# ── Task 7: docker-compose.prod.yml ──────────────────────────────────────────

def test_docker_compose_prod_exists():
    f = REPO_ROOT / "docker-compose.prod.yml"
    assert f.exists(), "docker-compose.prod.yml must exist"


def test_docker_compose_prod_has_all_services():
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    for svc in ["redis:", "backend:", "celery_worker:", "frontend:", "nginx:"]:
        assert svc in content, f"docker-compose.prod.yml missing service: {svc}"


def test_docker_compose_prod_backend_depends_on_redis():
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    assert "redis" in content
    assert content.find("redis:") < content.find("backend:")


def test_docker_compose_prod_nginx_exposes_port_80():
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    assert "80:80" in content


# ── Task 8: README + .env.prod.example + migration script ────────────────────

def test_env_prod_example_exists():
    f = REPO_ROOT / "backend" / ".env.prod.example"
    assert f.exists(), "backend/.env.prod.example must exist"


def test_env_prod_example_has_required_keys():
    content = (REPO_ROOT / "backend" / ".env.prod.example").read_text()
    for key in ["DATABASE_URL", "SUPABASE_URL", "ANTHROPIC_API_KEY",
                "MOCK_AGENTS", "USE_MOCK_DATA", "ENVIRONMENT", "ALLOWED_ORIGINS"]:
        assert key in content, f".env.prod.example missing key: {key}"


def test_readme_exists():
    assert (REPO_ROOT / "README.md").exists(), "README.md must exist"


def test_readme_has_quickstart_section():
    content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert any(s in content for s in ("Quick Start", "Quickstart", "Getting Started"))


def test_readme_references_docker_compose():
    content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "docker-compose.prod.yml" in content or "docker compose" in content.lower()


def test_migration_script_exists():
    f = REPO_ROOT / "backend" / "scripts" / "run_migrations.sh"
    assert f.exists(), "backend/scripts/run_migrations.sh must exist"
