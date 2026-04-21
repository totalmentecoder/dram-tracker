"""
DRAM Price & AI Infrastructure Tracker
=======================================
A live data pipeline correlating AI infrastructure demand (NVIDIA Data Center
revenue), consumer DRAM pricing (FRED PPI proxy), and PC game RAM requirements
(Steam API) — the empirical backbone of the author's MSc thesis.

Author : Salvatore Caldara
Contact: s.caldara@tilburguniversity.edu
GitHub : github.com/salvatorecaldara/dram-tracker

Requirements:
    pip install requests pandas yfinance fredapi plotly sqlalchemy python-dotenv

Setup:
    1. Get a free FRED API key at https://fred.stlouisfed.org/docs/api/api_key.html
    2. Create a .env file in this directory:
           FRED_API_KEY=your_key_here
    3. Run: python pipeline.py
"""

import os
import time
import re
import json
import sqlite3
import logging
from datetime import datetime, date
from pathlib import Path
from html.parser import HTMLParser

import requests
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from fredapi import Fred
from dotenv import load_dotenv

# ── Config ──────────────────────────────────────────────────────────────────

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

DB_PATH = Path("dram_tracker.db")

# FRED series: Producer Price Index – Semiconductor & Related Device Mfg.
# This is the best freely available proxy for memory chip manufacturing costs.
# Series ID: PCU334413334413  (Base: 2012=100)
FRED_SERIES = {
    "semiconductor_ppi": "PCU334413334413",
    "memory_ppi": "PCU334413A334413A",   # Memory chips specifically
}

# Steam Games: impèorted from games_list.py
from games_list import STEAM_GAMES

# ── Database setup ───────────────────────────────────────────────────────────

def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create SQLite database and schema if not present."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS dram_prices (
            date        TEXT PRIMARY KEY,
            series_id   TEXT NOT NULL,
            series_name TEXT NOT NULL,
            value       REAL NOT NULL,
            fetched_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS nvidia_financials (
            period      TEXT NOT NULL,
            segment     TEXT NOT NULL,
            revenue_usd REAL NOT NULL,
            fetched_at  TEXT NOT NULL,
            PRIMARY KEY (period, segment)
        );

        CREATE TABLE IF NOT EXISTS game_requirements (
            app_id          INTEGER NOT NULL,
            title           TEXT NOT NULL,
            genre           TEXT,
            min_ram_gb      REAL,
            rec_ram_gb      REAL,
            release_date    TEXT,
            fetched_at      TEXT NOT NULL,
            raw_min_req     TEXT,
            PRIMARY KEY (app_id)
        );
    """)
    conn.commit()
    log.info("Database initialised at %s", db_path)
    return conn


# ── FRED: DRAM price proxy ───────────────────────────────────────────────────

def fetch_dram_prices(conn: sqlite3.Connection, start: str = "2015-01-01") -> pd.DataFrame:
    """
    Pull DRAM-related PPI indices from FRED.
    Returns a tidy DataFrame and persists to SQLite.
    
    The Semiconductor PPI (PCU334413334413) serves as a manufacturing cost
    proxy. It tracks the price index for producers of memory chips, which
    correlates with — and partially drives — consumer DRAM spot prices.
    """
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY not found. Add it to your .env file.\n"
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    fred = Fred(api_key=api_key)
    rows = []
    fetched_at = datetime.utcnow().isoformat()

    for name, series_id in FRED_SERIES.items():
        try:
            log.info("Fetching FRED series: %s (%s)", name, series_id)
            data = fred.get_series(series_id, observation_start=start)
            for dt, value in data.items():
                if pd.isna(value):
                    continue
                rows.append({
                    "date": str(dt.date()),
                    "series_id": series_id,
                    "series_name": name,
                    "value": float(value),
                    "fetched_at": fetched_at,
                })
        except Exception as exc:
            log.warning("Could not fetch %s: %s", series_id, exc)

    df = pd.DataFrame(rows)
    if df.empty:
        log.warning("No FRED data retrieved.")
        return df

    # Upsert into SQLite
    cur = conn.cursor()
    cur.executemany(
        """INSERT OR REPLACE INTO dram_prices
           (date, series_id, series_name, value, fetched_at)
           VALUES (:date, :series_id, :series_name, :value, :fetched_at)""",
        df.to_dict("records"),
    )
    conn.commit()
    log.info("Stored %d FRED rows.", len(df))
    return df


# ── NVIDIA Financials ────────────────────────────────────────────────────────

def fetch_nvidia_revenue(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Pull NVIDIA quarterly financials via yfinance.
    Extracts total revenue as a proxy for AI infrastructure demand.
    
    Note: yfinance provides consolidated revenue, not segment breakdown.
    For Data Center vs Gaming split, see the enhancement note below.
    """
    log.info("Fetching NVIDIA financials from yfinance…")
    ticker = yf.Ticker("NVDA")
    
    try:
        # Quarterly income statement
        income = ticker.quarterly_income_stmt
        if income is None or income.empty:
            log.warning("No NVIDIA income data returned.")
            return pd.DataFrame()

        rows = []
        fetched_at = datetime.utcnow().isoformat()

        # Total Revenue row
        if "Total Revenue" in income.index:
            for col in income.columns:
                val = income.loc["Total Revenue", col]
                if pd.isna(val):
                    continue
                rows.append({
                    "period": str(col.date()),
                    "segment": "total_revenue",
                    "revenue_usd": float(val),
                    "fetched_at": fetched_at,
                })

        df = pd.DataFrame(rows).sort_values("period")
        
        cur = conn.cursor()
        cur.executemany(
            """INSERT OR REPLACE INTO nvidia_financials
               (period, segment, revenue_usd, fetched_at)
               VALUES (:period, :segment, :revenue_usd, :fetched_at)""",
            df.to_dict("records"),
        )
        conn.commit()
        log.info("Stored %d NVIDIA revenue rows.", len(df))
        return df

    except Exception as exc:
        log.error("NVIDIA fetch failed: %s", exc)
        return pd.DataFrame()

    # ── ENHANCEMENT (Week 4): Segment revenue ──────────────────────────────
    # yfinance does not expose segment-level data. For Data Center vs Gaming:
    # Option A: Parse NVIDIA quarterly earnings PDFs (IR page, free).
    # Option B: Use the SEC EDGAR API (free) for 10-Q filings.
    # Option C: Manually seed a CSV from public analyst reports.
    # The thesis uses NVIDIA Data Center revenue as the AI intensity proxy.
    # ────────────────────────────────────────────────────────────────────────


