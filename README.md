# project

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Django 6 on Python 3.14, managed with [uv](https://docs.astral.sh/uv/) and [just](https://just.systems).
SQLite everywhere by default (dev and a single VPS), Celery on a SQLite broker,
allauth for accounts, Strawberry for GraphQL. No Docker, no Redis, no Postgres required.

## Quick start

```bash
pyenv install 3.14.4   # if needed; .python-version pins it
just setup             # uv sync, copy .env.example -> .env, migrate, createsuperuser
just dev               # http://localhost:8000
```

Run `just` to list every recipe. Modules: `just db …`, `just celery …`, `just qa …`, `just deploy …`.

| URL | What |
|---|---|
| `/accounts/signup/`, `/accounts/login/` | Public users (allauth). Log in with **username or email**; email verification is optional (emails print to the console in dev). |
| `/admin/` | Admin users (`is_staff`). Path is `DJANGO_ADMIN_URL` in production. |
| `/graphql/` | GraphQL API, with GraphiQL in dev. Session auth + CSRF. |
| `/static/`, `/media/` | WhiteNoise / Django in dev; WhiteNoise + Caddy in production. |

## GraphQL

`config/schema.py` merges each app's `Query` / `Mutation` from its `schema.py`
(see `project/users/schema.py`). Built-in operations:

```graphql
mutation { login(login: "alice@example.com", password: "...") { user { username } errors { field messages } } }
mutation { register(username: "alice", email: "alice@example.com", password: "...") { user { id } errors { field messages } } }
mutation { logout }
query    { me { id username email name isStaff } }
```

Browser clients: `GET /graphql/` sets the `csrftoken` cookie; send it back as the
`X-CSRFToken` header on POSTs. `just graphql-schema` exports the SDL.

## Celery

In dev, tasks run inline (`CELERY_TASK_ALWAYS_EAGER=true`), so only `just dev` is needed.
To exercise a real worker: `just dev-all` (server + worker + beat), or `just celery worker`
and `just celery beat` separately. Results are stored in the DB (visible in the admin).
Periodic tasks are managed in the admin (django-celery-beat).

## Adding an app

```bash
mkdir project/blog && just manage startapp blog project/blog
```

Then set `name = "project.blog"` in its `apps.py`, add it to `LOCAL_APPS` in
`config/settings/base.py`, and (for GraphQL) add `project/blog/schema.py` to `config/schema.py`.

## Quality

`just qa check` runs ruff, djlint, mypy, missing-migration check, pytest and
`check --deploy` against production settings. `just qa fmt` auto-formats.

## Configuration and growing out of SQLite

All settings come from env vars (`.env` locally, see `.env.example`;
`deploy/production.env.example` for production).

| Need | Change |
|---|---|
| Postgres | `just add "psycopg[binary]"`, set `DATABASE_URL=postgres://…`, migrate, move data (`dumpdata`/`loaddata` or pgloader). |
| Redis broker | `just add redis`, set `CELERY_BROKER_URL=redis://localhost:6379/0`. |
| Redis cache | set `CACHE_URL=redis://localhost:6379/1` (needs `redis` installed). |
| Mandatory email verification | `DJANGO_ACCOUNT_EMAIL_VERIFICATION=mandatory` |

Avoid PostgreSQL-only model features (`ArrayField`, `HStoreField`, `contrib.postgres`)
while SQLite is the database.

## Deployment

Single VPS with Caddy + gunicorn + systemd + Litestream: see [deploy/README.md](deploy/README.md).
