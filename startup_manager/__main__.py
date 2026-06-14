from __future__ import annotations

import argparse
import threading

from .config import load_config
from .dashboard import run_dashboard
from .menubar import run_menubar
from .supervisor import ensure_state_dirs, start_autostart_services


def _autostart_background(config) -> None:
    messages = start_autostart_services(config)
    for message in messages:
        print(message)


def main() -> None:
    parser = argparse.ArgumentParser(description="Startup Apps manager")
    parser.add_argument(
        "command",
        nargs="?",
        default="menubar",
        choices=["menubar", "dashboard", "autostart"],
        help="Run mode (default: menubar with dashboard in background)",
    )
    args = parser.parse_args()

    ensure_state_dirs()
    config = load_config()

    if args.command == "dashboard":
        run_dashboard()
    elif args.command == "autostart":
        _autostart_background(config)
    else:
        if any(service.autostart for service in config.services.values()):
            threading.Thread(
                target=_autostart_background,
                args=(config,),
                daemon=True,
                name="autostart",
            ).start()
        run_menubar()


if __name__ == "__main__":
    main()
