from __future__ import annotations

from pathlib import Path

from startup_manager.config import AppConfig, ExtraPort, Service


def make_service(
    service_id: str,
    *,
    port: int = 8080,
    name: str | None = None,
    manager: str = "process",
    depends_on: list[str] | None = None,
    autostart: bool = True,
    extra_ports: list[ExtraPort] | None = None,
    project: Path | None = None,
) -> Service:
    return Service(
        id=service_id,
        name=name or service_id,
        description="",
        port=port,
        health_path=None,
        ui_path=None,
        autostart=autostart,
        manager=manager,
        project=project or Path("/tmp"),
        depends_on=depends_on or [],
        extra_ports=extra_ports or [],
    )


def make_config(
    services: dict[str, Service],
    *,
    dashboard_port: int = 9090,
) -> AppConfig:
    return AppConfig(
        dashboard_host="127.0.0.1",
        dashboard_port=dashboard_port,
        services=services,
    )
