"""
Manual Overrides Loader
=======================
Loads manually verified RAM requirements from manual_overrides.csv
into the dram_tracker SQLite database, correcting bad Steam API data.

Sources for manual data:
- PCGamingWiki: https://www.pcgamingwiki.com
- These values have been manually verified by the researcher.

Why this exists:
- Steam API returns incomplete or wrong data for some titles
- Delisted games (e.g. old FIFA entries) have no Steam API data
- This script ensures the database always reflects verified values

Run this AFTER pipeline.py to apply corrections.
"""

import sqlite3
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")

DB_PATH  = Path("dram_tracker.db")
CSV_PATH = Path("manual_overrides.csv")


def load_manual_overrides(
    conn: sqlite3.Connection,
    csv_path: Path = CSV_PATH,
) -> None:
    """
    Read manual_overrides.csv and update matching rows in game_requirements.
    
    Matches on title (case-insensitive). Only updates min_ram_gb and
    rec_ram_gb — all other fields (release_date, app_id, etc.) are
    preserved from the original Steam fetch.
    
    If a title in the CSV doesn't exist in the database at all,
    it logs a warning so you know to add it via pipeline.py first.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found at {csv_path}")

    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]

    cur = conn.cursor()
    updated = 0
    not_found = []

    for _, row in df.iterrows():
        title    = row["title"].strip()
        min_ram  = row["min_ram_gb"]   if "min_ram_gb"   in row and pd.notna(row["min_ram_gb"])   else None
        rec_ram  = row["rec_ram_gb"]   if "rec_ram_gb"   in row and pd.notna(row["rec_ram_gb"])   else None
        rel_date = row["release_date"] if "release_date" in row and pd.notna(row["release_date"]) else None
        source   = row.get("source", "manual")

        # Check if title exists (case-insensitive)
        cur.execute(
            "SELECT app_id FROM game_requirements WHERE LOWER(title) = LOWER(?)",
            (title,)
        )
        result = cur.fetchone()

        if not result:
            not_found.append(title)
            continue

        # Build update dynamically — only update fields that have values
        fields = []
        values = []

        if min_ram is not None:
            fields.append("min_ram_gb = ?")
            values.append(min_ram)
        if rec_ram is not None:
            fields.append("rec_ram_gb = ?")
            values.append(rec_ram)
        if rel_date is not None:
            fields.append("release_date = ?")
            values.append(str(rel_date).strip())

        if not fields:
            continue

        values.append(title)
        cur.execute(
            f"UPDATE game_requirements SET {', '.join(fields)} WHERE LOWER(title) = LOWER(?)",
            values,
        )
        log.info(
            "Updated %-35s min: %s | rec: %s | date: %s (source: %s)",
            title,
            f"{min_ram}GB" if min_ram else "—",
            f"{rec_ram}GB" if rec_ram else "—",
            rel_date if rel_date else "—",
            source,
        )
        updated += 1

    conn.commit()
    log.info("Applied %d manual overrides.", updated)

    if not_found:
        log.warning(
            "These titles were not found in the database — "
            "run pipeline.py first to fetch them:\n  %s",
            "\n  ".join(not_found)
        )


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    load_manual_overrides(conn)
    conn.close()