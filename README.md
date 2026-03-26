# DRAM Price & AI Infrastructure Tracker

**A live Python data pipeline correlating AI infrastructure demand with consumer DRAM pricing and PC game RAM requirements.**

> Built alongside my MSc thesis: *"Hardware Cannibalization and Software Strategy: AI Infrastructure Demand, DRAM Costs, and PC Game System Requirements"* — Tilburg University, 2025–2026.

---

## The Thesis in One Chart

When NVIDIA's Data Center revenue overtook its Gaming revenue in 2022, semiconductor fabs pivoted toward High Bandwidth Memory (HBM) for AI GPUs. HBM and consumer DDR4/DDR5 compete for the **same silicon wafers** — so as AI demand surged, consumer DRAM supply tightened and prices broke their historical downward trend.

This project tracks that chain empirically:

```
NVIDIA Data Center Revenue ↑  →  HBM production priority ↑
                                →  Consumer DRAM supply ↓
                                →  DRAM prices ↑
                                →  PC game RAM requirements plateau?
```

The research question: **do game developers suppress hardware requirements when consumer RAM becomes expensive?**

---

## What the Pipeline Does

| Data Source | What it captures | API |
|---|---|---|
| **FRED** (Federal Reserve) | Semiconductor Producer Price Index — manufacturing cost proxy for DRAM | Free, key required |
| **yfinance / NVIDIA IR** | NVIDIA quarterly revenue; Data Center vs Gaming segment split loaded separately via quarterly CSV | Free |
| **Steam Store API** | Minimum & recommended RAM requirements per AAA title, release dates | Free, no auth |
| **IGDB** | Cross-platform title detection; console counterparts for DiD control group | Free, Twitch auth |
| **PCGamingWiki** | Historical RAM requirements (2000–2022) for pre-shock baseline trend | Free, no auth |

All data is persisted to a local **SQLite** database and visualised in an interactive **Plotly** dashboard.

---

## Quickstart

```bash
# 1. Clone and install dependencies
git clone https://github.com/yourusername/dram-tracker.git
cd dram-tracker
pip install -r requirements.txt

# 2. Add your API keys (FRED free at https://fred.stlouisfed.org/docs/api/api_key.html)
#    Twitch credentials for IGDB at https://dev.twitch.tv/console
echo "FRED_API_KEY=your_key_here" > .env
echo "TWITCH_CLIENT_ID=your_id_here" >> .env
echo "TWITCH_CLIENT_SECRET=your_secret_here" >> .env

# 3. Run the pipeline
python pipeline.py
# → Opens interactive dashboard and saves dashboard.html
```

To skip re-fetching and just rebuild the dashboard from cached data:
```python
from pipeline import init_db, build_dashboard
conn = init_db()
build_dashboard(conn).show()
```

---

## Project Structure

```
dram-tracker/
├── pipeline.py                              # Main pipeline — FRED, NVIDIA, Steam, SQLite, Plotly dashboard
├── igdb_collector.py                        # IGDB platform detection — builds console control group
├── games_list.py                            # Single source of truth for all 43 curated AAA game IDs
├── manual_loader.py                         # Applies manual CSV overrides to fix Steam API gaps
├── manual_overrides.csv                     # Verified RAM values from PCGamingWiki (~13 titles)
├── build_did_dataset.py                     # Builds panel dataset for R regression (42 games × 2 platforms)
├── did_dataset.csv                          # OUTPUT: 84-row panel data for DiD model
├── nvidia_quarters.py                       # Parses NVIDIA quarterly segment revenue CSV
├── Formatted Data Revenue NVIDIA Quarterly.csv  # Manual NVIDIA DC vs Gaming breakdown
├── pretrend/
│   ├── pretrend.py                          # PCGamingWiki scraper — historical RAM trend 2000–2022
│   ├── pretrend_games.csv                   # 58 landmark titles (GTA, CoD, FIFA, etc.)
│   └── pretrend_chart.html                  # OUTPUT: Historical RAM chart (separate DB)
├── analysis/
│   ├── did_model.R                          # Difference-in-Differences econometric model (R/fixest)
│   ├── did_plot.png                         # OUTPUT: Mean RAM trajectories by platform & period
│   └── did_results.txt                      # OUTPUT: Regression table
├── dram_tracker.db                          # SQLite database (auto-created)
├── dashboard.html                           # Latest exported Plotly dashboard (auto-generated)
├── requirements.txt
└── .env.example
```

---

## Econometric Design (Thesis)

The pipeline feeds a **Difference-in-Differences (DiD)** model comparing PC games (treatment — exposed to DRAM price volatility) against their console counterparts (control — fixed hardware specs).