# ── Steam API: Game RAM Requirements ─────────────────────────────────────────

class _HTMLStripper(HTMLParser):
    """Minimal HTML tag stripper for parsing Steam requirement strings."""
    def __init__(self):
        super().__init__()
        self.reset()
        self._parts = []

    def handle_data(self, d):
        self._parts.append(d)

    def get_text(self):
        return " ".join(self._parts)


def _strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    return s.get_text()


def _parse_ram_gb(requirements_text: str) :
    """
    Extract RAM value in GB from Steam's requirements string.
    Handles formats like '16 GB RAM', '8GB Memory', '32 GB', '4096 MB RAM'.
    Returns None if no match found.
    """
    text = _strip_html(requirements_text)

    # Try GB pattern first
    gb_match = re.search(r"(\d+(?:\.\d+)?)\s*GB", text, re.IGNORECASE)
    if gb_match:
        return float(gb_match.group(1))

    # Fall back to MB
    mb_match = re.search(r"(\d+(?:\.\d+)?)\s*MB", text, re.IGNORECASE)
    if mb_match:
        return float(mb_match.group(1)) / 1024

    return None


def fetch_steam_requirements(conn: sqlite3.Connection, delay: float = 1.5) -> pd.DataFrame:
    """
    Pull system requirements for the defined game list from the Steam Store API.
    
    The Steam Store API is free and unauthenticated, but rate-limited.
    `delay` controls seconds between requests — keep at ≥ 1.5 to be polite.
    
    Returns a DataFrame with parsed minimum RAM values.
    """
    rows = []
    fetched_at = datetime.utcnow().isoformat()

    for title, (app_id, genre) in STEAM_GAMES.items():
        url = (
            f"https://store.steampowered.com/api/appdetails"
            f"?appids={app_id}&filters=basic,pc_requirements,release_date"
        )
        try:
            log.info("Fetching Steam data for: %s (AppID %d)", title, app_id)
            resp = requests.get(url, timeout=10, headers={"Accept-Language": "en-US"})
            resp.raise_for_status()
            data = resp.json()

            game_data = data.get(str(app_id), {})
            if not game_data.get("success"):
                log.warning("Steam returned no data for %s", title)
                continue

            details  = game_data["data"]
            pc_reqs  = details.get("pc_requirements", {})
            rel_date = details.get("release_date", {}).get("date", "")

            min_req_raw = pc_reqs.get("minimum", "")
            rec_req_raw = pc_reqs.get("recommended", "")

            min_ram = _parse_ram_gb(min_req_raw) if min_req_raw else None
            rec_ram = _parse_ram_gb(rec_req_raw) if rec_req_raw else None

            rows.append({
                "app_id":       app_id,
                "title":        title,
                "genre":        genre,
                "min_ram_gb":   min_ram,
                "rec_ram_gb":   rec_ram,
                "release_date": rel_date,
                "fetched_at":   fetched_at,
                "raw_min_req":  _strip_html(min_req_raw)[:500],
            })

        except requests.RequestException as exc:
            log.warning("Request failed for %s: %s", title, exc)
        except (KeyError, json.JSONDecodeError) as exc:
            log.warning("Parse error for %s: %s", title, exc)
        
        time.sleep(delay)  # Respect Steam's rate limits

    df = pd.DataFrame(rows)
    if df.empty:
        log.warning("No Steam data collected.")
        return df

    cur = conn.cursor()
    cur.executemany(
        """INSERT OR REPLACE INTO game_requirements
           (app_id, title, genre, min_ram_gb, rec_ram_gb, release_date, fetched_at, raw_min_req)
           VALUES (:app_id, :title, :genre, :min_ram_gb, :rec_ram_gb,
                   :release_date, :fetched_at, :raw_min_req)""",
        df.to_dict("records"),
    )
    conn.commit()
    log.info("Stored %d game requirement rows.", len(df))
    return df


