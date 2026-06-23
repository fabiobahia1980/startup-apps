from __future__ import annotations

import asyncio
import threading
from dataclasses import asdict
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .config import load_config, visible_services
from .docker import docker_overview
from .health import ServiceState, check_all
from .ports import collect_port_assignments, find_port_conflicts
from .supervisor import SupervisorError, restart_service, start_autostart_services, start_service, stop_service

config = load_config()
app = FastAPI(title="Startup Apps", version="1.0.0")


def _status_payload() -> dict[str, Any]:
    services = visible_services(config)
    statuses = asyncio.run(check_all(services))
    up = sum(1 for s in statuses if s.state == ServiceState.UP)
    degraded = sum(1 for s in statuses if s.state == ServiceState.DEGRADED)
    down = sum(1 for s in statuses if s.state in {ServiceState.DOWN, ServiceState.STARTING})
    return {
        "summary": {
            "total": len(statuses),
            "up": up,
            "degraded": degraded,
            "down": down,
        },
        "services": [asdict(status) for status in statuses],
        "ports": [asdict(item) for item in collect_port_assignments(config)],
        "conflicts": [
            {
                "port": conflict.port,
                "assignments": [asdict(item) for item in conflict.assignments],
            }
            for conflict in find_port_conflicts(config)
        ],
        "dashboard_url": f"http://{config.dashboard_host}:{config.dashboard_port}",
        "docker": docker_overview(config),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"ok": "true"}


@app.get("/api/status")
def status() -> dict[str, Any]:
    return _status_payload()


@app.post("/api/services/{service_id}/start")
def api_start(service_id: str) -> dict[str, str]:
    service = config.services.get(service_id)
    if not service or service.hidden:
        raise HTTPException(status_code=404, detail="Service not found")
    try:
        message = start_service(config, service)
    except SupervisorError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"message": message}


@app.post("/api/services/{service_id}/stop")
def api_stop(service_id: str) -> dict[str, str]:
    service = config.services.get(service_id)
    if not service or service.hidden:
        raise HTTPException(status_code=404, detail="Service not found")
    try:
        message = stop_service(service)
    except SupervisorError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"message": message}


@app.post("/api/services/{service_id}/restart")
def api_restart(service_id: str) -> dict[str, str]:
    service = config.services.get(service_id)
    if not service or service.hidden:
        raise HTTPException(status_code=404, detail="Service not found")
    try:
        message = restart_service(config, service)
    except SupervisorError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"message": message}


