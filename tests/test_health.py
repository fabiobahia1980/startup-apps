from __future__ import annotations

import unittest

from startup_manager.health import ServiceState, _derive_state


class DeriveStateTests(unittest.TestCase):
    def test_up_when_port_open_and_healthy(self) -> None:
        self.assertEqual(
            _derive_state(True, True, None, None),
            ServiceState.UP,
        )

    def test_degraded_when_owner_mismatch(self) -> None:
        self.assertEqual(
            _derive_state(True, True, 123, False),
            ServiceState.DEGRADED,
        )

    def test_degraded_when_health_fails(self) -> None:
        self.assertEqual(
            _derive_state(True, False, None, None),
            ServiceState.DEGRADED,
        )

    def test_starting_when_pid_without_port(self) -> None:
        self.assertEqual(
            _derive_state(False, None, 123, None),
            ServiceState.STARTING,
        )

    def test_down_when_port_closed(self) -> None:
        self.assertEqual(
            _derive_state(False, None, None, None),
            ServiceState.DOWN,
        )


if __name__ == "__main__":
    unittest.main()
