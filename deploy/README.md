# VPS deployment

Single server: Caddy (TLS, `/media/`) → gunicorn (Django + WhiteNoise for `/static/`),
plus Celery worker and beat under systemd. SQLite on local disk, replicated by Litestream.

## Layout

```
/srv/project/app     git checkout (owned by the `project` user)
/srv/project/.env    production env (from production.env.example, chmod 600)
/srv/project/data/   db.sqlite3, celery-broker.sqlite3, media/, cache/
```

## First install (Debian/Ubuntu)

```bash
sudo apt install caddy sqlite3 git
# Install uv and just for the project user; install litestream from its release .deb
sudo useradd --system --create-home --home-dir /srv/project project
sudo -u project git clone <repo> /srv/project/app
sudo -u project mkdir -p /srv/project/data/media
sudo -u project cp /srv/project/app/deploy/production.env.example /srv/project/.env  # then edit
sudo chmod 600 /srv/project/.env

sudo cp deploy/project-*.service /etc/systemd/system/
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile          # set your domain
sudo cp deploy/litestream.yml /etc/litestream.yml      # set bucket + credentials
sudo systemctl daemon-reload
sudo systemctl enable --now project-web project-worker project-beat litestream
sudo systemctl reload caddy

cd /srv/project/app && sudo -u project --preserve-env=PATH just deploy release
```

Give `project` passwordless sudo for `systemctl restart project-*` only, or restart the services manually after `release`.

## Updates

```bash
cd /srv/project/app && git pull && just deploy release
```

## Backups

Litestream streams every SQLite change to the replica. Also run `just db backup`
(with `SQLITE_PATH=/srv/project/data/db.sqlite3`) for point-in-time snapshots.
Restore with `litestream restore -o /srv/project/data/db.sqlite3 /srv/project/data/db.sqlite3`.
