"""
Manual Overrides Loader
=======================
Loads manually verified RAM requirements from manual_overrides.csv
into the dram_tracker SQLite database, correcting bad Steam API data.

Run this AFTER pipeline.py to apply corrections.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")

DB_PATH  = Path("dram_tracker.db")
CSV_PATH = Path("manual_overrides.csv")


def load_manual_overrides(conn, csv_path=CSV_PATH):
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

        cur.execute(
            "SELECT app_id FROM game_requirements WHERE LOWER(title) = LOWER(?)",
            (title,)
        )
        result = cur.fetchone()

        if not result:
            from games_list import STEAM_GAMES
            app_id_val = None
            genre_val = None
            for t, (aid, g) in STEAM_GAMES.items():
                if t.lower() == title.lower():
                    app_id_val = aid
                    genre_val = g
                    break

            if app_id_val and min_ram is not None:
                cur.execute(
                    """INSERT OR IGNORE INTO game_requirements
                       (app_id, title, genre, min_ram_gb, rec_ram_gb, release_date, fetched_at, raw_min_req)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        app_id_val, title, genre_val, min_ram, rec_ram,
                        str(rel_date).strip() if rel_date else None,
                        datetime.utcnow().isoformat(), "manual"
                    )
                )
                log.info("Inserted new game:  %s", title)
                updated += 1
            else:
                not_found.append(title)
            continue

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
            "These titles were not found in the database:\n  %s",
            "\n  ".join(not_found)
        )


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    load_manual_overrides(conn)
    conn.close()