# ============================================================================
# Interrupted Time Series (ITS) Analysis
# Hardware Cannibalization and Software Strategy
# Author: Salvatore Caldara, Tilburg University 2025-2026
# ============================================================================
#
# Primary test: H1
# RAM_it = β0 + β1·Time + β2·Post + β3·TimeSinceBreak + γ·Genre + ε
#
# β1 = pre-shock slope (historical RAM growth rate)
# β2 = level change at break point
# β3 = post-shock slope change (PRIMARY FINDING)
#   β3 < 0 → growth rate slowed → flattening hypothesis supported
#   β3 > 0 → growth rate accelerated
#   β3 = 0 → no change detected
# ============================================================================

library(fixest)
library(tidyverse)
library(modelsummary)
install.packages(c("DBI", "RSQLite"))

setwd("C:/Users/Salvatore Caldara/Desktop/dram-tracker")

# ── 1. Load Data ──────────────────────────────────────────────────────────────
df <- read_csv("its_dataset.csv")

cat("=== Dataset Overview ===\n")
cat("Total observations:", nrow(df), "\n")
cat("Pre-shock  (2015-2021):", sum(df$post == 0), "\n")
cat("Post-shock (2023-2026):", sum(df$post == 1), "\n")
cat("Genres:", paste(unique(df$genre), collapse=", "), "\n\n")


# ── 2. Descriptive Statistics ─────────────────────────────────────────────────
cat("=== Mean Min RAM by Year ===\n")
year_means <- df %>%
  group_by(year) %>%
  summarise(
    n        = n(),
    mean_ram = round(mean(min_ram_gb), 2),
    sd_ram   = round(sd(min_ram_gb), 2),
    .groups  = "drop"
  )
print(year_means)

cat("\n=== Mean Min RAM by Genre and Period ===\n")
genre_table <- df %>%
  group_by(genre, period) %>%
  summarise(
    n        = n(),
    mean_ram = round(mean(min_ram_gb), 2),
    sd_ram   = round(sd(min_ram_gb), 2),
    .groups  = "drop"
  )
print(genre_table)


# ── 3. Pre-Trend Visualisation ────────────────────────────────────────────────
annual_mean <- df %>%
  group_by(year, period) %>%
  summarise(mean_ram = mean(min_ram_gb), .groups = "drop")

ggplot(annual_mean, aes(x = year, y = mean_ram)) +
  geom_point(aes(color = period), size = 4) +
  geom_line(color = "gray60", linewidth = 1) +
  geom_vline(xintercept = 2022.75, linetype = "dashed",
             color = "red", linewidth = 0.8) +
  annotate("text", x = 2023.1, y = max(annual_mean$mean_ram) * 0.9,
           label = "AI Supply Shock\nQ3 2022", color = "red",
           hjust = 0, size = 3.5) +
  scale_color_manual(values = c("pre_ai" = "#00b4d8",
                                "ai_intensive" = "#f4a261")) +
  labs(
    title    = "Mean Minimum PC RAM Requirements by Year (2015-2026)",
    subtitle = "2022 excluded as transition year | ITS break point at Q3 2022",
    x        = "Year",
    y        = "Mean Minimum RAM (GB)",
    color    = "Period",
    caption  = "Source: Steam Store API, PCGamingWiki. Author's own compilation."
  ) +
  theme_minimal(base_size = 13) +
  theme(plot.title = element_text(face = "bold"))

ggsave("analysis/its_pretrend_plot.png", width = 9, height = 5, dpi = 300)
cat("\nPre-trend plot saved.\n")


# ── 4. Chow Test (Structural Break Validation) ────────────────────────────────
# Tests whether a statistically significant structural break exists at Q3 2022.
# If significant, confirms the theoretical break date is empirically supported.
cat("\n=== Chow Test: Structural Break at 2022 ===\n")

df_chow <- df %>% mutate(break_dummy = as.integer(year >= 2023))

m_restricted   <- lm(min_ram_gb ~ time_index, data = df_chow)
m_unrestricted <- lm(min_ram_gb ~ time_index * break_dummy, data = df_chow)

anova_result <- anova(m_restricted, m_unrestricted)
print(anova_result)

cat("\nInterpretation: If p < 0.05, a significant structural break exists at Q3 2022.\n")


# ── 5. Main ITS Regression ────────────────────────────────────────────────────
# Model 1: Basic ITS — no controls
m1 <- feols(min_ram_gb ~ time_index + post + time_since_break,
            data = df, vcov = "HC1")

# Model 2: ITS with genre fixed effects
m2 <- feols(min_ram_gb ~ time_index + post + time_since_break | genre,
            data = df, vcov = "HC1")

# Model 3: ITS with genre FE + recommended RAM as scope control
m3 <- feols(min_ram_gb ~ time_index + post + time_since_break + rec_ram_gb | genre,
            data = df, vcov = "HC1")

cat("\n=== ITS Regression Results ===\n")
cat("KEY: β3 (time_since_break) is your primary finding for H1\n\n")

summary(m1)
summary(m2)
summary(m3)


# ── 6. Genre Subsample Analysis ───────────────────────────────────────────────
cat("\n=== Genre Subsample Analysis ===\n")

