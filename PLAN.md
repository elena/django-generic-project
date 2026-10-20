# Plan: cookiecutter-django project "project" (no Docker, SQLite, uv, just, Celery, Strawberry)

## Context
Set up a new Django project in `/Users/elenaw/Code/temp4`, which is empty apart from `.git`. It will be the base for custom apps added later.

Requirements:
- User auth for public users and admin users, with login by **username or email** and optional email verification
- Static and media file serving
- `/admin/` and a GraphQL API using Strawberry
- Celery
- SQLite in dev and in production on a VPS, with an env-var switch to Postgres later
- uv, Python 3.14.4 through pyenv
- A justfile, split into modules under `.just/`

What I found:
- The cached template (`~/.cookiecutters/cookiecutter-django`, commit 62418f80) is behind upstream, so it gets refreshed first. It targets Django 6.0 and pins `requires-python = "==3.14.*"`. Its post-gen hook runs `uv add` from `requirements/*.txt` and then deletes `requirements/`, so the project ends up with `pyproject.toml` and `uv.lock`.
- With `use_docker=n` the hook **deletes the template's justfile**, which is Docker-only anyway. We write our own.
- The template's DB default is Postgres (`config/settings/base.py`, `env.db("DATABASE_URL", default="postgres://...")`). Celery and the cache are set up for Redis (`REDIS_URL`, django-redis). Redis isn't installed locally.
- Local tools available: pyenv 3.14.4, uv 0.9.5, just 1.58, cookiecutter 2.7.1.

## Step 0: Save this plan
Copy this plan into the project as `/Users/elenaw/Code/temp4/PLAN.md` before doing anything else, and keep it in the repo.

## Step 1: Generate
```bash
cd /Users/elenaw/Code/temp4
pyenv local 3.14.4                      # writes .python-version (uv also honours it)
cookiecutter https://github.com/cookiecutter/cookiecutter-django \
  --output-dir /tmp/cc --no-input \
  project_name=project project_slug=project username_type=username \
  use_docker=n cloud_provider=None mail_service="Other SMTP" rest_api=None \
  use_async=n use_celery=y use_whitenoise=y use_heroku=n use_sentry=n \
  frontend_pipeline=None mail_catcher=None ci_tool=Github editor="VS Code" \
  keep_local_envs_in_vcs=y open_source_license="Not open source" timezone=UTC
```
Then move `/tmp/cc/project/` into `temp4`, dotfiles included, without overwriting `.git`. Set `.python-version` to `3.14.4`. Create the virtualenv from pyenv's interpreter with `uv venv --python "$(pyenv which python)"`, then run `uv sync`.

## Step 2: Database, SQLite first and Postgres ready
In `config/settings/base.py`:
- `DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}`
- If the engine is SQLite, add the production-safe options: `"transaction_mode": "IMMEDIATE"` and `"init_command"` with `PRAGMA journal_mode=WAL; synchronous=NORMAL; busy_timeout=5000; foreign_keys=ON; cache_size=-20000`. Postgres ignores this block.
- Keep `ATOMIC_REQUESTS = True`. Read `CONN_MAX_AGE` from env.

In production, `DATABASE_URL=sqlite:////srv/project/data/db.sqlite3`. Moving to Postgres later means setting `DATABASE_URL=postgres://...`, adding `psycopg[binary]` back with uv, and loading data with `dumpdata`/`loaddata` or pgloader. No code changes.

Keep `psycopg` out of the dependencies until it's needed. Make sure no Postgres-only fields get used.

