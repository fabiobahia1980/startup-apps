from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass

from .config import AppConfig, Service


@dataclass
class PortAssignment:
    port: int
    service_id: str
    service_name: str
    label: str
    protocol: str


@dataclass
class PortConflict:
    port: int
    assignments: list[PortAssignment]


@dataclass
class PortListener:
    port: int
    protocol: str
    pid: int | None
    command: str | None


def collect_port_assignments(config: AppConfig) -> list[PortAssignment]:
    assignments: list[PortAssignment] = []
    for service in config.services.values():
        assignments.append(
            PortAssignment(
                port=service.port,
                service_id=service.id,
                service_name=service.name,
                label="primary",
                protocol="tcp",
            )
        )
        for extra in service.extra_ports:
            assignments.append(
                PortAssignment(
                    port=extra.port,
                    service_id=service.id,
                    service_name=service.name,
                    label=extra.label,
                    protocol=extra.protocol,
                )
            )
    assignments.append(
        PortAssignment(
            port=config.dashboard_port,
            service_id="dashboard",
            service_name="Startup Apps",
            label="dashboard",
            protocol="tcp",
        )
    )
    return assignments


def find_port_conflicts(config: AppConfig) -> list[PortConflict]:
    by_port: dict[tuple[int, str], list[PortAssignment]] = {}
    for assignment in collect_port_assignments(config):
        key = (assignment.port, assignment.protocol)
        by_port.setdefault(key, []).append(assignment)

    conflicts: list[PortConflict] = []
    for (port, protocol), items in sorted(by_port.items()):
        if protocol != "tcp" or len(items) <= 1:
            continue
        service_ids = {item.service_id for item in items}
        if _is_dependency_group(config, service_ids):
            continue
        conflicts.append(PortConflict(port=port, assignments=items))
    return conflicts


def _is_dependency_group(config: AppConfig, service_ids: set[str]) -> bool:
    for service_id in service_ids:
        service = config.services.get(service_id)
        if not service:
            continue
        deps = set(service.depends_on)
        if deps and deps.issubset(service_ids):
            return True
    return False


def is_port_listening(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def get_listener(port: int) -> PortListener | None:
    try:
        output = subprocess.check_output(
            ["lsof", "-iTCP", f":{port}", "-sTCP:LISTEN", "-P", "-n"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    lines = [line for line in output.splitlines() if line.strip()]
    if len(lines) < 2:
        return None

    parts = lines[1].split()
    pid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    command = parts[0] if parts else None
    return PortListener(port=port, protocol="tcp", pid=pid, command=command)


def port_owner_matches(service: Service, listener: PortListener | None) -> bool | None:
    if listener is None:
        return None
    if listener.pid is None:
        return None
    pid_file = service.pid_file
    if pid_file.exists():
        try:
            expected = int(pid_file.read_text().strip())
            return listener.pid == expected
        except ValueError:
            return None
    return None
