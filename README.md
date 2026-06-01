# DRAM Price & AI Infrastructure Tracker

**A live Python data pipeline correlating AI infrastructure demand with consumer DRAM pricing and PC game RAM requirements.**

> Built alongside my MSc thesis: *"Hardware Cannibalization and Software Strategy: AI Infrastructure Demand, DRAM Costs, and PC Game System Requirements"* - Tilburg University, 2025–2026.

---

## The Thesis in One Chart

When NVIDIA's Data Center revenue overtook its Gaming revenue in 2022, semiconductor fabs pivoted toward High Bandwidth Memory (HBM) for AI GPUs. HBM and consumer DDR4/DDR5 compete for the **same silicon wafers** - so as AI demand surged, consumer DRAM supply tightened and prices broke their historical downward trend.

This project tracks that chain empirically:

```
NVIDIA Data Center Revenue ↑  →  HBM production priority ↑
                                →  Consumer DRAM supply ↓
                                →  DRAM prices ↑
                                →  PC game RAM requirements plateau?
```

The research question: **Do game developers suppress hardware requirements and pay down technical debt when consumer RAM becomes expensive?**

---

## What the Pipeline Does

| Data Source | What it captures | API Details |
|---|---|---|
| **FRED** (Federal Reserve) | Semiconductor Producer Price Index (PCU334413334413) - manufacturing cost proxy for DRAM | Free, key required |
| **NVIDIA IR** | NVIDIA quarterly revenue; Data Center vs Gaming segment split loaded separately via quarterly CSV | Free |
| **Steam Store API** | Minimum & recommended RAM requirements per AAA title, release dates | Free, no auth, rate limited |
| **SteamDB** | Historical technical tags for AI upscaling adoption (DLSS, FSR, XESS) | Scraped, Manual |
| **IGDB** | Cross-platform title detection; console counterparts (category=0) | Free, Twitch auth |
| **PCGamingWiki** | Historical RAM requirements (2000–2022) for pre-shock baseline trend; verified manual overrides for titles | Free, Manual |

