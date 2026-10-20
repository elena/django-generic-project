# project task runner. Run `just` to list recipes, `just --list <module>` for a module.

set dotenv-load
set positional-arguments

mod db '.just/db.just'
mod celery '.just/celery.just'
mod qa '.just/qa.just'
mod deploy '.just/deploy.just'

# List available recipes
default:
    @just --list --list-submodules

# First-time setup: install deps, migrate, create a superuser
setup:
    uv sync
    @test -f .env || cp .env.example .env
    uv run python manage.py migrate
    uv run python manage.py createsuperuser

# Run the dev server (Celery tasks run inline)
dev port="8000":
    uv run python manage.py runserver_plus 0.0.0.0:{{ port }}

# Run dev server + Celery worker + beat together (Ctrl-C stops all)
dev-all port="8000":
    #!/usr/bin/env bash
    set -euo pipefail
    export CELERY_TASK_ALWAYS_EAGER=false
    trap 'kill 0' EXIT
    uv run celery -A config.celery_app worker -l info --pool=solo &
    uv run celery -A config.celery_app beat -l info &
    uv run python manage.py runserver_plus 0.0.0.0:{{ port }}

# Run any manage.py command, e.g. `just manage startapp blog`
manage *args:
    uv run python manage.py "$@"

# Django shell with models auto-imported
shell:
    uv run python manage.py shell_plus

# Add dependencies, e.g. `just add httpx` or `just add --dev pytest-mock`
add *pkgs:
    uv add "$@"

# Upgrade all locked dependencies
upgrade:
    uv lock --upgrade
    uv sync

# Export the GraphQL schema SDL to schema.graphql
graphql-schema:
    uv run python manage.py export_schema config.schema --path schema.graphql

# Remove caches and build artefacts
clean:
    find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
    rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage staticfiles
