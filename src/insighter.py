"""Turn a result DataFrame into an auto-chart + a one-line summary."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def auto_chart(df: pd.DataFrame) -> go.Figure | None:
    """Pick a sensible chart for the shape of the result, or None if unclear."""
    if df is None or df.empty or df.shape[1] < 2:
        return None

    cols = df.columns.tolist()
    numeric = [c for c in cols if _is_numeric(df[c])]
    categorical = [c for c in cols if not _is_numeric(df[c])]

    if not numeric:
        return None

    y = numeric[-1]
    # Prefer a category/date axis when there is one.
    x = categorical[0] if categorical else cols[0]

    if pd.api.types.is_datetime64_any_dtype(df[x]) or "date" in x.lower():
        return px.line(df, x=x, y=y, markers=True)

    plot_df = df if len(df) <= 30 else df.nlargest(30, y)
    return px.bar(plot_df, x=x, y=y)


def summarize(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "No rows returned."
    rows = len(df)
    if df.shape[1] == 1 and rows == 1:
        return f"Result: {df.iloc[0, 0]}"
    return f"Returned {rows} row(s) across {df.shape[1]} column(s)."
