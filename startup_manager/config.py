from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "services.yaml"
STATE_DIR = Path.home() / ".startup-apps"
PID_DIR = STATE_DIR / "pids"
LOG_DIR = STATE_DIR / "logs"
STOPPED_DIR = STATE_DIR / "stopped"


@dataclass
class ExtraPort:
    port: int
    label: str
    protocol: str = "tcp"


@dataclass
class Service:
    id: str
    name: str
    description: str
    port: int
    health_path: str | None
    ui_path: str | None
    autostart: bool
    manager: str
    project: Path
    start_script: Path | None = None
    stop_script: Path | None = None
    brew_service: str | None = None
    docker_compose_service: str | None = None
    depends_on: list[str] = field(default_factory=list)
    extra_ports: list[ExtraPort] = field(default_factory=list)
    hidden: bool = False

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def health_url(self) -> str | None:
        if not self.health_path:
            return None
        return f"{self.base_url}{self.health_path}"

    @property
    def ui_url(self) -> str | None:
        if not self.ui_path:
            return None
        return f"{self.base_url}{self.ui_path}"

    @property
    def pid_file(self) -> Path:
        return PID_DIR / f"{self.id}.pid"

    @property
    def log_file(self) -> Path:
        return LOG_DIR / f"{self.id}.log"


@dataclass
class AppConfig:
    dashboard_host: str
    dashboard_port: int
    services: dict[str, Service]


def _parse_service(service_id: str, raw: dict[str, Any]) -> Service:
    extra_ports = [
        ExtraPort(
            port=item["port"],
            label=item["label"],
            protocol=item.get("protocol", "tcp"),
        )
        for item in raw.get("extra_ports", [])
    ]
    start_script = raw.get("start_script")
    stop_script = raw.get("stop_script")
    return Service(
        id=service_id,
        name=raw["name"],
        description=raw.get("description", ""),
        port=raw["port"],
        health_path=raw.get("health_path"),
        ui_path=raw.get("ui_path"),
        autostart=raw.get("autostart", False),
        manager=raw["manager"],
        project=Path(raw["project"]),
        start_script=ROOT / start_script if start_script else None,
        stop_script=ROOT / stop_script if stop_script else None,
        brew_service=raw.get("brew_service"),
        docker_compose_service=raw.get("docker_compose_service"),
        depends_on=raw.get("depends_on", []),
        extra_ports=extra_ports,
        hidden=raw.get("hidden", False),
    )


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    with path.open() as f:
        raw = yaml.safe_load(f)

    dashboard = raw["dashboard"]
    services = {
        service_id: _parse_service(service_id, service_raw)
        for service_id, service_raw in raw["services"].items()
    }
    return AppConfig(
        dashboard_host=dashboard["host"],
        dashboard_port=dashboard["port"],
        services=services,
    )


def visible_services(config: AppConfig) -> list[Service]:
    return [s for s in config.services.values() if not s.hidden]
