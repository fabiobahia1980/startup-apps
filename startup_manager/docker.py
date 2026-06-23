from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig, Service


@dataclass
class DockerDaemonStatus:
    running: bool
    detail: str | None = None


@dataclass
class ContainerStatus:
    service_id: str
    name: str
    description: str
    container_name: str | None
    compose_service: str
    project: str
    port: int
    state: str
    health: str | None
    status_text: str | None
    running: bool


def is_daemon_running() -> DockerDaemonStatus:
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return DockerDaemonStatus(running=False, detail=str(exc))

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "docker info failed").strip()
        if "Cannot connect" in detail or "Is the docker daemon running" in detail:
            detail = "Docker daemon not running"
        return DockerDaemonStatus(running=False, detail=detail)

    version = result.stdout.strip() or "unknown"
    return DockerDaemonStatus(running=True, detail=f"v{version}")


def start_orbstack(wait_seconds: int = 60) -> str:
    result = subprocess.run(
        ["open", "-a", "OrbStack"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Could not launch OrbStack")

    for i in range(1, wait_seconds + 1):
        if is_daemon_running().running:
            return f"OrbStack ready after {i}s"
        if i == wait_seconds:
            raise RuntimeError("OrbStack did not become ready in time")
        subprocess.run(["sleep", "1"], check=False)

    return "OrbStack started"


def _compose_file(service: Service) -> Path:
    return service.project / "docker-compose.yml"


def inspect_container(service: Service) -> ContainerStatus:
    compose_service = service.docker_compose_service or service.id
    base = ContainerStatus(
        service_id=service.id,
        name=service.name,
        description=service.description,
        container_name=None,
        compose_service=compose_service,
        project=str(service.project),
        port=service.port,
        state="down",
        health=None,
        status_text=None,
        running=False,
    )

    daemon = is_daemon_running()
    if not daemon.running:
        base.status_text = daemon.detail
        return base

    compose = _compose_file(service)
    if not compose.exists():
        base.status_text = f"missing {compose}"
        base.state = "degraded"
        return base

    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(compose),
                "ps",
                "--format",
                "json",
                compose_service,
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
            cwd=service.project,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        base.status_text = str(exc)
        base.state = "degraded"
        return base

    if result.returncode != 0:
        base.status_text = (result.stderr or result.stdout or "docker compose ps failed").strip()
        return base

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        base.status_text = "container not created"
        return base

    try:
        data = json.loads(lines[0])
    except json.JSONDecodeError:
        base.status_text = "could not parse container status"
        base.state = "degraded"
        return base

    state = (data.get("State") or "").lower()
    health = data.get("Health") or None
    base.container_name = data.get("Name")
    base.status_text = data.get("Status")
    base.running = state == "running"
    base.health = health

    if base.running and health in {None, "", "healthy"}:
        base.state = "up"
    elif base.running:
        base.state = "degraded"
    elif state in {"restarting", "created", "starting"}:
        base.state = "starting"
    else:
        base.state = "down"

    return base


def docker_services(config: AppConfig) -> list[Service]:
    return [s for s in config.services.values() if s.manager == "docker"]


def docker_overview(config: AppConfig) -> dict:
    daemon = is_daemon_running()
    containers = [inspect_container(service) for service in docker_services(config)]
    running = sum(1 for c in containers if c.state == "up")
    return {
        "daemon": {
            "running": daemon.running,
            "detail": daemon.detail,
        },
        "summary": {
            "total": len(containers),
            "up": running,
            "down": len(containers) - running,
        },
        "containers": [
            {
                "service_id": c.service_id,
                "name": c.name,
                "description": c.description,
                "container_name": c.container_name,
                "compose_service": c.compose_service,
                "project": c.project,
                "port": c.port,
                "state": c.state,
                "health": c.health,
                "status_text": c.status_text,
                "running": c.running,
            }
            for c in containers
        ],
    }


def ensure_daemon_running() -> None:
    if is_daemon_running().running:
        return
    start_orbstack()
