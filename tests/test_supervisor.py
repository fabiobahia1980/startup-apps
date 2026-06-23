from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import startup_manager.supervisor as supervisor
from startup_manager.supervisor import (
    _services_order,
    clear_manually_stopped,
    is_manually_stopped,
    mark_manually_stopped,
    stop_all_services,
)

from .helpers import make_config, make_service


class SupervisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.stopped_dir = Path(self._tmpdir.name) / "stopped"
        self.stopped_dir.mkdir(parents=True, exist_ok=True)
        self.pid_patch = patch.object(supervisor, "STOPPED_DIR", self.stopped_dir)
        self.pid_patch.start()

    def tearDown(self) -> None:
        self.pid_patch.stop()
        self._tmpdir.cleanup()

    def test_manual_stop_marker_round_trip(self) -> None:
        service = make_service("taos", port=6969)
        self.assertFalse(is_manually_stopped(service))
        mark_manually_stopped(service)
        self.assertTrue(is_manually_stopped(service))
        clear_manually_stopped(service)
        self.assertFalse(is_manually_stopped(service))

    def test_services_order_respects_dependencies(self) -> None:
        config = make_config(
            {
                "orbstack": make_service("orbstack", port=0, manager="orbstack"),
                "postgres": make_service(
                    "postgres",
                    port=5433,
                    manager="docker",
                    depends_on=["orbstack"],
                ),
                "app": make_service("app", port=8080, depends_on=["postgres"]),
            }
        )
        order = [s.id for s in _services_order(config)]
        self.assertEqual(order.index("orbstack"), 0)
        self.assertLess(order.index("postgres"), order.index("app"))

    @patch.object(supervisor, "_quit_orbstack", return_value="Quit OrbStack")
    @patch.object(supervisor, "stop_service", side_effect=lambda svc: f"stopped {svc.id}")
    def test_stop_all_reverse_order(self, mock_stop, mock_quit) -> None:
        config = make_config(
            {
                "orbstack": make_service("orbstack", port=0, manager="orbstack"),
                "app": make_service("app", port=8080),
            }
        )
        messages = stop_all_services(config)
        self.assertEqual(mock_stop.call_count, 1)
        mock_stop.assert_called_once()
        self.assertEqual(mock_stop.call_args[0][0].id, "app")
        mock_quit.assert_called_once()
        self.assertTrue(any("OrbStack" in m for m in messages))


if __name__ == "__main__":
    unittest.main()