## Step 3: Celery on a SQLite broker, no Redis
- Add deps `sqlalchemy` (for kombu's `sqla` transport) and `django-celery-results`. Remove `redis`, `hiredis` and `django-redis`.
- In `base.py`:
  - `CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=f"sqla+sqlite:///{BASE_DIR / 'celery-broker.sqlite3'}")`
  - `CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")`
  - Add `django_celery_results` to `THIRD_PARTY_APPS`.
  - Drop the `REDIS_URL` and SSL lines.
  - Keep the template's `config/celery_app.py`, `project/users/tasks.py`, and django-celery-beat with `DatabaseScheduler`.
- The broker gets its own file, separate from the app DB, so queue polling doesn't compete with app writes for the lock.
- In `local.py`: `CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)`, so `runserver` works without a worker. `just dev-all` sets it to `False`.
- Cache in `production.py`: replace django-redis with `env.cache("CACHE_URL", default="filecache:///var/tmp/project_cache")`. Later this can become `CACHE_URL=redis://...`.
- To grow later: set `CELERY_BROKER_URL=redis://...` and add `redis` back.

## Step 4: Auth (allauth)
In `base.py`:
- `ACCOUNT_LOGIN_METHODS = {"username", "email"}`
- `ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]` (the template already sets this for the username type)
- `ACCOUNT_EMAIL_VERIFICATION = env("DJANGO_ACCOUNT_EMAIL_VERIFICATION", default="optional")`

Admin users use `/admin/` (staff or superuser accounts). Its path comes from `DJANGO_ADMIN_URL` in production, as the template already does. Dev email goes to the console backend.

## Step 5: GraphQL (Strawberry)
- Install with `uv add strawberry-graphql strawberry-graphql-django`, then add `strawberry_django` to `THIRD_PARTY_APPS`.
- New `project/users/schema.py`:
  - `UserType` built with `strawberry_django.type(User)`, exposing `id`, `username`, `email` and `name`.
  - `Query.me`, guarded by the `IsAuthenticated` extension.
  - `Mutation`:
    - `login(identifier, password)`: resolves username or email through allauth's `AuthenticationBackend`, then calls `django.contrib.auth.login`.
    - `logout`, from `strawberry_django.auth.logout`.
    - `register`, which uses allauth's signup flow so email verification still applies.
- New `config/schema.py`: merges each app's Query and Mutation with `strawberry.tools.merge_types` and adds `DjangoOptimizerExtension`. New apps add their own `schema.py` here.
- `config/urls.py`: `path("graphql/", GraphQLView.as_view(schema=schema, graphql_ide="graphiql" if settings.DEBUG else None))`. It uses session auth with CSRF protection kept on.
- Tests in `project/users/tests/test_schema.py`:
  - `me` as an anonymous user and as a logged-in user
  - login by username and by email

## Step 6: Static and media
- Static files: WhiteNoise in dev and prod; the template already does this.
- Media in dev: the template's `static(MEDIA_URL)` route in `urls.py`.
- Media in prod: `MEDIA_ROOT` from the env `DJANGO_MEDIA_ROOT` (default `BASE_DIR/media`), served by Caddy (see Step 8).

## Step 7: justfile and `.just/` modules
The root `justfile` sets `set dotenv-load`, defines a `default` recipe that runs `just --list`, and declares the modules: `mod db '.just/db.just'`, `mod celery '.just/celery.just'`, `mod qa '.just/qa.just'`, `mod deploy '.just/deploy.just'`.

| Recipe | Command |
|---|---|
| `just setup` | `uv sync` → `migrate` → `createsuperuser` (prompts) |
| `just dev` | `uv run python manage.py runserver_plus` |
| `just dev-all` | runserver + Celery worker + beat together, with `CELERY_TASK_ALWAYS_EAGER=false` (background jobs with `trap` cleanup) |
| `just manage *args` / `just shell` | `manage.py <args>` / `shell_plus` |
| `just add *pkgs` / `just upgrade` | `uv add` / `uv lock --upgrade && uv sync` |
| `db::migrate`, `db::makemigrations`, `db::reset`, `db::backup` | `db::reset` asks for confirmation. `db::backup` uses `sqlite3 .backup` into `backups/`. |
| `celery::worker`, `celery::beat`, `celery::purge` | `uv run celery -A config.celery_app ...` |
| `qa::test`, `qa::cov`, `qa::lint`, `qa::fmt`, `qa::types`, `qa::check` | pytest, coverage, `ruff check`, `ruff format`, mypy, and `check` runs all of them plus `manage.py check --deploy` against production settings |
| `deploy::collectstatic`, `deploy::release` | `collectstatic --noinput`, then migrate and collectstatic on the server |

## Step 8: VPS deploy scaffolding (small, in `deploy/`)
- `Caddyfile`: reverse-proxy to gunicorn, and serve `/media/*` from `MEDIA_ROOT`. Caddy handles TLS automatically.
- `systemd` units for gunicorn, the Celery worker, and Celery beat.
- `litestream.yml`: continuous replication of `db.sqlite3` to any S3-compatible bucket or an SFTP target. This is the only cloud piece, and it's only for backups.
- `.envs/.production/.django.example`, documenting `DATABASE_URL`, `CELERY_BROKER_URL`, `CACHE_URL`, `DJANGO_MEDIA_ROOT` and the other env vars.

Other housekeeping:
- `.gitignore`: add `*.sqlite3*`, `media/` and `backups/`.
- Update the README with the just commands and how to move to Postgres or Redis later.

## Verification
1. `just setup`, then `just qa::check`: tests, ruff and mypy pass, and `check --deploy` shows no errors.
2. `just dev`, then:
   - sign up at `/accounts/signup/` (the verification email prints to the console, and you can log in before verifying)
   - log in with the username, then again with the email
   - open `/admin/` as the superuser
3. Open `/graphql/` in GraphiQL:
   - `{ me { username } }` as an anonymous user returns an error
   - `login` with the email works, then `me` returns the user
4. `just dev-all`: in `shell_plus`, `get_users_count.delay()` and check the worker log shows it ran. Check the result is recorded in the admin under "Task results".
5. Static: a CSS file loads with `DEBUG=False` through WhiteNoise. Media: upload a file through the admin and fetch it at `/media/...`.
6. Postgres switch, sanity check only: `manage.py check` with `DATABASE_URL=postgres://x/y` parses without needing code changes.
7. Make the first git commit of the result.
