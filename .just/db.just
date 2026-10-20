set positional-arguments
set working-directory := '..'

db_file := env("SQLITE_PATH", "db.sqlite3")

# Apply migrations
migrate *args:
    uv run python manage.py migrate "$@"

# Create migrations, e.g. `just db makemigrations users`
makemigrations *args:
    uv run python manage.py makemigrations "$@"

# Show migration status
status:
    uv run python manage.py showmigrations

# Open a SQL shell on the configured database
shell:
    uv run python manage.py dbshell

# Online backup of the SQLite DB into backups/ (safe while running)
backup:
    mkdir -p backups
    sqlite3 {{ db_file }} ".backup 'backups/db-$(date +%Y%m%d-%H%M%S).sqlite3'"
    @ls -1t backups | head -1

# Restore the SQLite DB from a backup file (stop the app first)
[confirm("Overwrite the current database with the backup?")]
restore file:
    cp {{ db_file }} {{ db_file }}.pre-restore 2>/dev/null || true
    cp "{{ file }}" {{ db_file }}

# Delete the local SQLite DB + broker and re-migrate (dev only)
[confirm("Delete the local database and start fresh?")]
reset:
    rm -f {{ db_file }} {{ db_file }}-wal {{ db_file }}-shm celery-broker.sqlite3*
    uv run python manage.py migrate
