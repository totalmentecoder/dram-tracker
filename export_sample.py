import sqlite3
import pandas as pd

conn = sqlite3.connect('dram_tracker.db')

df = pd.read_sql("""
    SELECT 
        g.title,
        g.release_date,
        g.genre,
        g.min_ram_gb,
        g.rec_ram_gb,
        g.app_id as steam_app_id,
        COALESCE(u.has_upscaling, 0) as has_upscaling,
        COALESCE(u.has_dlss, 0) as has_dlss,
        COALESCE(u.has_fsr, 0) as has_fsr,
        COALESCE(u.has_xess, 0) as has_xess
    FROM game_requirements g
    LEFT JOIN upscaling_support u ON g.app_id = u.app_id
    WHERE g.min_ram_gb IS NOT NULL
    ORDER BY g.release_date
""", conn)

conn.close()
df.to_csv('sample_table.csv', index=False)
print(f"Exported {len(df)} games to sample_table.csv")