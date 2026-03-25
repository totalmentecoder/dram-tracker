"""
Pre-Trend Historical RAM Requirements
======================================
STANDALONE SCRIPT — completely separate from pipeline.py and dram_tracker.db.

Purpose:
    Generate a descriptive chart showing the historical growth of PC game
    minimum RAM requirements from 2000-2022, establishing the Wirth's Law
    baseline BEFORE the AI supply shock period.

    This chart goes in the thesis INTRODUCTION or LITERATURE REVIEW as
    visual motivation — it is NOT part of the DiD analysis.

How it works:
    1. Reads pretrend_games.csv — a curated list of landmark AAA titles
    2. Queries the PCGamingWiki Cargo API for each game's minimum RAM
       using the Steam App ID as the lookup key
    3. Stores results in a separate pretrend.db (never touches dram_tracker.db)
    4. Generates a standalone Plotly chart saved as pretrend_chart.html

PCGamingWiki API documentation:
    https://www.pcgamingwiki.com/wiki/PCGamingWiki:API
    Free, no authentication required.

Run:
    python pretrend.py
"""

import re
import time
import sqlite3
import logging
from pathlib import Path

import requests
import pandas as pd
import plotly.graph_objects as go

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

CSV_PATH  = Path("pretrend_games.csv")
DB_PATH   = Path("pretrend.db")
PCGW_API  = "https://www.pcgamingwiki.com/w/api.php"


# ── Database ──────────────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pretrend_requirements (
            steam_app_id  INTEGER PRIMARY KEY,
            title         TEXT NOT NULL,
            franchise     TEXT,
            year          INTEGER,
            min_ram_gb    REAL,
            rec_ram_gb    REAL,
            source        TEXT,
            fetched_at    TEXT
        );
    """)
    conn.commit()


# ── PCGamingWiki API ───────────────────────────────────────────────────────────

def _parse_ram_string(val):
    """
    Parse PCGamingWiki RAM strings to GB.
    Handles: '8 GB', '512 MB', '1.5 GB', '256MB', etc.
    Returns float in GB or None.
    """
    if not val or str(val).strip() in ("", "None", "N/A"):
        return None

    val = str(val).strip()

    gb_match = re.search(r"(\d+(?:\.\d+)?)\s*GB", val, re.IGNORECASE)
    if gb_match:
        return float(gb_match.group(1))

    mb_match = re.search(r"(\d+(?:\.\d+)?)\s*MB", val, re.IGNORECASE)
    if mb_match:
        return float(mb_match.group(1)) / 1024

    # Plain number — assume GB if >= 1, MB if < 1
    num_match = re.search(r"(\d+(?:\.\d+)?)", val)
    if num_match:
        num = float(num_match.group(1))
        return num if num >= 1 else num / 1024

    return None


def query_pcgw(steam_app_id: int, title: str, delay: float = 1.0):
    """
    Two-step PCGamingWiki query:
    Step 1 — get the PCGW page ID from the Steam App ID
    Step 2 — query system requirements using that page ID
    """
    try:
        # Step 1: get page ID
        redirect_url = f"https://www.pcgamingwiki.com/api/appid.php?appid={steam_app_id}"
        resp = requests.get(redirect_url, timeout=10, allow_redirects=False,
                           headers={"User-Agent": "dram-tracker-thesis/1.0"})
        
        # The redirect URL contains the page name
        location = resp.headers.get("Location", "")
        if not location:
            log.warning("No PCGW page for: %s (AppID %d)", title, steam_app_id)
            return None

        # Extract page name from redirect URL
        page_name = location.split("/wiki/")[-1]

        # Step 2: query system requirements by page name
        params = {
            "action": "cargoquery",
            "tables": "Infobox_game,System_requirements",
            "fields": "System_requirements.minRAM,System_requirements.recRAM",
            "join_on": "Infobox_game._pageID=System_requirements._pageID",
            "where": f'Infobox_game._pageName="{page_name}"',
            "format": "json",
            "limit": "5",
        }
        resp2 = requests.get(PCGW_API, params=params, timeout=10,
                            headers={"User-Agent": "dram-tracker-thesis/1.0"})
        resp2.raise_for_status()
        data = resp2.json()

        results = data.get("cargoquery", [])
        if not results:
            log.warning("No system requirements on PCGW for: %s", title)
            return None

        row = results[0].get("title", {})
        min_ram = _parse_ram_string(row.get("minRAM"))
        rec_ram = _parse_ram_string(row.get("recRAM"))

        log.info("%-45s min: %s GB | rec: %s GB",
                 title,
                 f"{min_ram:.2f}" if min_ram else "—",
                 f"{rec_ram:.2f}" if rec_ram else "—")

        return {"min_ram_gb": min_ram, "rec_ram_gb": rec_ram}

    except Exception as exc:
        log.warning("PCGW query failed for %s: %s", title, exc)
        return None
    finally:
        time.sleep(delay)


# ── Data Collection ───────────────────────────────────────────────────────────

def collect_pretrend_data(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    For each game in pretrend_games.csv, query PCGamingWiki and store results.
    Skips games already in the database (safe to re-run).
    """
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Game list not found: {CSV_PATH}")

    games_df = pd.read_csv(CSV_PATH)
    cur = conn.cursor()
    from datetime import datetime
    fetched_at = datetime.utcnow().isoformat()

    for _, row in games_df.iterrows():
        app_id    = int(row["steam_app_id"])
        title     = row["title"].strip()
        franchise = row.get("franchise", "")
        year      = int(row["year"])

        # Skip if already fetched
        cur.execute("SELECT 1 FROM pretrend_requirements WHERE steam_app_id = ?", (app_id,))
        if cur.fetchone():
            log.info("Skipping (cached): %s", title)
            continue

        result = query_pcgw(app_id, title)

        cur.execute(
            """INSERT OR REPLACE INTO pretrend_requirements
               (steam_app_id, title, franchise, year, min_ram_gb, rec_ram_gb, source, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                app_id, title, franchise, year,
                result["min_ram_gb"] if result else None,
                result["rec_ram_gb"] if result else None,
                "PCGamingWiki",
                fetched_at,
            )
        )
        conn.commit()

    return pd.read_sql("SELECT * FROM pretrend_requirements ORDER BY year", conn)


# ── Chart ─────────────────────────────────────────────────────────────────────

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


def build_pretrend_chart(df: pd.DataFrame) -> go.Figure:
    """
    Build a scatter + trend line chart showing minimum RAM requirements
    for landmark AAA PC titles from 2000-2022.

    Visual argument: RAM requirements followed a steady upward trend
    (consistent with Wirth's Law) until approximately 2022, when they
    plateaued at 8GB. This establishes the pre-treatment baseline for
    the DiD analysis.
    """
    df = df.dropna(subset=["min_ram_gb", "year"])
    df = df[df["year"] <= 2022]

    fig = go.Figure()

    # Plot each franchise as a separate colored series
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

    # Add overall trend line using all data points
    if len(df) > 2:
        import numpy as np
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
        legend=dict(
            orientation="v",
            x=1.02, y=1,
            bgcolor="rgba(0,0,0,0.4)",
        ),
        margin=dict(l=60, r=180, t=80, b=60),
    )

    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.07)", dtick=2)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.07)")

    return fig


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    log.info("Collecting pre-trend data from PCGamingWiki…")
    df = collect_pretrend_data(conn)
    conn.close()

    log.info("Building chart…")
    fig = build_pretrend_chart(df)

    out = Path("pretrend_chart.html")
    fig.write_html(out, include_plotlyjs="cdn")
    log.info("Chart saved to %s", out.resolve())
    fig.show()