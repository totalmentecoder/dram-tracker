"""
IGDB Collector
==============
Queries the IGDB API to find console counterparts for each Steam game,
building the control group for the Difference-in-Differences model.

For each game in the Steam list, this script:
1. Searches IGDB by name to find the canonical game entry
2. Checks which platforms it released on (PS5, Xbox Series X)
3. Stores platform availability and release dates in SQLite

This data answers: is this game cross-platform? If yes, it qualifies
for the DiD model as a treatment (PC) / control (console) pair.

Auth: Twitch OAuth2 client credentials flow.
Docs: https://api-docs.igdb.com/
"""

import os
import time
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

DB_PATH = Path("dram_tracker.db")

# IGDB platform IDs for current-gen consoles
PLATFORM_IDS = {
    "PS5":        167,
    "Xbox_Series": 169,
    "PC":         6,
    "PS4":        48,
    "Xbox_One":   49,
}

# Same logic as pipeline.py
from games_list import STEAM_GAMES

# ── Auth ─────────────────────────────────────────────────────────────────────

def get_twitch_token() -> str:
    """
    Obtain a Twitch OAuth2 access token using client credentials flow.
    Token is valid for ~60 days; this fetches a fresh one each run.
    """
    client_id     = os.getenv("TWITCH_CLIENT_ID")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise EnvironmentError(
            "TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET must be set in .env"
        )

    resp = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id":     client_id,
            "client_secret": client_secret,
            "grant_type":    "client_credentials",
        },
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    log.info("Twitch token obtained.")
    return token


# ── Database ──────────────────────────────────────────────────────────────────

def init_igdb_tables(conn: sqlite3.Connection) -> None:
    """Add IGDB-specific tables to the existing database."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS igdb_games (
            igdb_id         INTEGER PRIMARY KEY,
            title           TEXT NOT NULL,
            steam_app_id    INTEGER,
            igdb_release    TEXT,
            on_ps5          INTEGER DEFAULT 0,
            on_xbox_series  INTEGER DEFAULT 0,
            on_pc           INTEGER DEFAULT 0,
            on_ps4          INTEGER DEFAULT 0,
            on_xbox_one     INTEGER DEFAULT 0,
            is_cross_platform INTEGER DEFAULT 0,
            fetched_at      TEXT NOT NULL
        );
    """)
    conn.commit()
    log.info("IGDB tables ready.")


# ── IGDB Query ────────────────────────────────────────────────────────────────

def search_igdb_game(
    title: str,
    steam_app_id: int,
    token: str,
    client_id: str,
    delay: float = 0.5,
) :
    """
    Search IGDB for a game by title and return platform availability.
    Uses a fuzzy name search and picks the best match.
    """
    headers = {
        "Client-ID":     client_id,
        "Authorization": f"Bearer {token}",
    }

    # Query: search by name, return id, name, platforms, first_release_date
    body = (
        f'search "{title}"; '
        f'fields id, name, platforms, first_release_date; '
        f'limit 5;'
    )

    try:
        resp = requests.post(
            "https://api.igdb.com/v4/games",
            headers=headers,
            data=body,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()

        if not results:
            log.warning("No IGDB results for: %s", title)
            return None

        # Pick first result (best match by IGDB relevance)
        game = results[0]
        platforms = game.get("platforms", [])

        release_ts = game.get("first_release_date")
        release_dt = (
            datetime.utcfromtimestamp(release_ts).strftime("%Y-%m-%d")
            if release_ts else None
        )

        result = {
            "igdb_id":        game["id"],
            "title":          title,
            "steam_app_id":   steam_app_id,
            "igdb_release":   release_dt,
            "on_ps5":         int(PLATFORM_IDS["PS5"] in platforms),
            "on_xbox_series": int(PLATFORM_IDS["Xbox_Series"] in platforms),
            "on_pc":          int(PLATFORM_IDS["PC"] in platforms),
            "on_ps4":         int(PLATFORM_IDS["PS4"] in platforms),
            "on_xbox_one":    int(PLATFORM_IDS["Xbox_One"] in platforms),
            "fetched_at":     datetime.utcnow().isoformat(),
        }

        # Cross-platform = available on PC AND at least one console
        result["is_cross_platform"] = int(
            result["on_pc"] == 1 and
            (result["on_ps5"] == 1 or result["on_xbox_series"] == 1)
        )

        log.info(
            "%s → IGDB ID %d | PS5:%d XSX:%d PC:%d | Cross-platform:%d",
            title, result["igdb_id"],
            result["on_ps5"], result["on_xbox_series"], result["on_pc"],
            result["is_cross_platform"],
        )

        return result

    except requests.RequestException as exc:
        log.warning("IGDB request failed for %s: %s", title, exc)
        return None
    finally:
        time.sleep(delay)


# ── Main ──────────────────────────────────────────────────────────────────────

def run_igdb_collection(conn: sqlite3.Connection) -> None:
    """Collect IGDB platform data for all games and store in SQLite."""
    init_igdb_tables(conn)

    token     = get_twitch_token()
    client_id = os.getenv("TWITCH_CLIENT_ID")
    rows      = []

    for title, app_id in STEAM_GAMES.items():
        result = search_igdb_game(title, app_id, token, client_id)
        if result:
            rows.append(result)

    if not rows:
        log.warning("No IGDB data collected.")
        return

    cur = conn.cursor()
    cur.executemany(
        """INSERT OR REPLACE INTO igdb_games
           (igdb_id, title, steam_app_id, igdb_release,
            on_ps5, on_xbox_series, on_pc, on_ps4, on_xbox_one,
            is_cross_platform, fetched_at)
           VALUES
           (:igdb_id, :title, :steam_app_id, :igdb_release,
            :on_ps5, :on_xbox_series, :on_pc, :on_ps4, :on_xbox_one,
            :is_cross_platform, :fetched_at)""",
        rows,
    )
    conn.commit()

    cross = sum(r["is_cross_platform"] for r in rows)
    log.info(
        "Stored %d games. %d qualify as cross-platform (DiD sample).",
        len(rows), cross,
    )

    # Print the DiD-eligible sample
    print("\n── DiD-eligible cross-platform titles ──")
    for r in rows:
        if r["is_cross_platform"]:
            print(f"  ✓ {r['title']} (IGDB {r['igdb_id']}, released {r['igdb_release']})")

    print("\n── Excluded (PC only or no current-gen console) ──")
    for r in rows:
        if not r["is_cross_platform"]:
            print(f"  ✗ {r['title']}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    run_igdb_collection(conn)
    conn.close()