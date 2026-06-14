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
| Lemonade | 13305 | http://127.0.0.1:13305/ |
| **This dashboard** | **9090** | http://127.0.0.1:9090/ |
| Docker Desktop | daemon | managed via dashboard |
| Cursor Postgres | 5433 | docker container |
| HA Postgres | 5432 | docker container |

Secondary ports (documented in `config/services.yaml`):

- taOS LiteLLM proxy: 7834
- taOS browser proxy: 6970
- HA Postgres (docker): 5432
- Cursor Postgres (docker): 5433

## Install

```bash
cd /Users/oibaf/Projects/startup-apps
./scripts/install.sh
```

This will:

1. Create a Python venv and install dependencies
2. Install a LaunchAgent so the manager starts at login
3. Show a menu bar icon (`●` all up, `◐` partial, `○` all down)
4. Serve the observability dashboard on port 9090

## Port management

All ports live in one file:

```
config/services.yaml
```

The dashboard shows:

- Live health for each service
- Docker Desktop daemon status and managed containers
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

Per-service scripts:

```bash
./scripts/services/start-taos.sh
./scripts/services/stop-9router.sh
```

## Notes

- **Lemonade** autostarts at login using the built binary at `/Users/oibaf/Projects/lemonade/build/lemond`.
- **Docker Desktop** starts automatically at login (before Postgres containers). Enable **Start Docker Desktop when you log in** in Docker settings for faster startup.
- **Postgres on 5432**: HA agent docker-compose maps Postgres to host port 5432. If Homebrew `postgresql@16` is already using 5432, either stop it or change the HA compose port mapping before enabling HA autostart.
- **Dev UI port 8082** is shared by HA agent and Cursor dashboard Trunk dev servers — only one can use it at a time during development.
