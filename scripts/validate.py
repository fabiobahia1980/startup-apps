#!/usr/bin/env python3
"""Validate services.yaml and startup_manager imports (CI-safe, no rumps)."""
from __future__ import annotations

import compileall
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from startup_manager.config import load_config  # noqa: E402
from startup_manager.ports import find_port_conflicts  # noqa: E402

MANAGERS = frozenset({"orbstack", "brew", "docker", "process"})
IMPORT_MODULES = (
    "startup_manager.config",
    "startup_manager.ports",
    "startup_manager.health",
    "startup_manager.supervisor",
    "startup_manager.docker",
    "startup_manager.doctor",
    "startup_manager.dashboard",
    "startup_manager.watcher",
)


def validate_config() -> list[str]:
    errors: list[str] = []
    config = load_config()

    if not config.dashboard_host:
        errors.append("dashboard.host is required")
    if config.dashboard_port <= 0:
        errors.append("dashboard.port must be positive")

    for service_id, service in config.services.items():
        if service.manager not in MANAGERS:
            errors.append(f"{service_id}: unknown manager {service.manager!r}")

        for dep_id in service.depends_on:
            if dep_id not in config.services:
                errors.append(f"{service_id}: depends_on unknown service {dep_id!r}")

        if service.manager == "brew" and not service.brew_service:
            errors.append(f"{service_id}: brew manager requires brew_service")
        if service.manager == "docker" and not service.docker_compose_service:
            errors.append(f"{service_id}: docker manager requires docker_compose_service")
        if service.manager in {"orbstack", "process"} and not service.start_script:
            errors.append(f"{service_id}: {service.manager} manager requires start_script")
        if service.start_script and not service.start_script.exists():
            errors.append(f"{service_id}: missing start_script {service.start_script}")
        if service.stop_script and not service.stop_script.exists():
            errors.append(f"{service_id}: missing stop_script {service.stop_script}")

    conflicts = find_port_conflicts(config)
    for conflict in conflicts:
        names = ", ".join(a.service_name for a in conflict.assignments)
        errors.append(f"port conflict :{conflict.port} — {names}")

    return errors


def validate_imports() -> list[str]:
    errors: list[str] = []
    for module in IMPORT_MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:
            errors.append(f"import {module}: {exc}")
    return errors


def validate_compile() -> list[str]:
    errors: list[str] = []
    for path in (ROOT / "startup_manager", ROOT / "scripts"):
        if not compileall.compile_dir(path, quiet=1):
            errors.append(f"compile failed under {path}")
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(validate_config())
    errors.extend(validate_imports())
    errors.extend(validate_compile())

    if errors:
        print("Validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("OK: config, imports, and compile checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