@app.post("/api/autostart")
def api_autostart() -> dict[str, list[str]]:
    return {"messages": start_autostart_services(config)}


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Startup Apps</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0f1419;
      --panel: #171d25;
      --border: #2a3441;
      --text: #e7edf5;
      --muted: #8b98a8;
      --up: #3dd68c;
      --down: #f87171;
      --degraded: #fbbf24;
      --accent: #60a5fa;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top, #1a2430, var(--bg) 55%);
      color: var(--text);
      min-height: 100vh;
    }
    .wrap { max-width: 1100px; margin: 0 auto; padding: 28px 20px 48px; }
    h1 { margin: 0 0 6px; font-size: 28px; }
    .sub { color: var(--muted); margin-bottom: 24px; }
    .summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }
    .card, .service, .ports {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
    }
    .card { padding: 14px 16px; }
    .card strong { display: block; font-size: 24px; margin-top: 4px; }
    .card span { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
    .toolbar { display: flex; gap: 10px; margin-bottom: 18px; flex-wrap: wrap; }
    button {
      background: #223041;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 12px;
      cursor: pointer;
    }
    button:hover { border-color: var(--accent); }
    .services { display: grid; gap: 12px; }
    .service { padding: 16px; display: grid; grid-template-columns: 1fr auto; gap: 12px; }
    .service h2 { margin: 0 0 4px; font-size: 18px; }
    .meta { color: var(--muted); font-size: 13px; }
    .badge {
      align-self: start;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge.up { background: rgba(61,214,140,.15); color: var(--up); }
    .badge.down { background: rgba(248,113,113,.15); color: var(--down); }
    .badge.degraded, .badge.starting, .badge.unknown {
      background: rgba(251,191,36,.15); color: var(--degraded);
    }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
    .actions a { color: var(--accent); text-decoration: none; }
    .ports { margin-top: 20px; padding: 16px; }
    .docker { margin-top: 20px; padding: 16px; }
    .docker-grid { display: grid; gap: 10px; margin-top: 12px; }
    .docker-card {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 14px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
    }
    .ports table, .docker table { width: 100%; border-collapse: collapse; }
    .ports th, .ports td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--border); }
    .conflict { color: var(--down); margin-top: 8px; }
    @media (max-width: 720px) {
      .summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .service { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Startup Apps</h1>
    <p class="sub">Local service observability and port registry</p>
    <div class="summary" id="summary"></div>
    <div class="toolbar">
      <button onclick="refresh()">Refresh</button>
      <button onclick="autostart()">Start autostart services</button>
    </div>
    <div class="services" id="services"></div>
    <div class="docker">
      <h3>OrbStack</h3>
      <div class="meta" id="docker-daemon"></div>
      <div class="docker-grid" id="docker-containers"></div>
    </div>
    <div class="ports">
      <h3>Port registry</h3>
      <div id="conflicts"></div>
      <table>
        <thead><tr><th>Port</th><th>Service</th><th>Label</th><th>Protocol</th></tr></thead>
        <tbody id="ports"></tbody>
      </table>
    </div>
  </div>
  <script>
    async function refresh() {
      const res = await fetch('/api/status');
      const data = await res.json();
      const s = data.summary;
      document.getElementById('summary').innerHTML = `
        <div class="card"><span>Total</span><strong>${s.total}</strong></div>
        <div class="card"><span>Up</span><strong style="color:var(--up)">${s.up}</strong></div>
        <div class="card"><span>Degraded</span><strong style="color:var(--degraded)">${s.degraded}</strong></div>
        <div class="card"><span>Down</span><strong style="color:var(--down)">${s.down}</strong></div>`;
      document.getElementById('services').innerHTML = data.services.map(service => `
        <div class="service">
          <div>
            <h2>${service.name}</h2>
            <div class="meta">${service.port ? ':' + service.port : 'daemon'} · ${service.description}</div>
            <div class="meta">${service.listener_command ? service.listener_command + ' · ' : ''}PID ${service.pid ?? '—'} · ${service.latency_ms != null ? service.latency_ms + 'ms' : '—'} · ${service.health_detail ?? ''}</div>
            <div class="actions">
              ${service.ui_url ? `<a href="${service.ui_url}" target="_blank">Open UI</a>` : ''}
              <a href="#" onclick="action('${service.id}', 'restart'); return false;">Restart</a>
              <a href="#" onclick="action('${service.id}', 'stop'); return false;">Stop</a>
              <a href="#" onclick="action('${service.id}', 'start'); return false;">Start</a>
            </div>
          </div>
          <div class="badge ${service.state}">${service.state}</div>
        </div>`).join('');
      const docker = data.docker;
      document.getElementById('docker-daemon').innerHTML =
        `Daemon: <strong style="color:${docker.daemon.running ? 'var(--up)' : 'var(--down)'}">${docker.daemon.running ? 'running' : 'down'}</strong>` +
        (docker.daemon.detail ? ` · ${docker.daemon.detail}` : '') +
        ` · ${docker.summary.up}/${docker.summary.total} containers up`;
      document.getElementById('docker-containers').innerHTML = docker.containers.map(c => `
        <div class="docker-card">
          <div>
            <strong>${c.name}</strong>
            <div class="meta">:${c.port} · ${c.container_name ?? c.compose_service} · ${c.status_text ?? ''}</div>
            <div class="actions">
              <a href="#" onclick="action('${c.service_id}', 'restart'); return false;">Restart</a>
              <a href="#" onclick="action('${c.service_id}', 'stop'); return false;">Stop</a>
              <a href="#" onclick="action('${c.service_id}', 'start'); return false;">Start</a>
            </div>
          </div>
          <div class="badge ${c.state}">${c.state}</div>
        </div>`).join('');
      document.getElementById('ports').innerHTML = data.ports.map(p => `
        <tr><td>${p.port}</td><td>${p.service_name}</td><td>${p.label}</td><td>${p.protocol}</td></tr>`).join('');
      document.getElementById('conflicts').innerHTML = data.conflicts.length
        ? `<div class="conflict">Port conflicts: ${data.conflicts.map(c => `:${c.port} (${c.assignments.map(a => a.service_name).join(', ')})`).join('; ')}</div>`
        : '';
    }
    async function action(id, op) {
      await fetch(`/api/services/${id}/${op}`, { method: 'POST' });
      await refresh();
    }
    async function autostart() {
      await fetch('/api/autostart', { method: 'POST' });
      await refresh();
    }
    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>"""


def run_dashboard(blocking: bool = True) -> None:
    uvicorn.run(
        app,
        host=config.dashboard_host,
        port=config.dashboard_port,
        log_level="warning",
        access_log=False,
    )


def run_dashboard_thread() -> threading.Thread:
    thread = threading.Thread(target=run_dashboard, daemon=True, name="dashboard")
    thread.start()
    return thread
