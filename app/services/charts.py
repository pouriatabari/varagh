"""The charts of the pages.

The charts are built out of the database, without the AI: the server picks the
series and hands the labels and the values to the template. The AI answers use
the same renderer, so a chart always states the basis it was measured on.
"""

from __future__ import annotations

from typing import Any

from app.ai.charts import build_series, resolve_charts
from app.ai.schemas import ChartSpec


def build_charts(
    specs: list[dict[str, Any]],
    series: dict[str, dict[str, Any]],
    id_prefix: str = "chart",
) -> list[dict[str, Any]]:
    """Build the charts of a page out of a series map.

    Every spec names a series of ``series`` and carries the title and the
    basis of the chart. A spec that names an unknown series is skipped.
    """
    charts = []
    for spec in specs:
        try:
            charts.append(ChartSpec(**spec))
        except Exception:  # a broken spec is simply not drawn
            continue
    payload = {"series": build_series(series)}
    return resolve_charts(charts, payload, id_prefix=id_prefix)
