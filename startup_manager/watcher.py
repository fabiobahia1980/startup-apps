from __future__ import annotations

import threading
import time

from .config import AppConfig, load_config
from .supervisor import start_autostart_with_retries


class AutostartWatcher(threading.Thread):
    def __init__(
        self,
        config: AppConfig | None = None,
        interval_seconds: int = 45,
        boot_window_seconds: int = 600,
    ) -> None:
        super().__init__(daemon=True, name="autostart-watcher")
        self.config = config or load_config()
        self.interval_seconds = interval_seconds
        self.boot_window_seconds = boot_window_seconds
        self._started_at = time.monotonic()

    def run(self) -> None:
        while True:
            elapsed = time.monotonic() - self._started_at
            if elapsed < self.boot_window_seconds:
                start_autostart_with_retries(self.config, passes=1)
            else:
                start_autostart_with_retries(self.config, passes=1)
            time.sleep(self.interval_seconds)


def start_autostart_watcher(config: AppConfig | None = None) -> AutostartWatcher:
    watcher = AutostartWatcher(config=config)
    watcher.start()
    return watcher
