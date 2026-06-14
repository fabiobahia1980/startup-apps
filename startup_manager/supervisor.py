from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

from .config import LOG_DIR, PID_DIR, AppConfig, Service
from .docker import ensure_daemon_running


class SupervisorError(RuntimeError):
    pass


def ensure_state_dirs() -> None:
    PID_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _run_script(script: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    if not script.exists():
        raise SupervisorError(f"Script not found: {script}")
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [str(script)],
        cwd=script.parent.parent,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


def start_service(config: AppConfig, service: Service) -> str:
    ensure_state_dirs()
    for dep_id in service.depends_on:
        dep = config.services.get(dep_id)
        if dep:
            start_service(config, dep)

    if service.manager == "brew":
        if not service.brew_service:
            raise SupervisorError(f"{service.name} missing brew_service")
        result = subprocess.run(
            ["brew", "services", "start", service.brew_service],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise SupervisorError(result.stderr.strip() or result.stdout.strip())
        return f"Started brew service {service.brew_service}"

    if service.manager == "docker-desktop":
        if not service.start_script:
            raise SupervisorError(f"{service.name} missing start_script")
        result = _run_script(service.start_script)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise SupervisorError(detail or f"Failed to start {service.name}")
        return result.stdout.strip() or f"Started {service.name}"

    if service.manager == "docker":
        if not service.docker_compose_service:
            raise SupervisorError(f"{service.name} missing docker_compose_service")
        try:
            ensure_daemon_running()
        except RuntimeError as exc:
            raise SupervisorError(str(exc)) from exc
        result = subprocess.run(
            ["docker", "compose", "up", "-d", service.docker_compose_service],
            cwd=service.project,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise SupervisorError(result.stderr.strip() or result.stdout.strip())
        return f"Started docker service {service.docker_compose_service}"

    if service.manager == "process":
        if not service.start_script:
            raise SupervisorError(f"{service.name} missing start_script")
        result = _run_script(service.start_script)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise SupervisorError(detail or f"Failed to start {service.name}")
        return result.stdout.strip() or f"Started {service.name}"

    raise SupervisorError(f"Unknown manager: {service.manager}")


def stop_service(service: Service) -> str:
    ensure_state_dirs()

    if service.manager == "brew":
        if not service.brew_service:
            raise SupervisorError(f"{service.name} missing brew_service")
        result = subprocess.run(
            ["brew", "services", "stop", service.brew_service],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise SupervisorError(result.stderr.strip() or result.stdout.strip())
        return f"Stopped brew service {service.brew_service}"

    if service.manager == "docker-desktop":
        return f"{service.name} left running (quit Docker Desktop from the menu bar app)"

    if service.manager == "docker":
        if not service.docker_compose_service:
            raise SupervisorError(f"{service.name} missing docker_compose_service")
        result = subprocess.run(
            ["docker", "compose", "stop", service.docker_compose_service],
            cwd=service.project,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise SupervisorError(result.stderr.strip() or result.stdout.strip())
        return f"Stopped docker service {service.docker_compose_service}"

    if service.manager == "process":
        if service.stop_script and service.stop_script.exists():
            result = _run_script(service.stop_script)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip()
                raise SupervisorError(detail or f"Failed to stop {service.name}")
            return result.stdout.strip() or f"Stopped {service.name}"
        return _stop_by_pid(service)

    raise SupervisorError(f"Unknown manager: {service.manager}")


def restart_service(config: AppConfig, service: Service) -> str:
    stop_service(service)
    return start_service(config, service)


def start_autostart_services(config: AppConfig) -> list[str]:
    messages: list[str] = []
    order = _autostart_order(config)
    for service in order:
        if service.autostart:
            try:
                messages.append(start_service(config, service))
            except SupervisorError as exc:
                messages.append(f"{service.name}: {exc}")
    return messages


def _autostart_order(config: AppConfig) -> list[Service]:
    services = [s for s in config.services.values() if s.autostart]
    by_id = {s.id: s for s in services}
    visited: set[str] = set()
    ordered: list[Service] = []

    def visit(service: Service) -> None:
        if service.id in visited:
            return
        for dep_id in service.depends_on:
            dep = by_id.get(dep_id) or config.services.get(dep_id)
            if dep and dep.autostart:
                visit(dep)
        visited.add(service.id)
        ordered.append(service)

    for service in services:
        visit(service)
    return ordered


def _stop_by_pid(service: Service) -> str:
    if not service.pid_file.exists():
        return f"{service.name} not running (no pid file)"
    try:
        pid = int(service.pid_file.read_text().strip())
    except ValueError:
        service.pid_file.unlink(missing_ok=True)
        return f"{service.name} not running (invalid pid file)"

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        service.pid_file.unlink(missing_ok=True)
        return f"{service.name} not running (stale pid)"

    service.pid_file.unlink(missing_ok=True)
    return f"Stopped {service.name} (pid {pid})"
