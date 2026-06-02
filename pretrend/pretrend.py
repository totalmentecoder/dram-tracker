"""
Pre-Trend Historical RAM Requirements
======================================
Reads pretrend_games.csv and generates a chart showing the historical
growth of PC game minimum RAM requirements from 2000-2022.

This chart goes in the thesis INTRODUCTION or LITERATURE REVIEW as
visual motivation for the Wirth's Law baseline.
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
    "Halo":              "#e9c46a",
    "Crysis":            "#ffb703",
    "Witcher":           "#a8dadc",
    "Elder Scrolls":     "#6a4c93",
    "Battlefield":       "#ff6b6b",
}


def collect_pretrend_data() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found at {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    df.columns = [c.strip() for c in df.columns]
    df = df.dropna(subset=["min_ram_gb"])
    df["year"] = df["year"].astype(int)
    log.info("Loaded %d games with RAM data.", len(df))
    return df


def build_pretrend_chart(df: pd.DataFrame) -> go.Figure:
    df = df[df["year"] <= 2022].copy()

    fig = go.Figure()

    # ── Franchise lines ───────────────────────────────────────────────────────
    franchises = df["franchise"].unique()
    for franchise in sorted(franchises):
        fdf = df[df["franchise"] == franchise].sort_values("year")
        if len(fdf) < 2:
            continue  # Skip single-point franchises
        color = FRANCHISE_COLORS.get(franchise, "#888888")

        fig.add_trace(go.Scatter(
            x=fdf["year"],
            y=fdf["min_ram_gb"],
            mode="lines+markers",
            name=franchise,
            line=dict(color=color, width=2),
            marker=dict(size=7, color=color),
            text=fdf["title"],
            hovertemplate="%{text}<br>%{x} — %{y} GB<extra></extra>",
            opacity=0.85,
        ))

    # ── Overall trend line (thick, prominent) ─────────────────────────────────
    if len(df) > 2:
        z = np.polyfit(df["year"], df["min_ram_gb"], 1)
        p = np.poly1d(z)
        years_range = list(range(2000, 2023))
        trend_y = [max(0, p(y)) for y in years_range]

        fig.add_trace(go.Scatter(
            x=years_range,
            y=trend_y,
            mode="lines",
            name="Overall trend",
            line=dict(
                color="rgba(255,255,255,0.9)",
                width=4,
                dash="dot"
            ),
            hoverinfo="skip",
        ))

    # ── Layout ────────────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text="AAA PC Game Minimum RAM Requirements (2000–2022)<br>"
                 "<sup>Pre-treatment baseline — consistent growth consistent with Wirth's Law</sup>",
            font=dict(size=17, family="Georgia, serif"),
        ),
        xaxis=dict(
            title="Release Year",
            tickmode="linear",
            dtick=2,
            showgrid=True,
            gridcolor="rgba(255,255,255,0.07)",
        ),
        yaxis=dict(
            title="Minimum RAM (GB)",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.07)",
        ),
        template="plotly_dark",
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        height=550,
        legend=dict(
            orientation="v",
            x=1.02,
            y=1,
            bgcolor="rgba(15,17,23,0.8)",
            bordercolor="rgba(255,255,255,0.15)",
            borderwidth=1,
            font=dict(size=12),
        ),
        margin=dict(l=60, r=200, t=90, b=60),
        font=dict(size=12),
    )

    return fig


if __name__ == "__main__":
    df = collect_pretrend_data()
    fig = build_pretrend_chart(df)

    out = Path("pretrend_chart.html")
    fig.write_html(out, include_plotlyjs="cdn")
    log.info("Chart saved to %s", out.resolve())
    fig.show()
