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
| **yfinance / NVIDIA IR** | NVIDIA quarterly revenue, Data Center vs Gaming segment split | Free |
| **Steam Store API** | Minimum & recommended RAM requirements per AAA title, release dates | Free, no auth |
| **IGDB** *(Week 4+)* | Cross-platform titles, console counterparts for DiD control group | Free, Twitch auth |

All data is persisted to a local **SQLite** database and visualised in an interactive **Plotly** dashboard.

---

## Quickstart

```bash
# 1. Clone and install dependencies
git clone https://github.com/yourusername/dram-tracker.git
cd dram-tracker
pip install -r requirements.txt

# 2. Add your FRED API key (free at https://fred.stlouisfed.org/docs/api/api_key.html)
echo "FRED_API_KEY=your_key_here" > .env

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
├── pipeline.py          # Main pipeline — data fetch, SQLite, Plotly dashboard
├── igdb_collector.py    # IGDB integration (Week 4) — cross-platform titles
├── analysis/
│   ├── did_model.R      # Difference-in-Differences econometric model (R/fixest)
│   └── explore.ipynb    # Exploratory data analysis notebook
├── data/
│   └── dram_tracker.db  # SQLite database (auto-created, gitignored)
├── dashboard.html       # Latest exported dashboard (auto-generated)
├── requirements.txt
└── .env.example
```

---

## Econometric Design (Thesis)

The pipeline feeds a **Difference-in-Differences (DiD)** model comparing PC games (treatment — exposed to DRAM price volatility) against their console counterparts (control — fixed hardware specs).

```
RAMᵢₜ = α + β₁·PC_dummy + β₂·AI_period + β₃·(PC × AI_period) + γ·Xᵢₜ + εᵢₜ
```

Where `β₃` is the DiD coefficient: the differential change in PC RAM requirements *caused by* the AI-driven supply shock, controlling for genre, engine, and release year.

**Identification assumption:** in the absence of the shock, PC and console RAM requirements would have followed parallel trends.

---

## Key Findings (Preliminary)

> *Updated as data collection progresses.*

- The Semiconductor PPI inflects upward in **Q3 2022**, coinciding with NVIDIA's first quarter where Data Center revenue exceeded Gaming revenue.
- Minimum PC RAM requirements for AAA titles **[finding TBC after full data collection]**.
- AI upscaling adoption (DLSS/FSR tags in SteamDB) **[finding TBC]**.

---

## Roadmap

- [x] FRED DRAM price proxy pipeline
- [x] NVIDIA revenue ingestion (yfinance)
- [x] Steam Store API game requirements parser
- [ ] IGDB integration for console counterparts
- [ ] NVIDIA segment revenue (EDGAR 10-Q parser)
- [ ] DiD regression in R (`fixest` package)
- [ ] Automated weekly refresh (GitHub Actions)
- [ ] Power BI `.pbix` export

---

## Data Notes & Limitations

- **FRED series `PCU334413334413`** is a Producer Price Index for the entire Semiconductor Manufacturing sector — not a pure DRAM spot price. True DRAM spot prices (DRAMeXchange/TrendForce) require a paid subscription; the PPI is used as a free, academically defensible proxy.
- **Steam API** rate limits require ~1.5s between requests. The pipeline includes a polite delay.
- **yfinance** provides consolidated revenue; Data Center vs. Gaming segment data must be sourced from NVIDIA's quarterly IR reports.
- The periodization (pre-AI: 2019–2022; AI-intensive: 2023–2026) is confirmed via structural break analysis on the DRAM price series.

---

## Tech Stack

`Python 3.11` · `SQLite` · `pandas` · `yfinance` · `fredapi` · `Plotly` · `requests`

Analysis: `R` (`fixest`, `ggplot2`)  
Data: `FRED API` · `Steam Store API` · `IGDB API` · `yfinance`

---

## Author

**Salvatore Caldara** — MSc Information Management, Tilburg University  
Relocating to Zürich, Summer 2026  
[LinkedIn](https://linkedin.com/in/salvatorecaldara) · [s.caldara@tilburguniversity.edu](mailto:s.caldara@tilburguniversity.edu)

---

*This repository is the empirical infrastructure layer of ongoing academic research. Data, findings, and code will be updated as the thesis progresses.*
