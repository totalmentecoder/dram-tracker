"""
NVIDIA Segment Revenue Loader
==============================
Parses the manually-collected NVIDIA quarterly segment CSV and loads it
into the dram_tracker SQLite database, replacing the yfinance consolidated
revenue with the proper Data Center vs Gaming breakdown.

The crossover point — Q1 2022, when Data Center first exceeded Gaming —
is the AI intensity event your DiD model is built around.
"""

import re
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
DB_PATH = Path("dram_tracker.db")
CSV_PATH = Path("Formatted Data Revenue NVIDIA Quarterly.csv")


def _parse_european_number(val: str):
    """
    Convert European-formatted currency string to float.
    e.g. ' $57.000.000,00 ' -> 57000000.0
    """
    val = val.strip().replace("$", "").replace(" ", "")
    # Remove thousand separators (dots), replace decimal comma with dot
    val = re.sub(r"\.(?=\d{3})", "", val)
    val = val.replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None


def load_nvidia_segments(
    conn: sqlite3.Connection,
    csv_path: Path = CSV_PATH,
) -> pd.DataFrame:
    """
    Parse and load NVIDIA segment revenue CSV into SQLite.
    Creates/updates the nvidia_financials table with proper segment rows.
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV not found at {csv_path}. "
            "Place Formatted_Data_Revenue_NVIDIA_Quarterly.csv in the project folder."
        )

    raw = pd.read_csv(csv_path, sep=";", header=0)
    raw.columns = [c.strip() for c in raw.columns]

    # Rename for convenience
    raw = raw.rename(columns={
        "Column1":            "date_raw",
        "Data centers and AI": "data_center",
        "Gaming":             "gaming",
        "Other":              "other",
        "Total":              "total",
    })

    rows = []
    fetched_at = datetime.utcnow().isoformat()

    for _, row in raw.iterrows():
        # Parse date — format is DD/MM/YYYY
        try:
            dt = pd.to_datetime(row["date_raw"].strip(), dayfirst=True)
            period = str(dt.date())
        except Exception:
            continue

        segments = {
            "data_center": row.get("data_center"),
            "gaming":      row.get("gaming"),
            "other":       row.get("other"),
            "total":       row.get("total"),
        }

        for seg_name, raw_val in segments.items():
            if pd.isna(raw_val):
                continue
            amount = _parse_european_number(str(raw_val))
            if amount is None:
                continue
            rows.append({
                "period":      period,
                "segment":     seg_name,
                "revenue_usd": amount,
                "fetched_at":  fetched_at,
            })

    df = pd.DataFrame(rows)
    if df.empty:
        log.warning("No segment data parsed.")
        return df

    cur = conn.cursor()
    cur.executemany(
        """INSERT OR REPLACE INTO nvidia_financials
           (period, segment, revenue_usd, fetched_at)
           VALUES (:period, :segment, :revenue_usd, :fetched_at)""",
        df.to_dict("records"),
    )
    conn.commit()
    log.info("Stored %d NVIDIA segment rows (%d quarters).",
             len(df), len(df) // 4)
    return df


def build_segment_chart(conn: sqlite3.Connection):
    """
    Build a standalone Plotly chart showing Data Center vs Gaming revenue
    over time, with the Q1 2022 crossover annotated.
    Used as Panel 2 in the main dashboard.
    """
    import plotly.graph_objects as go

    df = pd.read_sql(
        """SELECT period, segment, revenue_usd
           FROM nvidia_financials
           WHERE segment IN ('data_center', 'gaming')
           ORDER BY period""",
        conn,
    )
    if df.empty:
        log.warning("No segment data in DB — run load_nvidia_segments first.")
        return None

    df["period"] = pd.to_datetime(df["period"])
    df["revenue_bn"] = df["revenue_usd"] / 1e9

    dc   = df[df["segment"] == "data_center"]
    game = df[df["segment"] == "gaming"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dc["period"], y=dc["revenue_bn"],
        mode="lines", name="Data Center & AI",
        line=dict(color="#76b900", width=2.5),
    ))

    fig.add_trace(go.Scatter(
        x=game["period"], y=game["revenue_bn"],
        mode="lines", name="Gaming",
        line=dict(color="#00b4d8", width=2.5),
    ))

    # Mark the crossover
    fig.add_vline(
        x="2022-01-01",
        line_dash="dash",
        line_color="rgba(255,100,100,0.7)",
    )
    fig.add_annotation(
        x="2022-01-01", y=dc["revenue_bn"].max() * 0.6,
        text="AI Crossover<br>Q1 2022",
        showarrow=False,
        font=dict(color="rgba(255,100,100,0.9)", size=11),
        xanchor="left",
    )

    fig.update_layout(
        title="NVIDIA Quarterly Revenue: Data Center vs Gaming (USD bn)",
        template="plotly_dark",
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
        margin=dict(l=60, r=40, t=60, b=40),
    )

    return fig


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
    conn = sqlite3.connect(DB_PATH)
    load_nvidia_segments(conn)
    fig = build_segment_chart(conn)
    if fig:
        fig.show()
    conn.close()