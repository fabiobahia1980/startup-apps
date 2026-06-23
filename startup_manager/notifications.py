from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthAlert:
    title: str
    subtitle: str
    message: str


def evaluate_health_alert(
    *,
    previous_up: int | None,
    up: int,
    total: int,
    down_names: list[str],
) -> HealthAlert | None:
    """Return an alert when service count drops or recovers to full health."""
    if up < total and (previous_up is None or up < previous_up):
        names = ", ".join(down_names[:5])
        if len(down_names) > 5:
            names += f" (+{len(down_names) - 5} more)"
        return HealthAlert(
            title="Startup Apps",
            subtitle=f"{up}/{total} services up",
            message=names or "One or more services are down",
        )

    if previous_up is not None and previous_up < total and up == total:
        return HealthAlert(
            title="Startup Apps",
            subtitle="All services up",
            message=f"{up}/{total}",
        )

    return None
