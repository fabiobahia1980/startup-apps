# Startup Apps

Unified manager for local AI/observability services: login startup, menu bar status, and a single observability dashboard with a canonical port registry.

## Services

| Service | Port | UI |
|---------|------|-----|
| OMLX | 8000 | http://127.0.0.1:8000/admin |
| taOS | 6969 | http://127.0.0.1:6969/ |
| HA Agent Observability | 8080 | http://127.0.0.1:8080/ |
| Cursor AI Observability | 8081 | http://127.0.0.1:8081/ |
| 9router | 20128 | http://127.0.0.1:20128/dashboard |
| OpenCode | 3344 | http://127.0.0.1:3344/ |
| Lemonade | 13305 | http://127.0.0.1:13305/ |
| **This dashboard** | **9090** | http://127.0.0.1:9090/ |
| OrbStack | daemon | managed via dashboard |
| Cursor Postgres | 5433 | docker container |
| HA Postgres | 5434 | docker container |

Secondary ports (documented in `config/services.yaml`):

- taOS LiteLLM proxy: 7834
- taOS browser proxy: 6970
- HA Postgres (docker): 5434 — avoids conflict with Homebrew Postgres on 5432
- Cursor Postgres (docker): 5433

## Install

```bash
cd /Users/oibaf/Projects/startup-apps
./scripts/install.sh
```

This will:

1. Create a Python venv and install dependencies
2. Install a LaunchAgent so the manager starts at login
3. Show a menu bar count (e.g. `8/8` for visible services) that refreshes every 5 seconds
4. Serve the observability dashboard on port 9090

## Port management

All ports live in one file:

```
config/services.yaml
```

The dashboard shows:

- Live health for each service
- OrbStack daemon status and managed containers
- Which process owns each port (`lsof`)
- Registry conflicts (duplicate TCP assignments)
- Start / stop / restart controls

Edit `config/services.yaml` to change ports, then restart the manager.

## Manual commands

```bash
# Menu bar + dashboard (also starts autostart services)
.venv/bin/python -m startup_manager menubar

# Dashboard only
.venv/bin/python -m startup_manager dashboard

# Start all autostart services once
.venv/bin/python -m startup_manager autostart
```

Menu bar actions: **Start autostart services**, **Stop all services** (stops managed apps; manager keeps running), **Quit manager** (manager only).

Per-service scripts:

```bash
./scripts/services/start-taos.sh
./scripts/services/stop-9router.sh
```

## Notes

- **Lemonade** autostarts at login using the built binary at `/Users/oibaf/Projects/lemonade/build/lemond`.
- **OrbStack** starts automatically at login (before Postgres containers). Enable **Start at login** in OrbStack settings for faster startup. Uninstall Docker Desktop to avoid conflicts with the Docker socket.
- **HA Postgres** runs on host port **5434** (OrbStack maps `5434:5432`) so it does not conflict with Homebrew `postgresql@16` on 5432. Set `DATABASE_URL=...@127.0.0.1:5434/...` in `ha-local-agent-mm/.env`.
- **OMLX** is started by the Homebrew service (`brew services start jundot/omlx/omlx`). If the **oMLX** app is also a macOS Login Item, it will try to start a second server on port 8000. Use the brew instance at http://127.0.0.1:8000/admin and remove the login item: `./scripts/fix-omlx-login-item.sh` (or System Settings → General → Login Items).
- **Dev UI port 8082** is shared by HA agent and Cursor dashboard Trunk dev servers — only one can use it at a time during development.

## Doctor

Check for known autostart conflicts and audit all registered TCP ports:

```bash
./scripts/doctor.sh
```

Reports oMLX login-item conflicts, LaunchAgent and dashboard health, registry port conflicts, and live listener status per port.

Run locally: `python scripts/validate.py` (also runs in GitHub Actions on push/PR to `main`).

## Post-reboot e2e test

Validate login autostart after a reboot:

```bash
# Run immediately (no wait)
./scripts/e2e-reboot-test.sh

# Install one-shot test that runs 120s after next login
./scripts/install-e2e-reboot-test.sh

# Remove one-shot agent after a successful run
./scripts/remove-e2e-reboot-test.sh
```

Log: `~/.startup-apps/e2e-reboot.log`
