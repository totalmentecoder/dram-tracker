"""
DiD Dataset Builder
====================
Builds the panel dataset for the Difference-in-Differences robustness check.
Goes in Appendix A of the thesis.

For each game, creates two rows:
- PC row (treatment): actual Steam RAM requirement
- Console row (control): fixed 16GB (PS5/Xbox Series X hardware spec)

RAM_it = α + β1·PC + β2·Post + β3·(PC×Post) + γ·Genre + ε
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
OUT_PATH = Path("did_dataset.csv")

CONSOLE_RAM_GB = 16.0
AI_SHOCK_YEAR  = 2023
BASE_YEAR      = 2015


def parse_release_year(date_str: str):
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


def build_did_dataset(conn):
    games = pd.read_sql(
        """SELECT title, genre, min_ram_gb, rec_ram_gb, release_date
           FROM game_requirements
           WHERE min_ram_gb IS NOT NULL""",
        conn,
    )

    log.info("Loaded %d games.", len(games))

    games["year"] = games["release_date"].apply(parse_release_year)
    games = games.dropna(subset=["year"])
    games["year"] = games["year"].astype(int)
    games = games[(games["year"] >= BASE_YEAR) & (games["year"] <= 2026)]
    games = games[games["year"] != 2022]

    games["post"]   = (games["year"] >= AI_SHOCK_YEAR).astype(int)
    games["period"] = games["post"].map({0: "pre_ai", 1: "ai_intensive"})

    rows = []
    for _, game in games.iterrows():
        rows.append({
            "title":      game["title"],
            "genre":      game["genre"],
            "platform":   "PC",
            "pc_dummy":   1,
            "post":       game["post"],
            "did":        game["post"] * 1,
            "min_ram_gb": game["min_ram_gb"],
            "rec_ram_gb": game["rec_ram_gb"],
            "year":       game["year"],
            "period":     game["period"],
        })
        rows.append({
            "title":      game["title"],
            "genre":      game["genre"],
            "platform":   "Console",
            "pc_dummy":   0,
            "post":       game["post"],
            "did":        0,
            "min_ram_gb": CONSOLE_RAM_GB,
            "rec_ram_gb": CONSOLE_RAM_GB,
            "year":       game["year"],
            "period":     game["period"],
        })

    df = pd.DataFrame(rows).sort_values(["title", "platform"])

    pc = df[df["platform"] == "PC"]
    log.info("Dataset: %d observations (%d games x 2 platforms)", len(df), len(games))
    log.info("PC pre-AI:  %d games | mean: %.2f GB", len(pc[pc["post"]==0]), pc[pc["post"]==0]["min_ram_gb"].mean())
    log.info("PC post-AI: %d games | mean: %.2f GB", len(pc[pc["post"]==1]), pc[pc["post"]==1]["min_ram_gb"].mean())

    return df


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    df   = build_did_dataset(conn)
    conn.close()
    df.to_csv(OUT_PATH, index=False)
    log.info("Saved to %s", OUT_PATH)
    print(df.head(10).to_string(index=False))
