# Recipes run ON the VPS from the project checkout (see deploy/README.md).
set positional-arguments
set working-directory := '..'

export DJANGO_SETTINGS_MODULE := "config.settings.production"

# Collect static files for WhiteNoise
collectstatic:
    uv run python manage.py collectstatic --noinput

# Install locked prod deps, migrate, collect static, restart services
release:
    uv sync --locked --no-dev
    uv run python manage.py migrate --noinput
    uv run python manage.py collectstatic --noinput
    sudo systemctl restart project-web project-worker project-beat

# Tail logs of all project services
logs:
    journalctl -f -u project-web -u project-worker -u project-beat

# Status of all project services
status:
    systemctl status project-web project-worker project-beat --no-pager
