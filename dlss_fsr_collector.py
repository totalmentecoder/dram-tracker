"""
DLSS/FSR Adoption Collector
============================
Collects AI upscaling technology adoption data for each game in the sample.
This data is required for H2 and H4 hypothesis testing.

Strategy:
1. Query PCGamingWiki Cargo API for DLSS/FSR fields per game
2. Fall back to manual_upscaling.csv for games the API can't resolve
3. Store results in dram_tracker.db and export to upscaling_dataset.csv

Output binary variable:
- has_upscaling = 1 if game supports DLSS, FSR, or XeSS at release
- has_upscaling = 0 if no upscaling support documented
"""

import time
import sqlite3
import logging
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

DB_PATH  = Path("dram_tracker.db")
OUT_PATH = Path("upscaling_dataset.csv")
MANUAL_PATH = Path("manual_upscaling.csv")
PCGW_API = "https://www.pcgamingwiki.com/w/api.php"


# ── Database ──────────────────────────────────────────────────────────────────

def init_upscaling_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS upscaling_support (
            app_id        INTEGER PRIMARY KEY,
            title         TEXT NOT NULL,
            has_dlss      INTEGER DEFAULT 0,
            has_fsr       INTEGER DEFAULT 0,
            has_xess      INTEGER DEFAULT 0,
            has_upscaling INTEGER DEFAULT 0,
            source        TEXT,
            fetched_at    TEXT
        )
    """)
    conn.commit()


# ── PCGamingWiki Query ────────────────────────────────────────────────────────

def query_pcgw_upscaling(steam_app_id: int, title: str, delay: float = 1.5):
    """
    Query PCGamingWiki Cargo API for DLSS/FSR support.
    Uses the Video_settings table joined with Infobox_game via Steam App ID.
    """
    params = {
        "action":  "cargoquery",
        "tables":  "Infobox_game,Video_settings",
        "fields":  "Video_settings.DLSS,Video_settings.FSR,Video_settings.XeSS",
        "join_on": "Infobox_game._pageID=Video_settings._pageID",
        "where":   f'Infobox_game.Steam_AppID HOLDS "{steam_app_id}"',
        "format":  "json",
        "limit":   "3",
    }

    try:
        resp = requests.get(
            PCGW_API, params=params, timeout=10,
            headers={"User-Agent": "dram-tracker-thesis/1.0 (academic research)"}
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("cargoquery", [])

        if not results:
            return None

        row = results[0].get("title", {})
        dlss = row.get("DLSS", "")
        fsr  = row.get("FSR", "")
        xess = row.get("XeSS", "")

        has_dlss = int(bool(dlss and dlss.strip() not in ("", "false", "N/A", "none")))
        has_fsr  = int(bool(fsr  and fsr.strip()  not in ("", "false", "N/A", "none")))
        has_xess = int(bool(xess and xess.strip() not in ("", "false", "N/A", "none")))

        log.info("%-45s DLSS:%d FSR:%d XeSS:%d", title, has_dlss, has_fsr, has_xess)

        return {
            "has_dlss":      has_dlss,
            "has_fsr":       has_fsr,
            "has_xess":      has_xess,
            "has_upscaling": int(has_dlss or has_fsr or has_xess),
            "source":        "PCGamingWiki",
        }

    except Exception as exc:
        log.warning("PCGW query failed for %s: %s", title, exc)
        return None
    finally:
        time.sleep(delay)


# ── Manual Override Loader ────────────────────────────────────────────────────

def load_manual_upscaling(conn):
    """
    Load manual_upscaling.csv into the database.
    Format: title, has_dlss, has_fsr, has_xess, source
    """
    if not MANUAL_PATH.exists():
        log.info("No manual_upscaling.csv found — skipping manual overrides.")
        return

    df = pd.read_csv(MANUAL_PATH)
    cur = conn.cursor()

    for _, row in df.iterrows():
        title = row["title"].strip()
        cur.execute(
            "SELECT app_id FROM game_requirements WHERE LOWER(title) = LOWER(?)",
            (title,)
        )
        result = cur.fetchone()
        if not result:
            log.warning("Manual upscaling: title not found in DB: %s", title)
            continue

        app_id = result[0]
        has_dlss = int(row.get("has_dlss", 0))
        has_fsr  = int(row.get("has_fsr", 0))
        has_xess = int(row.get("has_xess", 0))

        cur.execute(
            """INSERT OR REPLACE INTO upscaling_support
               (app_id, title, has_dlss, has_fsr, has_xess, has_upscaling, source, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (app_id, title, has_dlss, has_fsr, has_xess,
             int(has_dlss or has_fsr or has_xess),
             str(row.get("source", "manual")),
             datetime.utcnow().isoformat())
        )
        log.info("Manual override applied: %s", title)

    conn.commit()


