set positional-arguments
set working-directory := '..'

# Run tests, e.g. `just qa test -k schema`
test *args:
    uv run pytest "$@"

# Run tests with coverage report (HTML in htmlcov/)
cov:
    uv run coverage run -m pytest
    uv run coverage report
    uv run coverage html

# Lint with ruff and djlint
lint:
    uv run ruff check .
    uv run djlint project/templates --lint

# Format and auto-fix with ruff
fmt:
    uv run ruff check --fix .
    uv run ruff format .

# Type-check with mypy
types:
    uv run mypy project config

# Fail if model changes are missing migrations
migrations:
    uv run python manage.py makemigrations --check --dry-run

# Django deploy checks against production settings (dummy secrets)
deploy-check:
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_SECRET_KEY="check-$(openssl rand -hex 32)" \
    DJANGO_ADMIN_URL=admin/ \
    uv run python manage.py check --deploy --fail-level WARNING

# Everything CI would run
check: lint types migrations test deploy-check
