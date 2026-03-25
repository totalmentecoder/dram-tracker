"""
DiD Dataset Builder
===================
Creates the panel dataset required for the Difference-in-Differences model.

For each cross-platform game in game_requirements, this script:
1. Takes the existing PC row
2. Creates a matching console row with fixed 16GB RAM (PS5/Xbox Series X spec)
3. Assigns period labels (pre_ai: 2019-2022, ai_intensive: 2023-2026)
4. Exports the final panel to did_dataset.csv for use in R

The resulting dataset has two observations per game:
- One PC row (treatment group) — variable RAM requirements
- One Console row (control group) — fixed 16GB hardware spec

This structure is required for the DiD regression:
RAM_it = α + β1·PC + β2·Post + β3·(PC × Post) + controls + ε

Where β3 is the causal effect of the AI supply shock on PC RAM requirements.

Console memory specs (fixed):
- PlayStation 5:    16 GB GDDR6 unified memory
- Xbox Series X:    16 GB GDDR6 unified memory
"""

import sqlite3
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

DB_PATH  = Path("dram_tracker.db")
OUT_PATH = Path("did_dataset.csv")

# Console fixed memory spec — PS5 and Xbox Series X both have 16GB
CONSOLE_RAM_GB = 16.0

# Period cutoff — confirmed empirically via structural break in DRAM prices
# Q1 2022: first quarter where NVIDIA Data Center revenue exceeded Gaming
AI_SHOCK_YEAR = 2023  # Conservative: use when structural change became visible to developers


def parse_release_year(date_str: str):
    """
    Extract year from Steam/manual release date strings.
    Handles formats: '3 Feb, 2022', '19 Oct 2021', '23 Jan, 2025'
    Returns integer year or None.
    """
    if not date_str or date_str.strip() in ("", "Coming soon", "To be announced"):
        return None

    date_str = date_str.strip()

    # Try common formats
    for fmt in ("%d %b, %Y", "%d %b %Y", "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).year
        except ValueError:
            continue

    # Last resort — extract 4-digit year
    import re
    match = re.search(r"\b(20\d{2})\b", date_str)
    if match:
        return int(match.group(1))

    return None


def build_did_dataset(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Build the panel dataset for DiD analysis.

    Steps:
    1. Load all games from game_requirements
    2. Parse release years and assign period labels
    3. Create PC rows (treatment)
    4. Create Console rows (control) with fixed 16GB
    5. Stack and export
    """
    games = pd.read_sql(
        """SELECT title, min_ram_gb, rec_ram_gb, release_date
           FROM game_requirements
           WHERE min_ram_gb IS NOT NULL""",
        conn,
    )

    log.info("Loaded %d games with RAM data.", len(games))

    # Parse release year
    games["year"] = games["release_date"].apply(parse_release_year)

    # Drop games with unparseable dates
    missing_year = games[games["year"].isna()]
    if not missing_year.empty:
        log.warning("Could not parse year for: %s", list(missing_year["title"]))

    games = games.dropna(subset=["year"])
    games["year"] = games["year"].astype(int)

    # Filter to study window 2019-2026
    games = games[(games["year"] >= 2019) & (games["year"] <= 2026)]
    log.info("Games within study window (2019-2026): %d", len(games))

    # Assign period
    # Pre-AI:       2019-2022 (stable/declining DRAM prices, pre-shock)
    # AI-intensive: 2023-2026 (post-shock, developers responding to market signals)
    games["post"] = (games["year"] >= AI_SHOCK_YEAR).astype(int)
    games["period"] = games["post"].map({0: "pre_ai", 1: "ai_intensive"})

    rows = []

    for _, game in games.iterrows():
        # ── PC row (treatment group) ──────────────────────────────────────
        rows.append({
            "title":       game["title"],
            "platform":    "PC",
            "pc_dummy":    1,          # Treatment indicator
            "post":        game["post"],
            "did":         game["post"] * 1,  # PC × Post interaction
            "min_ram_gb":  game["min_ram_gb"],
            "rec_ram_gb":  game["rec_ram_gb"],
            "year":        game["year"],
            "period":      game["period"],
            "release_date": game["release_date"],
        })

        # ── Console row (control group) ───────────────────────────────────
        # Fixed 16GB represents PS5/Xbox Series X unified memory spec.
        # This is constant across all games and all time periods by design —
        # console hardware is immune to consumer DRAM market fluctuations.
        rows.append({
            "title":       game["title"],
            "platform":    "Console",
            "pc_dummy":    0,          # Control indicator
            "post":        game["post"],
            "did":         game["post"] * 0,  # PC × Post = 0 for console
            "min_ram_gb":  CONSOLE_RAM_GB,
            "rec_ram_gb":  CONSOLE_RAM_GB,
            "year":        game["year"],
            "period":      game["period"],
            "release_date": game["release_date"],
        })

    df = pd.DataFrame(rows)
    df = df.sort_values(["title", "platform"])

    # Summary
    pc_df      = df[df["platform"] == "PC"]
    pre_pc     = pc_df[pc_df["post"] == 0]
    post_pc    = pc_df[pc_df["post"] == 1]

    log.info("Dataset built: %d total observations (%d games × 2 platforms)",
             len(df), len(games))
    log.info("PC pre-AI period:       %d games | mean min RAM: %.1f GB",
             len(pre_pc), pre_pc["min_ram_gb"].mean())
    log.info("PC AI-intensive period: %d games | mean min RAM: %.1f GB",
             len(post_pc), post_pc["min_ram_gb"].mean())
    log.info("Raw DiD signal: PC mean changed by %.1f GB pre→post",
             post_pc["min_ram_gb"].mean() - pre_pc["min_ram_gb"].mean())

    return df


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    df   = build_did_dataset(conn)
    conn.close()

    df.to_csv(OUT_PATH, index=False)
    log.info("Dataset saved to %s (%d rows)", OUT_PATH, len(df))
    print("\nFirst 10 rows:")
    print(df.head(10).to_string(index=False))
    print("\nPeriod distribution:")
    print(df.groupby(["platform", "period"])["min_ram_gb"].agg(["count", "mean"]).round(2))