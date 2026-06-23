from __future__ import annotations

import unittest

from startup_manager.notifications import evaluate_health_alert


class NotificationTests(unittest.TestCase):
    def test_alerts_on_initial_shortfall(self) -> None:
        alert = evaluate_health_alert(
            previous_up=None,
            up=7,
            total=8,
            down_names=["9router"],
        )
        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert.subtitle, "7/8 services up")
        self.assertIn("9router", alert.message)

    def test_no_repeat_while_still_down(self) -> None:
        self.assertIsNone(
            evaluate_health_alert(
                previous_up=7,
                up=7,
                total=8,
                down_names=["9router"],
            )
        )

    def test_alerts_on_further_drop(self) -> None:
        alert = evaluate_health_alert(
            previous_up=7,
            up=6,
            total=8,
            down_names=["9router", "OpenCode"],
        )
        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert.subtitle, "6/8 services up")

    def test_recovery_notification(self) -> None:
        alert = evaluate_health_alert(
            previous_up=7,
            up=8,
            total=8,
            down_names=[],
        )
        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert.subtitle, "All services up")

    def test_no_recovery_alert_when_already_full(self) -> None:
        self.assertIsNone(
            evaluate_health_alert(
                previous_up=8,
                up=8,
                total=8,
                down_names=[],
            )
        )


if __name__ == "__main__":
    unittest.main()