```
RAMᵢₜ = α + β₁·PC_dummy + β₂·Post + β₃·(PC × Post) + γ·Xᵢₜ + εᵢₜ
```

Where `β₃` is the DiD coefficient: the differential change in PC RAM requirements *caused by* the AI-driven supply shock, controlling for genre, engine, and release year.

**Identification assumption:** in the absence of the shock, PC and console RAM requirements would have followed parallel trends.

**Control arm:** Console observations are fixed at **16 GB** (the unified memory spec of PS5 and Xbox Series X), providing a hardware-invariant baseline.

**Period cutoff:** The AI shock structural break is identified at Q1 2022 (first quarter NVIDIA Data Center revenue exceeded Gaming). The DiD dataset uses 2023 as the treatment onset to account for developer response lag.

Three nested specifications are estimated:
1. **Basic DiD** — no controls
2. **Year fixed effects**
3. **Year FE + recommended RAM covariate**

Parallel trends are verified via a pre-period interaction test (`PC_dummy × Year`).

---

## Key Findings (Preliminary)

> *Updated as data collection and analysis progress.*

- The Semiconductor PPI inflects upward in **Q3 2022**, coinciding with NVIDIA's first quarter where Data Center revenue exceeded Gaming revenue.
- Raw (unadjusted) DiD signal: minimum PC RAM requirements increased by approximately **+1.1 GB** in the AI-intensive period relative to the console trend — contrary to the flattening hypothesis. Regression controls (year fixed effects, recommended RAM) may shift this estimate.
- Full β₃ estimate with standard errors pending final regression run.
- AI upscaling adoption (DLSS/FSR) **[finding TBC]**.

---

## Roadmap

- [x] FRED DRAM price proxy pipeline
- [x] NVIDIA revenue ingestion (yfinance)
- [x] Steam Store API game requirements parser
- [x] Manual override pipeline for Steam API gaps (PCGamingWiki-verified)
- [x] IGDB integration for console counterparts (collector + schema complete)
- [x] DiD dataset builder (84-row panel, 42 games × 2 platforms)
- [x] DiD regression in R (`fixest` package) — model running
- [x] Historical pretrend chart (PCGamingWiki, 2000–2022)
- [ ] NVIDIA segment revenue fully integrated into dashboard (CSV parsed; not yet wired to Plotly panels)
- [ ] IGDB cross-platform filter applied to DiD sample (collector done; sample restriction pending)
- [ ] Automated weekly refresh (GitHub Actions)
- [ ] Power BI `.pbix` export

---

## Data Notes & Limitations

- **FRED series `PCU334413334413`** is a Producer Price Index for the entire Semiconductor Manufacturing sector — not a pure DRAM spot price. True DRAM spot prices (DRAMeXchange/TrendForce) require a paid subscription; the PPI is used as a free, academically defensible proxy.
- **Steam API** rate limits require ~1.5s between requests. The pipeline includes a polite delay. Some delisted or free-to-play titles do not return data; these are corrected via `manual_overrides.csv`.
- **yfinance** provides consolidated NVIDIA revenue. Data Center vs. Gaming segment data is sourced from manually collected quarterly IR reports and loaded via `nvidia_quarters.py`. The dashboard currently plots total revenue; segment panels are a pending enhancement.
- **Console RAM fixed at 16 GB** — PS5 and Xbox Series X both ship with 16 GB unified memory. This provides zero within-platform variation by design; all DiD identification comes from the PC treatment arm.
- The periodization (pre-AI: 2019–2022; AI-intensive: 2023–2026) reflects a conservative developer response lag. The underlying structural break in DRAM prices is identified at Q1 2022.
- **Pretrend analysis** uses a separate `pretrend.db` and does not modify `dram_tracker.db`.

---

## Tech Stack

`Python 3.11` · `SQLite` · `pandas` · `yfinance` · `fredapi` · `Plotly` · `requests` · `python-dotenv`

Analysis: `R` (`fixest`, `tidyverse`, `ggplot2`, `modelsummary`)
Data: `FRED API` · `Steam Store API` · `IGDB API` · `yfinance` · `PCGamingWiki`

---

## Author

**Salvatore Caldara** — MSc Information Management, Tilburg University
Relocating to Zürich, Summer 2026
[LinkedIn](https://linkedin.com/in/salvatorecaldara) · [s.caldara@tilburguniversity.edu](mailto:s.caldara@tilburguniversity.edu)

---

*This repository is the empirical infrastructure layer of ongoing academic research. Data, findings, and code will be updated as the thesis progresses.*
