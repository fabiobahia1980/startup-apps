from __future__ import annotations

from collections import defaultdict

from .config import AppConfig, load_config
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
    return run_port_audit(config)
