"""
games_list.py
=============
Single source of truth for all game titles used across pipeline.py
and igdb_collector.py. Import from here to keep both files in sync.

Each entry: "Title": steam_app_id
Steam App IDs verified manually via store.steampowered.com
"""

# Format: "Title": (steam_app_id, genre)
STEAM_GAMES = {
    # ── 2015 ──────────────────────────────────────────────────────────────────
    "The Witcher 3":                   (292030,  "Action-RPG"),
    "Batman Arkham Knight":            (208650,  "Action-Adventure"),
    "Metal Gear Solid V":              (287700,  "Action-Adventure"),
    "Fallout 4":                       (377160,  "Action-RPG"),
    "FIFA 16":                         (1325910, "Sports"),
    "NBA 2K16":                        (329010,  "Sports"),
    "F1 2015":                         (286570,  "Sports"),
    "Assassin's Creed Syndicate":      (368500,  "Action-Adventure"),
    "Call of Duty Black Ops III":      (311210,  "FPS"),
    "Just Cause 3":                    (225540,  "Action-Adventure"),
    "Rainbow Six Siege":               (359550,  "FPS"),

    # ── 2016 ──────────────────────────────────────────────────────────────────
    "Battlefield 1":                   (1238820, "FPS"),
    "Deus Ex Mankind Divided":         (337000,  "Action-RPG"),
    "FIFA 17":                         (1343400, "Sports"),
    "NBA 2K17":                        (385760,  "Sports"),
    "F1 2016":                         (391040,  "Sports"),
    "Call of Duty Infinite Warfare":   (292730,  "FPS"),
    "Dishonored 2":                    (403640,  "Action-Adventure"),
    "Watch Dogs 2":                    (447040,  "Action-Adventure"),
    "Mafia III":                       (360430,  "Action-Adventure"),

    # ── 2017 ──────────────────────────────────────────────────────────────────
    "Assassin's Creed Origins":        (582160,  "Action-Adventure"),
    "Middle Earth Shadow of War":      (356190,  "Action-RPG"),
    "FIFA 18":                         (1237980, "Sports"),
    "NBA 2K18":                        (560820,  "Sports"),
    "F1 2017":                         (515220,  "Sports"),
    "Call of Duty WWII":               (476600,  "FPS"),
    "Wolfenstein II":                  (612880,  "FPS"),
    "Need for Speed Payback":          (621490,  "Sports"),

    # ── 2018 ──────────────────────────────────────────────────────────────────
    "Assassin's Creed Odyssey":        (812140,  "Action-Adventure"),
    "Far Cry 5":                       (552520,  "FPS"),
    "FIFA 19":                         (1238840, "Sports"),
    "NBA 2K19":                        (652670,  "Sports"),
    "F1 2018":                         (737800,  "Sports"),
    "Shadow of the Tomb Raider":       (750920,  "Action-Adventure"),
    "Monster Hunter World":            (582010,  "Action-RPG"),
    "Battlefield V":                   (1260630, "FPS"),

    # ── 2019 ──────────────────────────────────────────────────────────────────
    "Red Dead Redemption 2":           (1174180, "Action-Adventure"),
    "Death Stranding":                 (1190460, "Action-Adventure"),
    "Control":                         (870780,  "Action-Adventure"),
    "Assetto Corsa Competizione":      (805550,  "Sports"),

    # ── 2020 ──────────────────────────────────────────────────────────────────
    "Resident Evil 3":                 (952060,  "Action-Adventure"),
    "Assassin's Creed Valhalla":       (2208920, "Action-Adventure"),
    "Watch Dogs Legion":               (2089820, "Action-Adventure"),
    "FIFA 21":                         (1238820, "Sports"),
    "NBA 2K21":                        (1320010, "Sports"),
    "F1 2020":                         (1080110, "Sports"),
    "Mafia Definitive Edition":        (1030840, "Action-Adventure"),

    # ── 2021 ──────────────────────────────────────────────────────────────────
    "Resident Evil Village":           (1196590, "Action-Adventure"),
    "Far Cry 6":                       (1681320, "FPS"),
    "FIFA 22":                         (1811700, "Sports"),
    "NBA 2K22":                        (1488740, "Sports"),
    "F1 2021":                         (1134570, "Sports"),
    "Forza Horizon 5":                 (1551360, "Sports"),
    "Halo Infinite":                   (1240440, "FPS"),
    "Battlefield 2042":                (1517290, "FPS"),
    "Call of Duty Vanguard":           (1085660, "FPS"),

    # ── 2022 ──────────────────────────────────────────────────────────────────
    "Dying Light 2":                   (534380,  "Action-Adventure"),
    "Elden Ring":                      (1245620, "Action-RPG"),
    "A Plague Tale Requiem":           (1952490, "Action-Adventure"),
    "FIFA 23":                         (1811710, "Sports"),
    "NBA 2K23":                        (2273450, "Sports"),
    "F1 22":                           (1692250, "Sports"),
    "Uncharted Legacy of Thieves":     (1659420, "Action-Adventure"),
    "FF7 Remake Intergrade":           (1462040, "Action-RPG"),
    "God of War":                      (1593500, "Action-Adventure"),
    "Marvel's Spider-Man Remastered":  (1817070, "Action-Adventure"),

    # ── 2023 ──────────────────────────────────────────────────────────────────
    "Hogwarts Legacy":                 (990080,  "Action-RPG"),
    "Resident Evil 4 Remake":          (2050650, "Action-Adventure"),
    "Assassin's Creed Mirage":         (2620590, "Action-Adventure"),
    "Alan Wake 2":                     (1850050, "Action-Adventure"),
    "Baldur's Gate 3":                 (1086940, "Action-RPG"),
    "Cyberpunk 2077":                  (1091500, "Action-RPG"),
    "FIFA 24":                         (2195250, "Sports"),
    "NBA 2K24":                        (2338770, "Sports"),
    "F1 23":                           (2108330, "Sports"),
    "Call of Duty MW3 2023":           (2519060, "FPS"),

    # ── 2024 ──────────────────────────────────────────────────────────────────
    "Star Wars Outlaws":               (2803270, "Action-Adventure"),
    "Black Myth: Wukong":              (2358720, "Action-RPG"),
    "EA FC 25":                        (2731540, "Sports"),
    "NBA 2K25":                        (2767030, "Sports"),
    "F1 24":                           (2488060, "Sports"),

    # ── 2025 ──────────────────────────────────────────────────────────────────
    "Marvel's Spider-Man 2":           (2119490, "Action-Adventure"),
    "Assassin's Creed Shadows":        (2933620, "Action-Adventure"),
    "Monster Hunter Wilds":            (2246340, "Action-RPG"),
    "FF7 Rebirth":                     (2909400, "Action-RPG"),
    "The Last of Us Part I":           (1888930, "Action-Adventure"),
}