# ── Main Collection ───────────────────────────────────────────────────────────

def collect_upscaling_data(conn):
    from games_list import STEAM_GAMES

    init_upscaling_table(conn)
    cur = conn.cursor()
    fetched_at = datetime.utcnow().isoformat()

    for title, (app_id, genre) in STEAM_GAMES.items():
        # Skip if already collected
        cur.execute("SELECT 1 FROM upscaling_support WHERE app_id = ?", (app_id,))
        if cur.fetchone():
            log.info("Skipping (cached): %s", title)
            continue

        result = query_pcgw_upscaling(app_id, title)

        if result:
            cur.execute(
                """INSERT OR REPLACE INTO upscaling_support
                   (app_id, title, has_dlss, has_fsr, has_xess, has_upscaling, source, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (app_id, title,
                 result["has_dlss"], result["has_fsr"], result["has_xess"],
                 result["has_upscaling"], result["source"], fetched_at)
            )
            conn.commit()
        else:
            # Insert placeholder — will be filled by manual override
            cur.execute(
                """INSERT OR IGNORE INTO upscaling_support
                   (app_id, title, has_dlss, has_fsr, has_xess, has_upscaling, source, fetched_at)
                   VALUES (?, ?, 0, 0, 0, 0, 'pending', ?)""",
                (app_id, title, fetched_at)
            )
            conn.commit()

    # Apply manual overrides on top
    load_manual_upscaling(conn)


# ── Export ────────────────────────────────────────────────────────────────────

def export_upscaling_dataset(conn):
    df = pd.read_sql("""
        SELECT
            g.title, g.genre, g.min_ram_gb, g.release_date,
            u.has_dlss, u.has_fsr, u.has_xess, u.has_upscaling, u.source
        FROM game_requirements g
        LEFT JOIN upscaling_support u ON g.app_id = u.app_id
        WHERE g.min_ram_gb IS NOT NULL
        ORDER BY g.release_date
    """, conn)

    df.to_csv(OUT_PATH, index=False)
    log.info("Exported %d rows to %s", len(df), OUT_PATH)

    pending = df[df["source"] == "pending"]
    if not pending.empty:
        log.warning(
            "%d games need manual verification — add to manual_upscaling.csv:\n  %s",
            len(pending),
            "\n  ".join(pending["title"].tolist())
        )

    return df


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(df):
    df["year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year
    df = df.dropna(subset=["year", "has_upscaling"])
    df["period"] = df["year"].apply(lambda y: "ai_intensive" if y >= 2023 else "pre_ai")

    print("\n=== Upscaling Adoption Summary ===")
    print(df.groupby("period")["has_upscaling"].agg(["count", "sum", "mean"]).round(3))

    print("\n=== By Genre ===")
    print(df.groupby(["genre", "period"])["has_upscaling"].agg(["count", "mean"]).round(3))


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    collect_upscaling_data(conn)
    df = export_upscaling_dataset(conn)
    print_summary(df)
    conn.close()
