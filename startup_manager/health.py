from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

import httpx

from .config import Service
from .docker import inspect_container, is_daemon_running
from .ports import PortListener, get_listener, is_port_listening, port_owner_matches


class ServiceState(str, Enum):
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    STARTING = "starting"
    UNKNOWN = "unknown"


@dataclass
class ServiceStatus:
    id: str
    name: str
    description: str
    port: int
    state: ServiceState
    health_ok: bool | None
    port_open: bool
    pid: int | None
    listener_command: str | None
    managed_pid: int | None
    owner_match: bool | None
    ui_url: str | None
    health_url: str | None
    checked_at: str
    health_detail: str | None = None
    latency_ms: float | None = None


async def check_service(service: Service, client: httpx.AsyncClient) -> ServiceStatus:
    if service.manager == "docker-desktop":
        return await _check_docker_desktop(service)
    if service.manager == "docker":
        return await _check_docker_container(service)
    return await _check_http_service(service, client)


async def _check_docker_desktop(service: Service) -> ServiceStatus:
    daemon = await asyncio.to_thread(is_daemon_running)
    state = ServiceState.UP if daemon.running else ServiceState.DOWN
    return ServiceStatus(
        id=service.id,
        name=service.name,
        description=service.description,
        port=service.port,
        state=state,
        health_ok=daemon.running,
        port_open=False,
        pid=None,
        listener_command=None,
        managed_pid=None,
        owner_match=None,
        ui_url=service.ui_url,
        health_url=service.health_url,
        checked_at=datetime.now(UTC).isoformat(),
        health_detail=daemon.detail,
    )


async def _check_docker_container(service: Service) -> ServiceStatus:
    container = await asyncio.to_thread(inspect_container, service)
    port_open = is_port_listening(service.port) if service.port else False
    state = ServiceState(container.state)
    health_ok = container.state == "up"
    return ServiceStatus(
        id=service.id,
        name=service.name,
        description=service.description,
        port=service.port,
        state=state,
        health_ok=health_ok,
        port_open=port_open,
        pid=None,
        listener_command=container.container_name,
        managed_pid=None,
        owner_match=None,
        ui_url=service.ui_url,
        health_url=service.health_url,
        checked_at=datetime.now(UTC).isoformat(),
        health_detail=container.status_text,
    )


async def _check_http_service(service: Service, client: httpx.AsyncClient) -> ServiceStatus:
    port_open = is_port_listening(service.port)
    listener = get_listener(service.port) if port_open else None
    managed_pid = _read_pid(service)
    owner_match = port_owner_matches(service, listener)

    health_ok: bool | None = None
    health_detail: str | None = None
    latency_ms: float | None = None

    if service.health_url:
        if port_open:
            try:
                started = asyncio.get_running_loop().time()
                response = await client.get(service.health_url)
                latency_ms = round((asyncio.get_running_loop().time() - started) * 1000, 1)
                health_ok = response.status_code < 400
                if not health_ok:
                    health_detail = f"HTTP {response.status_code}"
            except httpx.RequestError as exc:
                health_ok = False
                health_detail = str(exc)
        else:
            health_ok = False
            health_detail = "port closed"
    elif port_open:
        health_ok = True
    else:
        health_ok = None

    state = _derive_state(port_open, health_ok, managed_pid, owner_match)
    return ServiceStatus(
        id=service.id,
        name=service.name,
        description=service.description,
        port=service.port,
        state=state,
        health_ok=health_ok,
        port_open=port_open,
        pid=listener.pid if listener else managed_pid,
        listener_command=listener.command if listener else None,
        managed_pid=managed_pid,
        owner_match=owner_match,
        ui_url=service.ui_url,
        health_url=service.health_url,
        checked_at=datetime.now(UTC).isoformat(),
        health_detail=health_detail,
        latency_ms=latency_ms,
    )


def _read_pid(service: Service) -> int | None:
    if not service.pid_file.exists():
        return None
    try:
        return int(service.pid_file.read_text().strip())
    except ValueError:
        return None


def _derive_state(
    port_open: bool,
    health_ok: bool | None,
    managed_pid: int | None,
    owner_match: bool | None,
) -> ServiceState:
    if port_open and health_ok is True:
        if owner_match is False:
            return ServiceState.DEGRADED
        return ServiceState.UP
    if port_open and health_ok is False:
        return ServiceState.DEGRADED
    if managed_pid and not port_open:
        return ServiceState.STARTING
    if not port_open:
        return ServiceState.DOWN
    return ServiceState.UNKNOWN


async def check_all(services: list[Service]) -> list[ServiceStatus]:
    async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
        return await asyncio.gather(*(check_service(service, client) for service in services))
