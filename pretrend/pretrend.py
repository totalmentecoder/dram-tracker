"""
Pre-Trend Historical RAM Requirements
======================================
STANDALONE SCRIPT — completely separate from pipeline.py and dram_tracker.db.

Purpose:
    Generate a descriptive chart showing the historical growth of PC game
    minimum RAM requirements from 2000-2022, establishing the Wirth's Law
    baseline BEFORE the AI supply shock period.

    This chart goes in the thesis INTRODUCTION or LITERATURE REVIEW as
    visual motivation — it is NOT part of the ITS analysis.

How it works:
    Reads pretrend_games.csv directly — no API calls, no database.
    CSV must have columns: title, franchise, year, steam_app_id, min_ram_gb

Run:
    python pretrend.py
"""

import logging
from pathlib import Path

import pandas as pd
import numpy as np
import plotly.graph_objects as go

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

CSV_PATH = Path("pretrend_games.csv")

FRANCHISE_COLORS = {
    "GTA":               "#e63946",
    "Assassin's Creed":  "#457b9d",
    "Far Cry":           "#f4a261",
    "Call of Duty":      "#2a9d8f",
    "FIFA":              "#8ecae6",
    "Halo":              "#264653",
    "Crysis":            "#e9c46a",
    "Witcher":           "#a8dadc",
    "Elder Scrolls":     "#6a4c93",
    "Battlefield":       "#ff6b6b",
}


def collect_pretrend_data() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"CSV not found at {CSV_PATH}. "
            "Make sure pretrend_games.csv has a min_ram_gb column filled in."
        )
    df = pd.read_csv(CSV_PATH)
    df.columns = [c.strip() for c in df.columns]

    if "min_ram_gb" not in df.columns:
        raise ValueError(
            "pretrend_games.csv is missing the 'min_ram_gb' column. "
            "Add it and fill in the values manually from PCGamingWiki."
        )

    df = df.dropna(subset=["min_ram_gb"])
    df["year"] = df["year"].astype(int)
    log.info("Loaded %d games with RAM data.", len(df))
    return df


def build_pretrend_chart(df: pd.DataFrame) -> go.Figure:
    df = df[df["year"] <= 2022].copy()

    fig = go.Figure()

    franchises = df["franchise"].unique()
    for franchise in sorted(franchises):
        fdf = df[df["franchise"] == franchise].sort_values("year")
        color = FRANCHISE_COLORS.get(franchise, "#888888")

        fig.add_trace(go.Scatter(
            x=fdf["year"],
            y=fdf["min_ram_gb"],
            mode="lines+markers",
            name=franchise,
            line=dict(color=color, width=1.5),
            marker=dict(size=8, color=color),
            text=fdf["title"],
            hovertemplate="%{text}<br>%{x} — %{y} GB<extra></extra>",
        ))

    # Overall trend line
    if len(df) > 2:
        z = np.polyfit(df["year"], df["min_ram_gb"], 1)
        p = np.poly1d(z)
        years_range = list(range(int(df["year"].min()), 2023))
        fig.add_trace(go.Scatter(
            x=years_range,
            y=[p(y) for y in years_range],
            mode="lines",
            name="Overall trend",
            line=dict(color="rgba(255,255,255,0.4)", width=2, dash="dot"),
            hoverinfo="skip",
        ))

    fig.update_layout(
        title=dict(
            text="AAA PC Game Minimum RAM Requirements (2000–2022)<br>"
                 "<sup>Pre-treatment baseline — Wirth's Law in action</sup>",
            font=dict(size=18, family="Georgia, serif"),
        ),
        xaxis_title="Release Year",
        yaxis_title="Minimum RAM (GB)",
        template="plotly_dark",
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        height=600,
        legend=dict(orientation="v", x=1.02, y=1, bgcolor="rgba(0,0,0,0.4)"),
        margin=dict(l=60, r=180, t=80, b=60),
    )

    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.07)", dtick=2)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.07)")

    return fig


if __name__ == "__main__":
    df = collect_pretrend_data()

    fig = build_pretrend_chart(df)

    out = Path("pretrend_chart.html")
    fig.write_html(out, include_plotlyjs="cdn")
    log.info("Chart saved to %s", out.resolve())
    fig.show()