# Sports titles (consistently lower RAM — less affected by shock)
df_sports <- df %>% filter(genre == "Sports")
m_sports  <- feols(min_ram_gb ~ time_index + post + time_since_break,
                   data = df_sports, vcov = "HC1")

# Graphically intensive titles (most affected by shock)
df_intensive <- df %>% filter(genre %in% c("Action-RPG", "Action-Adventure"))
m_intensive  <- feols(min_ram_gb ~ time_index + post + time_since_break,
                      data = df_intensive, vcov = "HC1")

cat("Sports titles:\n")
summary(m_sports)

cat("\nGraphically intensive titles (Action-RPG + Action-Adventure):\n")
summary(m_intensive)


# ── 7. Sensitivity Check — Including 2022 ────────────────────────────────────
cat("\n=== Sensitivity Check: Including 2022 ===\n")

df_full <- read_csv("its_dataset.csv")
# Re-read without the 2022 exclusion
df_sensitivity <- read_csv("its_dataset.csv") %>%
  bind_rows(
    read_csv("its_dataset.csv") %>%
      filter(FALSE)  # placeholder — will be replaced with full dataset
  )

# Load full dataset including 2022
df_full2 <- read_csv("its_dataset.csv")
# Note: its_dataset.csv already excludes 2022 — sensitivity check
# requires re-running build_its_dataset.py with 2022 included
# This is flagged for completion in the robustness check appendix
cat("Note: Sensitivity check requires its_dataset_full.csv (including 2022).\n")
cat("Run build_its_dataset.py with 2022 included to generate this file.\n")


# ── 8. H3 Correlation Analysis ────────────────────────────────────────────────
cat("\n=== H3: NVIDIA Data Center Revenue vs Semiconductor PPI ===\n")

# Load NVIDIA and PPI data from SQLite
library(DBI)
library(RSQLite)

conn <- dbConnect(RSQLite::SQLite(), "dram_tracker.db")

nvidia <- dbGetQuery(conn, "
  SELECT period, revenue_usd
  FROM nvidia_financials
  WHERE segment = 'data_center'
  ORDER BY period
")

ppi <- dbGetQuery(conn, "
  SELECT date, value
  FROM dram_prices
  WHERE series_name = 'semiconductor_ppi'
  ORDER BY date
")

dbDisconnect(conn)

# Aggregate NVIDIA to annual
nvidia$year <- as.integer(substr(nvidia$period, 1, 4))
nvidia_annual <- nvidia %>%
  group_by(year) %>%
  summarise(dc_revenue = sum(revenue_usd) / 1e9, .groups = "drop")

# Aggregate PPI to annual
ppi$year <- as.integer(substr(ppi$date, 1, 4))
ppi_annual <- ppi %>%
  group_by(year) %>%
  summarise(ppi_value = mean(value), .groups = "drop")

# Merge
h3_df <- inner_join(nvidia_annual, ppi_annual, by = "year") %>%
  filter(year >= 2015 & year <= 2025)

cat("H3 dataset:\n")
print(h3_df)

# Pearson correlation
pearson_h3 <- cor.test(h3_df$dc_revenue, h3_df$ppi_value, method = "pearson")
cat("\nPearson correlation (NVIDIA DC Revenue vs PPI):\n")
print(pearson_h3)

# Spearman as robustness
spearman_h3 <- cor.test(h3_df$dc_revenue, h3_df$ppi_value, method = "spearman")
cat("\nSpearman correlation:\n")
print(spearman_h3)

# OLS regression
m_h3 <- lm(ppi_value ~ dc_revenue, data = h3_df)
cat("\nOLS: PPI ~ NVIDIA Data Center Revenue:\n")
summary(m_h3)


# ── 9. Export Results ─────────────────────────────────────────────────────────
sink("analysis/its_results.txt")
cat("ITS Analysis Results\n")
cat("Thesis: Hardware Cannibalization and Software Strategy\n")
cat("Author: Salvatore Caldara, Tilburg University 2025-2026\n")
cat("=======================================================\n\n")

cat("=== H1: ITS Regression Results ===\n")
cat("Model 1 - Basic ITS:\n")
summary(m1)
cat("\nModel 2 - ITS + Genre FE:\n")
summary(m2)
cat("\nModel 3 - ITS + Genre FE + Rec RAM:\n")
summary(m3)

cat("\n=== Genre Subsamples ===\n")
cat("Sports:\n")
summary(m_sports)
cat("\nGraphically Intensive:\n")
summary(m_intensive)

cat("\n=== H3: Correlation Analysis ===\n")
print(pearson_h3)
sink()

cat("\nAll results saved to analysis/its_results.txt\n")
cat("Pre-trend plot saved to analysis/its_pretrend_plot.png\n")
cat("\nDone.\n")

# ── Sensitivity Check: Including 2022 ────────────────────────────────────────
df_sens <- read_csv("its_dataset_full.csv")

m_sens <- feols(min_ram_gb ~ time_index + post + time_since_break | genre,
                data = df_sens, vcov = "HC1")

cat("=== Sensitivity Check: ITS including 2022 as pre-shock ===\n")
summary(m_sens)