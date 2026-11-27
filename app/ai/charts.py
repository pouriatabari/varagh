"""Charts in the AI answers.

The model never sends numbers: it names a series of the payload it was given
and the server resolves the labels and the values. A chart therefore cannot
show a figure that is not in the database — the same rule the review draft
follows with the task ids.
"""

from __future__ import annotations

from typing import Any

from app.ai.provider import AIError
from app.i18n import t

CHART_TYPES = ("bar", "line", "doughnut", "pie")
BASES = ("measured", "estimated", "elapsed")


def build_series(entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return a series map out of ``{name: {labels, values, unit}}``."""
    return {
        name: {
            "labels": [str(label) for label in data.get("labels", [])],
            "values": [float(value) for value in data.get("values", [])],
            "unit": str(data.get("unit", "")),
        }
        for name, data in entries.items()
    }


def series_map(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return the series of a payload."""
    series = (payload or {}).get("series")
    return series if isinstance(series, dict) else {}


def validate_charts(charts: list[Any], payload: dict[str, Any] | None) -> None:
    """Refuse a chart that names a series the payload does not have."""
    available = series_map(payload)
    for chart in charts:
        if chart.series not in available:
            raise AIError(f"the answer cites an unknown series: {chart.series}")


def resolve_charts(
    charts: list[Any],
    payload: dict[str, Any] | None,
    id_prefix: str = "chart",
) -> list[dict[str, Any]]:
    """Turn the chart specs of an answer into renderable data."""
    available = series_map(payload)
    resolved: list[dict[str, Any]] = []
    for index, chart in enumerate(charts):
        series = available.get(chart.series)
        if not isinstance(series, dict):
            continue
        labels = [str(label) for label in series.get("labels", [])]
        values = [float(value) for value in series.get("values", [])]
        if not labels or len(labels) != len(values):
            continue
        unit = str(series.get("unit", ""))
        resolved.append(
            {
                "id": f"{id_prefix}-{index}",
                "type": chart.type,
                "title": chart.title_fa,
                "labels": labels,
                "values": values,
                "unit": unit,
                "unit_label": t(unit) if unit else "",
                "basis": chart.basis,
                "basis_label": t(f"time.basis.{chart.basis}"),
            }
        )
    return resolved
