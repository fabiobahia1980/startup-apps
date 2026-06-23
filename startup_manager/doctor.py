from __future__ import annotations

import os
import subprocess
from collections import defaultdict
from pathlib import Path

from .config import PID_DIR, AppConfig, Service, load_config
from .ports import (
    PortAssignment,
    collect_port_assignments,
    find_port_conflicts,
    get_listener,
    is_port_listening,
)


def _format_services(assignments: list[PortAssignment]) -> str:
    names = sorted({f"{a.service_name} ({a.label})" for a in assignments})
    return ", ".join(names)


def evaluate_orbstack_login(*, has_login_item: bool, docker_running: bool) -> str | None:
    if has_login_item or docker_running:
        return None
    return (
        "OrbStack not in Login Items and Docker daemon is down — "
        "enable Start at login in OrbStack settings"
    )


def _has_login_item(name: str) -> bool:
    result = subprocess.run(
        ["osascript", "-e", 'tell application "System Events" to get the name of every login item'],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    items = [item.strip() for item in result.stdout.split(",")]
    return name in items


def _docker_running() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return result.returncode == 0


def run_orbstack_login_check() -> int:
    warning = evaluate_orbstack_login(
        has_login_item=_has_login_item("OrbStack"),
        docker_running=_docker_running(),
    )
    if warning:
        print(f"WARN: {warning}")
        return 1
    print("OK:   OrbStack login configured or daemon running")
    return 0


def _audit_service_pid(service: Service, pid_file: Path) -> str | None:
    try:
        pid = int(pid_file.read_text().strip())
    except ValueError:
        return f"invalid pid file for {service.name}"

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return f"stale pid file for {service.name} (pid {pid} not running)"

    if service.port > 0 and is_port_listening(service.port):
        listener = get_listener(service.port)
        if listener and listener.pid and listener.pid != pid:
            return (
                f"{service.name} pid file={pid} but "
                f":{service.port} owned by pid {listener.pid}"
            )
    return None


def run_stale_pid_audit(config: AppConfig, pid_dir: Path | None = None) -> int:
    directory = pid_dir or PID_DIR
    issues = 0

    if not directory.exists():
        print("OK:   No pid files")
        return 0

    for pid_file in sorted(directory.glob("*.pid")):
        service_id = pid_file.stem
        service = config.services.get(service_id)
        if service is None:
            print(f"WARN: Orphan pid file {pid_file.name} (unknown service)")
            issues += 1
            continue
        if service.manager != "process":
            continue

        warning = _audit_service_pid(service, pid_file)
        if warning:
            print(f"WARN: {warning[0].upper()}{warning[1:]}")
            issues += 1

    if issues == 0:
        print("OK:   No stale pid files")
    return issues


def run_port_audit(config: AppConfig) -> int:
    issues = 0

    conflicts = find_port_conflicts(config)
    if conflicts:
        for conflict in conflicts:
            services = ", ".join(a.service_name for a in conflict.assignments)
            print(f"WARN: Port conflict :{conflict.port} — {services}")
            issues += 1
    else:
        print("OK:   No TCP port conflicts in registry")

    by_port: dict[int, list[PortAssignment]] = defaultdict(list)
    for assignment in collect_port_assignments(config):
        if assignment.protocol != "tcp" or assignment.port <= 0:
            continue
        by_port[assignment.port].append(assignment)

    for port in sorted(by_port):
        assignments = by_port[port]
        label = _format_services(assignments)
        if is_port_listening(port):
            listener = get_listener(port)
            if listener and listener.command:
                detail = f"{listener.command} pid {listener.pid}"
            else:
                detail = "listening"
            print(f"OK:   :{port} {label} — {detail}")
        else:
            print(f"     :{port} {label} — idle")

    return issues


def run_doctor() -> int:
    config = load_config()
    issues = 0

    print("==> Service checks")
    issues += run_orbstack_login_check()
    issues += run_stale_pid_audit(config)

    print("")
    print("==> Port registry")
    issues += run_port_audit(config)

    return issues
