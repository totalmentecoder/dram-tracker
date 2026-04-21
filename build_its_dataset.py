"""
ITS Dataset Builder
====================
Builds the PC-only time series dataset for the Interrupted Time Series model.

Unlike the DiD design, ITS does not require a control group. Instead it models
the trajectory of PC game RAM requirements over time and tests whether the
slope changed after the AI supply shock (break point: Q3 2022).

Output: its_dataset.csv — one row per PC game with:
- title, genre, year, release_date
- min_ram_gb, rec_ram_gb
- post: 1 if released 2023+, 0 if 2015-2022
- time_index: continuous time variable (years since 2015)
- time_since_break: time elapsed since break point (0 for pre-period)

The ITS regression will be:
RAM_t = α + β1·time + β2·post + β3·time_since_break + controls + ε

Where:
- β1 = pre-shock slope (RAM growth rate before 2022)
- β2 = level change at the break point
- β3 = slope change after the break point (the main finding)
- β3 < 0 → growth rate slowed after shock (flattening hypothesis)
- β3 > 0 → growth rate accelerated after shock
"""

import re
import sqlite3
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

DB_PATH  = Path("dram_tracker.db")
OUT_PATH = Path("its_dataset.csv")

BREAK_YEAR = 2022  # Q3 2022: NVIDIA Data Center revenue overtook Gaming
BASE_YEAR  = 2015  # Start of study window


def parse_release_year(date_str: str):
    """Extract year from mixed-format date strings."""
    if not date_str or str(date_str).strip() in ("", "Coming soon", "To be announced"):
        return None
    date_str = str(date_str).strip()
    for fmt in ("%d %b, %Y", "%d %b %Y", "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).year
        except ValueError:
            continue
    match = re.search(r"\b(20\d{2})\b", date_str)
    return int(match.group(1)) if match else None


def build_its_dataset(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Build the PC-only time series dataset for ITS analysis.
    """
    games = pd.read_sql(
        """SELECT title, genre, min_ram_gb, rec_ram_gb, release_date
           FROM game_requirements
           WHERE min_ram_gb IS NOT NULL""",
        conn,
    )

    log.info("Loaded %d games with RAM data.", len(games))

    # Parse release year
    games["year"] = games["release_date"].apply(parse_release_year)

    # Drop unparseable dates
    missing = games[games["year"].isna()]
    if not missing.empty:
        log.warning("Could not parse year for: %s", list(missing["title"]))
    games = games.dropna(subset=["year"])
    games["year"] = games["year"].astype(int)

    # Filter to study window
    games = games[(games["year"] >= BASE_YEAR) & (games["year"] <= 2026)]
    log.info("Games within study window (%d–2026): %d", BASE_YEAR, len(games))

    # ── ITS variables ─────────────────────────────────────────────────────────

    # post: treatment indicator — 1 if released after break point
    games["post"] = (games["year"] > BREAK_YEAR).astype(int)

    # time_index: continuous time since study start (for pre-shock slope)
    games["time_index"] = games["year"] - BASE_YEAR

    # time_since_break: counts time elapsed after break (0 in pre-period)
    # This is the key variable for detecting slope change
    games["time_since_break"] = ((games["year"] - BREAK_YEAR) * (games["year"] > BREAK_YEAR)).astype(int)

    # period label
    games["period"] = games["post"].map({0: "pre_ai", 1: "ai_intensive"})

    games = games.sort_values("year")

    # ── Summary ───────────────────────────────────────────────────────────────
    pre  = games[games["post"] == 0]
    post = games[games["post"] == 1]

    log.info("Pre-shock  (2015–2022): %d games | mean min RAM: %.2f GB | SD: %.2f",
             len(pre), pre["min_ram_gb"].mean(), pre["min_ram_gb"].std())
    log.info("Post-shock (2023–2026): %d games | mean min RAM: %.2f GB | SD: %.2f",
             len(post), post["min_ram_gb"].mean(), post["min_ram_gb"].std())
    log.info("Raw level change: %.2f GB", post["min_ram_gb"].mean() - pre["min_ram_gb"].mean())

    # Genre breakdown
    log.info("\nGenre distribution:")
    print(games.groupby(["genre", "period"])["min_ram_gb"].agg(["count", "mean"]).round(2))

    return games[[
        "title", "genre", "year", "release_date",
        "min_ram_gb", "rec_ram_gb",
        "post", "time_index", "time_since_break", "period"
    ]]


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    df   = build_its_dataset(conn)
    conn.close()

    df.to_csv(OUT_PATH, index=False)
    log.info("Dataset saved to %s (%d rows)", OUT_PATH, len(df))

    print("\nFirst 10 rows:")
    print(df.head(10).to_string(index=False))