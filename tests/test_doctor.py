from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from startup_manager.doctor import (
    _audit_service_pid,
    evaluate_orbstack_login,
    run_stale_pid_audit,
)
from startup_manager.ports import PortListener

from .helpers import make_config, make_service


class OrbStackLoginTests(unittest.TestCase):
    def test_warn_when_no_login_and_docker_down(self) -> None:
        msg = evaluate_orbstack_login(has_login_item=False, docker_running=False)
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("OrbStack", msg)

    def test_ok_with_login_item(self) -> None:
        self.assertIsNone(evaluate_orbstack_login(has_login_item=True, docker_running=False))

    def test_ok_when_daemon_running(self) -> None:
        self.assertIsNone(evaluate_orbstack_login(has_login_item=False, docker_running=True))


class StalePidTests(unittest.TestCase):
    def test_detects_dead_pid(self) -> None:
        service = make_service("taos", port=6969)
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "taos.pid"
            pid_file.write_text("999999999")
            warning = _audit_service_pid(service, pid_file)
            self.assertIsNotNone(warning)
            assert warning is not None
            self.assertIn("stale", warning)

    def test_detects_invalid_pid_file(self) -> None:
        service = make_service("taos", port=6969)
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "taos.pid"
            pid_file.write_text("not-a-pid")
            warning = _audit_service_pid(service, pid_file)
            self.assertIsNotNone(warning)
            assert warning is not None
            self.assertIn("invalid", warning)

    def test_audit_orphan_and_clean_pid_dir(self) -> None:
        config = make_config({"taos": make_service("taos", port=6969)})
        with tempfile.TemporaryDirectory() as tmp:
            pid_dir = Path(tmp)
            (pid_dir / "unknown.pid").write_text("1")
            issues = run_stale_pid_audit(config, pid_dir=pid_dir)
            self.assertEqual(issues, 1)

    @patch("startup_manager.doctor.is_port_listening", return_value=True)
    @patch("startup_manager.doctor.get_listener")
    def test_detects_pid_listener_mismatch(self, mock_listener, _mock_listening) -> None:
        mock_listener.return_value = PortListener(
            port=6969, protocol="tcp", pid=4242, command="other"
        )
        service = make_service("taos", port=6969)
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "taos.pid"
            pid_file.write_text(str(os.getpid()))
            warning = _audit_service_pid(service, pid_file)
            self.assertIsNotNone(warning)
            assert warning is not None
            self.assertIn("owned by pid", warning)


if __name__ == "__main__":
    unittest.main()
