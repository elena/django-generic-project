set positional-arguments
set working-directory := '..'

app := "config.celery_app"

# Run a Celery worker (with CELERY_TASK_ALWAYS_EAGER=false)
worker *args:
    CELERY_TASK_ALWAYS_EAGER=false uv run celery -A {{ app }} worker -l info "$@"

# Run Celery beat (periodic tasks, schedules managed in the admin)
beat *args:
    uv run celery -A {{ app }} beat -l info "$@"

# Show registered tasks and worker status
inspect:
    uv run celery -A {{ app }} inspect registered

# Discard all queued tasks
[confirm("Purge all queued Celery tasks?")]
purge:
    uv run celery -A {{ app }} purge -f