# ── Plotly Dashboard ─────────────────────────────────────────────────────────

def build_dashboard(conn: sqlite3.Connection) -> go.Figure:
    """
    Build a three-panel Plotly dashboard:
      Panel 1 — Semiconductor PPI over time (DRAM cost proxy)
      Panel 2 — NVIDIA quarterly revenue (AI infrastructure demand)
      Panel 3 — Minimum PC RAM requirements per AAA title over time
    
    The visual argument: as NVIDIA Data Center revenue diverges from gaming
    revenue (AI demand spike), the semiconductor PPI rises — and AAA PC game
    minimum RAM requirements show signs of plateauing or inflating differently
    than the historical trend would predict.
    """
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=False,
        subplot_titles=(
            "Semiconductor Producer Price Index (FRED PCU334413334413)",
            "NVIDIA Total Quarterly Revenue — AI Demand Proxy (USD bn)",
            "AAA PC Game Minimum RAM Requirements (GB)",
        ),
        vertical_spacing=0.10,
    )

    # ── Panel 1: DRAM PPI ────────────────────────────────────────────────────
    ppi_df = pd.read_sql(
        "SELECT date, value FROM dram_prices WHERE series_name='semiconductor_ppi' ORDER BY date",
        conn,
    )
    if not ppi_df.empty:
        ppi_df["date"] = pd.to_datetime(ppi_df["date"])
        fig.add_trace(
            go.Scatter(
                x=ppi_df["date"], y=ppi_df["value"],
                mode="lines", name="Semiconductor PPI",
                line=dict(color="#00b4d8", width=2),
            ),
            row=1, col=1,
        )
        # Add vertical line at AI shock period (mid-2022)
        fig.add_vline(
            x="2022-01-01", line_dash="dash", line_color="rgba(255,100,100,0.6)",
        )

    # ── Panel 2: NVIDIA Segment Revenue ─────────────────────────────────────
    seg_df = pd.read_sql(
        """SELECT period, segment, revenue_usd
        FROM nvidia_financials
        WHERE segment IN ('data_center', 'gaming')
        ORDER BY period""",
        conn,
    )
    if not seg_df.empty:
        seg_df["period"] = pd.to_datetime(seg_df["period"])
        seg_df["revenue_bn"] = seg_df["revenue_usd"] / 1e9
        dc   = seg_df[seg_df["segment"] == "data_center"]
        game = seg_df[seg_df["segment"] == "gaming"]
        fig.add_trace(
            go.Scatter(
                x=dc["period"], y=dc["revenue_bn"],
                mode="lines", name="Data Center & AI",
                line=dict(color="#76b900", width=2.5),
            ),
            row=2, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=game["period"], y=game["revenue_bn"],
                mode="lines", name="Gaming",
                line=dict(color="#00b4d8", width=2.5),
            ),
            row=2, col=1,
        )
        fig.add_vline(
            x="2022-01-01",
            line_dash="dash",
            line_color="rgba(255,100,100,0.7)",
            row=2, col=1,
        )

    # ── Panel 3: Game RAM Requirements ──────────────────────────────────────
    games_df = pd.read_sql(
        "SELECT title, min_ram_gb, rec_ram_gb, release_date FROM game_requirements",
        conn,
    )
    if not games_df.empty:
        # Parse release dates — Steam uses "DD Mon, YYYY" or "Mon DD, YYYY"
        def parse_date(d):
            if not d or str(d).strip() in ("", "Coming soon", "To be announced"):
                return None
            import re
            for fmt in ("%d %b, %Y", "%d %b %Y", "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
                try:
                    from datetime import datetime
                    return datetime.strptime(str(d).strip(), fmt)
                except ValueError:
                    continue
            match = re.search(r"\b(20\d{2})\b", str(d))
            if match:
                from datetime import datetime
                return datetime(int(match.group(1)), 1, 1)
            return None

        games_df["release_dt"] = games_df["release_date"].apply(parse_date)
        
        games_df = games_df.dropna(subset=["release_dt", "min_ram_gb"])
        games_df = games_df.sort_values("release_dt")

        fig.add_trace(
            go.Scatter(
                x=games_df["release_dt"], y=games_df["min_ram_gb"],
                mode="markers+lines", name="Min RAM (GB)",
                marker=dict(size=10, color="#f4a261"),
                line=dict(color="#f4a261", width=1.5, dash="dot"),
                text=games_df["title"], hovertemplate="%{text}<br>%{y} GB<extra></extra>",
            ),
            row=3, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=games_df["release_dt"], y=games_df["rec_ram_gb"],
                mode="markers", name="Rec RAM (GB)",
                marker=dict(size=8, color="#e9c46a", symbol="diamond"),
                text=games_df["title"], hovertemplate="%{text}<br>%{y} GB (rec)<extra></extra>",
            ),
            row=3, col=1,
        )
        
        fig.add_vline(
            x="2022-01-01",
            line_dash="dash",
            line_color="rgba(255,100,100,0.7)",
            row=2, col=1            
        )

    # ── Layout ───────────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text="DRAM Price & AI Infrastructure Tracker",
            font=dict(size=20, family="Georgia, serif"),
        ),
        height=950,
        template="plotly_dark",
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        margin=dict(l=60, r=40, t=80, b=40),
    )

    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.07)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.07)")

    return fig


# ── Main entry point ─────────────────────────────────────────────────────────

def run_pipeline(
    fetch_fred: bool   = True,
    fetch_nvda: bool   = True,
    fetch_steam: bool  = True,
    show_dashboard: bool = True,
    save_html: bool    = True,
) -> None:
    """
    Run the full pipeline.
    
    Set individual fetch flags to False to skip re-fetching cached data.
    SQLite acts as a local cache — safe to re-run incrementally.
    """
    conn = init_db()

    if fetch_fred:
        fetch_dram_prices(conn)

    if fetch_nvda:
        fetch_nvidia_revenue(conn)

    if fetch_steam:
        # Note: Steam API fetches take ~25 seconds for the default game list
        # due to the polite rate-limit delay.
        fetch_steam_requirements(conn)
        from manual_loader import load_manual_overrides
        load_manual_overrides(conn)

    fig = build_dashboard(conn)

    if save_html:
        out_path = Path("dashboard.html")
        fig.write_html(out_path, include_plotlyjs="cdn")
        log.info("Dashboard saved to %s", out_path.resolve())

    if show_dashboard:
        fig.show()

    conn.close()
    log.info("Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()
