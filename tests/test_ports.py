from __future__ import annotations

import unittest

from startup_manager.config import ExtraPort
from startup_manager.ports import collect_port_assignments, find_port_conflicts

from .helpers import make_config, make_service


class PortConflictTests(unittest.TestCase):
    def test_no_conflicts_on_distinct_ports(self) -> None:
        config = make_config(
            {
                "a": make_service("a", port=8001),
                "b": make_service("b", port=8002),
            }
        )
        self.assertEqual(find_port_conflicts(config), [])

    def test_detects_duplicate_tcp_ports(self) -> None:
        config = make_config(
            {
                "a": make_service("a", port=9000),
                "b": make_service("b", port=9000),
            }
        )
        conflicts = find_port_conflicts(config)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].port, 9000)

    def test_skips_dependency_group_shared_port(self) -> None:
        config = make_config(
            {
                "app": make_service("app", port=5433, depends_on=["postgres"]),
                "postgres": make_service("postgres", port=5433, manager="docker"),
            }
        )
        self.assertEqual(find_port_conflicts(config), [])

    def test_udp_extra_port_does_not_conflict_with_tcp(self) -> None:
        config = make_config(
            {
                "svc": make_service(
                    "svc",
                    port=13305,
                    extra_ports=[
                        ExtraPort(port=13305, label="beacon", protocol="udp"),
                    ],
                ),
            }
        )
        self.assertEqual(find_port_conflicts(config), [])

    def test_includes_dashboard_port(self) -> None:
        config = make_config({"a": make_service("a", port=8080)}, dashboard_port=9090)
        ports = {a.port for a in collect_port_assignments(config)}
        self.assertEqual(ports, {8080, 9090})


if __name__ == "__main__":
    unittest.main()