All data is extracted, cleaned, and persisted to a local SQLite database (dram_tracker.db), which directly feeds the R econometric models.

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
├── pipeline.py                              # Main orchestration script — FRED, NVIDIA, Steam, SQLite, Plotly
├── igdb_collector.py                        # Platform detection — builds console control group
├── dlss_fsr_collector.py                    # AI upscaling integration tracker
├── games_list.py                            # Single source of truth for curated AAA game IDs
├── manual_loader.py                         # Applies manual CSV overrides to fix Steam API gaps
├── manual_overrides.csv                     # Verified RAM values from PCGamingWiki (13 titles)
├── build_its_dataset.py                     # Compiles the 72-row ITS sample
├── its_dataset_full.csv                     # OUTPUT: Full panel data for ITS model
├── build_did_dataset.py                     # Builds panel dataset for R DiD regression
├── did_dataset.csv                          # OUTPUT: Panel data for DiD model
├── nvidia_quarters.py                       # Parses NVIDIA quarterly segment revenue CSV
├── Formatted Data Revenue NVIDIA Quarterly.csv 
├── pretrend/                                # Historical Wirth's Law baseline (2000-2022)
│   ├── pretrend.py                          
│   ├── pretrend_games.csv                   
│   └── Pretrend.png                         
├── analysis/                                # R scripts and regression outputs
│   ├── its_model.R                          # Primary Interrupted Time Series estimation (R/fixest)
│   ├── did_model.R                          # Supplementary DiD structural comparison
│   ├── h2_results.txt                       # Output: Logistic regression (Upscaling Adoption)
│   └── its_results.txt                      # Output: ITS Regression tables (H1)
├── dram_tracker.db                          # SQLite database (auto-created)
├── dashboard.html                           # Latest exported Plotly dashboard (auto-generated)
├── requirements.txt                         # Python dependencies
└── requirements_r_.txt                      # R dependencies (e.g., fixest)
```

---

## Econometric Specifications & Estimation Strategy

The empirical architecture relies on two distinct specifications to map developer behavior across the Q3 2022 structural break.

### 1. Primary Model: Interrupted Time Series (ITS)
To evaluate the primary trajectory of software bloat, the pipeline estimates a segmented Ordinary Least Squares (OLS) model with heteroskedasticity-robust standard errors:

RAM_it = β_0 + β_1·Time_t + β_2·Post_t + β_3·TimeSinceBreak_t + γ·Genre_i + ε_it

*   **β_3 (Primary Coefficient):** Captures the post-shock slope change to test for the suppression of hardware requirements.
*   **Periodization:** Pre-shock baseline spans 2015–2021; the AI-intensive period spans 2023–2026. The year 2022 is explicitly excluded from primary estimation to prevent transition-year contamination around the mid-year shock.

### 2. Supplementary Model: Structural DiD Comparison
To capture platform governance dynamics, a descriptive Difference-in-Differences (DiD) framework is implemented. Because console observations are coded at a fixed 16 GB capacity dictated by static hardware cycles, this model operates as a descriptive measure of structural divergence rather than a strict causal identification check. 

Three nested specifications are estimated within the R analysis pipeline (`analysis/did_model.R`):
1.  **Specification 1 (Basic DiD):** Baseline model evaluating the interaction (`PC_dummy × Post`) with no additional covariates.
2.  **Specification 2 (Genre Fixed Effects):** Introduces categorical controls to adjust for systematic baseline differences in memory demands across game categories.
3.  **Specification 3 (Recommended RAM Covariate):** Incorporates recommended specs to control for the overall fidelity and scale of individual titles.

---

## Key Findings (Final Thesis Outcomes)

*   **Structural Break Confirmed:** A Chow test validates a statistically significant structural break in PC RAM requirements exactly at Q3 2022 (`p = 0.001`), coinciding precisely with the NVIDIA revenue segment crossover.
*   **Wirth's Law Persists (H1):** Contrary to the hypothesis that hardware demands would suppress, PC RAM requirements accelerated[cite: 3]. Mean minimum RAM jumped from 6.93 GB (pre-shock) to 11.40 GB (post-shock), representing a 64.5% increase.
*   **Algorithmic Substitution (H2):** AI upscaling adoption exploded. Games released in the AI-intensive period are **10 times more likely** to integrate DLSS or FSR than pre-shock games (`Odds Ratio = 10.0, p < 0.001`). 
*   **Macroeconomic Proxy Masking (H3):** The predicted positive correlation between AI demand and consumer DRAM prices was not supported, as the broad FRED semiconductor PPI was dominated by long-run Moore's Law cost reductions (`Spearman rho = -0.891, p = 0.0004`). However, a localized upward anomaly in the index occurred precisely around the Q3 2022 break.
*   **Substitution Mechanism (H4):** The direct test linking the price proxy to upscaling adoption was inconclusive. The sector-wide FRED PPI lacked sufficient variance (ranging only 2.6 index points) to validate the mechanism, highlighting the need for proprietary DDR4/DDR5 spot-price data in future research.
*   **Structural Divergence (DiD):** The supplementary structural comparison confirmed that PC RAM requirements grew significantly more than the insulated, hardware-static console baseline, diverging by an additional `+4.06 GB` (`p = 0.0003`) following the supply shock.

---

## Roadmap

[x] FRED DRAM price proxy pipeline
[x] NVIDIA revenue ingestion (yfinance)
[x] Steam Store API game requirements parser
[x] Manual override pipeline for Steam API gaps (13 PCGamingWiki-verified titles)
[x] IGDB integration for console counterparts (collector + schema complete)
[x] ITS & DiD dataset builders
[x] ITS & DiD regressions in R (fixest package) — completed and verified
[x] Historical pretrend chart (PCGamingWiki, 2000–2022)
[ ] Automated weekly refresh (GitHub Actions)
[ ] Power BI .pbix export integration

---

## Data Notes & Limitations

- **FRED series `PCU334413334413`** s a Producer Price Index for the entire Semiconductor Manufacturing sector — not a pure DRAM spot price. True DRAM spot prices (DRAMeXchange/TrendForce) require a paid subscription; the PPI is used as a free, academically defensible proxy.
- **Steam API** rate limits require ~1.5s between requests. The pipeline includes a polite delay. Some delisted or free-to-play titles do not return data; these are corrected via `manual_overrides.csv`.
- **yfinance** provides consolidated NVIDIA revenue. Data Center vs. Gaming segment data is sourced from manually collected quarterly IR reports and loaded via `nvidia_quarters.py`. 
- **Console RAM fixed at 16 GB** — PS5 and Xbox Series X both ship with 16 GB unified memory. This provides zero within-platform variation by design; all DiD identification comes from the PC treatment arm.
- The periodization (pre-AI: 2019–2022; AI-intensive: 2023–2026) reflects a conservative developer response lag. The underlying structural break in DRAM prices is identified at Q1 2022.
- **Pretrend analysis** uses a separate `pretrend.db` and does not modify `dram_tracker.db`.
- The periodization (pre-AI: 2015–2021; AI-intensive: 2023–2026) reflects a conservative developer response lag, with 2022 explicitly excluded from the primary ITS estimation to prevent transition-year contamination around the mid-year shock.

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

