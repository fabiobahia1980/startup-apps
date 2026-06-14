from __future__ import annotations

import asyncio
import webbrowser

import rumps

from .config import load_config, visible_services
from .dashboard import run_dashboard_thread
from .health import ServiceState, check_all
from .supervisor import start_autostart_services


APP_NAME = "StartupApps"


class StartupAppsMenuBar(rumps.App):
    def __init__(self) -> None:
        super().__init__(APP_NAME, title="…", quit_button=None)
        self.config = load_config()
        self.dashboard_url = f"http://{self.config.dashboard_host}:{self.config.dashboard_port}"
        run_dashboard_thread()
        self.refresh_menu(None)
        self.timer = rumps.Timer(self.refresh_menu, 5)
        self.timer.start()

    def open_dashboard(self, _: rumps.MenuItem) -> None:
        webbrowser.open(self.dashboard_url)

    def start_autostart(self, _: rumps.MenuItem) -> None:
        messages = start_autostart_services(self.config)
        rumps.notification("Startup Apps", "Autostart complete", "\n".join(messages[:3]))
        self.refresh_menu(None)

    def refresh_menu(self, _: rumps.MenuItem | None) -> None:
        statuses = asyncio.run(check_all(visible_services(self.config)))
        up = sum(1 for s in statuses if s.state == ServiceState.UP)
        total = len(statuses)
        self.title = f"{up}/{total}"

        items: list[rumps.MenuItem | None] = [
            None,
            rumps.MenuItem("Open dashboard", callback=self.open_dashboard),
            rumps.MenuItem("Refresh", callback=self.refresh_menu),
            None,
        ]

        for status in statuses:
            icon = {
                ServiceState.UP: "✓",
                ServiceState.DOWN: "✗",
                ServiceState.DEGRADED: "!",
                ServiceState.STARTING: "…",
                ServiceState.UNKNOWN: "?",
            }[status.state]
            port_label = f":{status.port}" if status.port else ""
            items.append(
                rumps.MenuItem(
                    f"{icon} {status.name}{port_label}",
                    callback=self.make_service_callback(status.id),
                )
            )

        items.extend(
            [
                None,
                rumps.MenuItem("Start autostart services", callback=self.start_autostart),
                None,
                rumps.MenuItem("Quit", callback=self.quit_app),
            ]
        )
        self.menu = items

    def make_service_callback(self, service_id: str):
        def callback(_: rumps.MenuItem) -> None:
            service = self.config.services[service_id]
            if service.ui_url:
                webbrowser.open(service.ui_url)
            else:
                rumps.notification(service.name, "No UI URL", f"Port {service.port}")

        return callback

    def quit_app(self, _: rumps.MenuItem) -> None:
        rumps.quit_application()


def run_menubar() -> None:
    StartupAppsMenuBar().run()
