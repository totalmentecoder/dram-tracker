"""
games_list.py
=============
Single source of truth for all game titles used across pipeline.py
and igdb_collector.py. Import from here to keep both files in sync.

Each entry: "Title": steam_app_id
Steam App IDs verified manually via store.steampowered.com
"""

STEAM_GAMES = {
    # ── Pre-AI period (2019–2022) ─────────────────────────────────────────
    "Red Dead Redemption 2":          1174180,
    "Death Stranding":                1190460,
    "Control":                        870780,
    "Resident Evil 3":                952060,
    "Assassin's Creed Valhalla":      2208920,
    "Watch Dogs Legion":              2089820,
    "FIFA 21":                        1238820,
    "NBA 2K21":                       1320010,
    "F1 2020":                        1080110,
    "Resident Evil Village":          1196590,
    "Far Cry 6":                      1681320,
    "FIFA 22":                        1811700,
    "NBA 2K22":                       1488740,
    "F1 2021":                        1134570,
    "Forza Horizon 5":                1551360,
    "Halo Infinite":                  1240440,
    "Uncharted Legacy of Thieves":    1659420,
    "Mafia Definitive Edition":       1030840,
    "Dying Light 2":                  534380,
    "Elden Ring":                     1245620,
    "A Plague Tale Requiem":          1952490,
    "FIFA 23":                        1811710,
    "NBA 2K23":                       2273450,
    "F1 22":                          1692250,
    "Assetto Corsa Competizione":     805550,
    "Call of Duty Vanguard":          1085660,
    "Battlefield 2042":               1517290,
    "Marvel's Spider-Man Remastered": 1817070,
    "FF7 Remake Intergrade":          1462040,

    # ── AI-intensive period (2023–2026) ───────────────────────────────────
    "Hogwarts Legacy":                990080,
    "Resident Evil 4 Remake":         2050650,
    "Assassin's Creed Mirage":        2620590,
    "Alan Wake 2":                    1850050,
    "Baldur's Gate 3":                1086940,
    "Cyberpunk 2077":                 1091500,
    "FIFA 24":                        2195250,
    "NBA 2K24":                       2338770,
    "F1 23":                          2108330,
    "Call of Duty MW3 2023":          2519060,
    "Star Wars Outlaws":              2803270,
    "Black Myth: Wukong":             2358720,
    "EA FC 25":                       2731540,
    "NBA 2K25":                       2767030,
    "F1 24":                          2488060,
    "Marvel's Spider-Man 2":          2119490,
    "Assassin's Creed Shadows":       2933620,
    "Monster Hunter Wilds":           2246340,
    "FF7 Rebirth":                    2909400,
}