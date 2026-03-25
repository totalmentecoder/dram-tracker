# ============================================================================
# DiD Model: AI Supply Shock and PC Game RAM Requirements
# ============================================================================
# Thesis: Hardware Cannibalization and Software Strategy
# Author: Salvatore Caldara, Tilburg University, 2025-2026
#
# Research Question:
# How has the AI-driven supply shock in the consumer RAM market affected
# minimum RAM requirements in PC games compared with console counterparts?
#
# Model:
# RAM_it = α + β1·PC + β2·Post + β3·(PC × Post) + controls + ε
#
# Where:
# - RAM_it   = minimum RAM requirement for game i, platform t
# - PC       = 1 if PC platform, 0 if console (treatment indicator)
# - Post     = 1 if released 2023+, 0 if 2019-2022 (period indicator)
# - PC×Post  = DiD interaction term — THIS IS β3, your main finding
# - β3 < 0  → PC requirements grew LESS than console trend → flattening
# - β3 > 0  → PC requirements grew MORE than console trend → inflation
# - β3 = 0  → no differential effect → no evidence of shock response
#
# Package: fixest — fast fixed effects estimation, standard in econometrics
# ============================================================================

library(fixest)
library(tidyverse)
library(modelsummary)

# ── 1. Load Data ─────────────────────────────────────────────────────────────

# Set working directory to your dram-tracker folder
# Update this path if needed
setwd("C:/Users/Salvatore Caldara/Desktop/dram-tracker")

df <- read_csv("did_dataset.csv")

cat("Dataset loaded:", nrow(df), "observations\n")
cat("Games:", nrow(df) / 2, "\n")
cat("Platforms:", unique(df$platform), "\n")
cat("Periods:", unique(df$period), "\n\n")


# ── 2. Descriptive Statistics ─────────────────────────────────────────────────
# Before running any regression, always examine your data visually.
# This table shows the mean RAM requirement by platform and period —
# the raw DiD estimate before controlling for anything.

cat("=== Descriptive Statistics ===\n")
desc_table <- df %>%
  group_by(platform, period) %>%
  summarise(
    n         = n(),
    mean_ram  = round(mean(min_ram_gb, na.rm = TRUE), 2),
    sd_ram    = round(sd(min_ram_gb, na.rm = TRUE), 2),
    min_ram   = min(min_ram_gb, na.rm = TRUE),
    max_ram   = max(min_ram_gb, na.rm = TRUE),
    .groups   = "drop"
  )
print(desc_table)

# Raw DiD calculation (manual)
# This is what the regression will formally test
pre_pc      <- df %>% filter(platform == "PC",      period == "pre_ai")       %>% pull(min_ram_gb) %>% mean()
post_pc     <- df %>% filter(platform == "PC",      period == "ai_intensive") %>% pull(min_ram_gb) %>% mean()
pre_con     <- df %>% filter(platform == "Console", period == "pre_ai")       %>% pull(min_ram_gb) %>% mean()
post_con    <- df %>% filter(platform == "Console", period == "ai_intensive") %>% pull(min_ram_gb) %>% mean()

raw_did <- (post_pc - pre_pc) - (post_con - pre_con)

cat("\n=== Raw DiD Estimate ===\n")
cat("PC:      pre =", round(pre_pc, 2), "→ post =", round(post_pc, 2), "| Δ =", round(post_pc - pre_pc, 2), "GB\n")
cat("Console: pre =", round(pre_con, 2), "→ post =", round(post_con, 2), "| Δ =", round(post_con - pre_con, 2), "GB\n")
cat("DiD (β3):", round(raw_did, 2), "GB\n\n")


# ── 3. Visualisation ──────────────────────────────────────────────────────────
# The parallel trends plot — the most important diagnostic for DiD validity.
# Shows mean RAM by platform and period. If the lines were parallel before
# the shock, the parallel trends assumption holds.

plot_df <- df %>%
  group_by(platform, period) %>%
  summarise(mean_ram = mean(min_ram_gb, na.rm = TRUE), .groups = "drop") %>%
  mutate(period = factor(period, levels = c("pre_ai", "ai_intensive"),
                         labels = c("Pre-AI (2019-2022)", "AI-Intensive (2023-2026)")))

ggplot(plot_df, aes(x = period, y = mean_ram, color = platform, group = platform)) +
  geom_line(linewidth = 1.5) +
  geom_point(size = 4) +
  geom_label(aes(label = paste0(round(mean_ram, 1), " GB")),
             nudge_y = 0.3, show.legend = FALSE) +
  scale_color_manual(values = c("PC" = "#f4a261", "Console" = "#00b4d8")) +
  labs(
    title    = "DiD: Mean Minimum RAM Requirements by Platform and Period",
    subtitle = "Treatment: PC games | Control: Console games (fixed 16GB hardware)",
    x        = "Period",
    y        = "Mean Minimum RAM (GB)",
    color    = "Platform",
    caption  = "Source: Steam Store API, PCGamingWiki. Author's own compilation."
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title    = element_text(face = "bold"),
    plot.subtitle = element_text(color = "gray40"),
    legend.position = "bottom"
  )

ggsave("did_plot.png", width = 8, height = 5, dpi = 300)
cat("Plot saved: did_plot.png\n\n")


# ── 4. DiD Regression Models ─────────────────────────────────────────────────
# We estimate three progressively refined models.
# fixest::feols() is used — it handles fixed effects efficiently and
# produces heteroskedasticity-robust standard errors by default.

# Model 1: Basic DiD
# No controls — pure treatment effect estimate
# RAM = α + β1·PC + β2·Post + β3·(PC×Post) + ε
m1 <- feols(min_ram_gb ~ pc_dummy + post + did,
            data = df,
            vcov = "HC1")  # Heteroskedasticity-robust standard errors

# Model 2: DiD with year fixed effects
# Controls for year-specific shocks affecting all games equally
# (e.g., economic conditions, hardware generation cycles)
m2 <- feols(min_ram_gb ~ pc_dummy + post + did | year,
            data = df,
            vcov = "HC1")

# Model 3: DiD with year fixed effects + recommended RAM as control
# Recommended RAM captures game ambition/scope as a control variable
# If a game recommends 32GB but requires 8GB minimum, that's a
# deliberate accessibility decision — relevant to your RQ
m3 <- feols(min_ram_gb ~ pc_dummy + post + did + rec_ram_gb | year,
            data = df,
            vcov = "HC1")

cat("=== Regression Results ===\n")
cat("β3 (DiD coefficient) interpretation:\n")
cat("  Negative → PC requirements grew LESS than console (flattening hypothesis)\n")
cat("  Positive → PC requirements grew MORE than console (inflation hypothesis)\n")
cat("  Zero     → No differential effect detected\n\n")

# Print results
summary(m1)
summary(m2)
summary(m3)

# ── 5. Parallel Trends Assumption Check ──────────────────────────────────────
# The DiD assumption: in the absence of the shock, PC and console RAM
# requirements would have followed parallel trends.
# We can't directly test this (counterfactual), but we can check
# whether the pre-period trends look similar.

cat("\n=== Pre-Period Trend Check ===\n")
pre_only <- df %>% filter(period == "pre_ai")

pre_trend <- feols(min_ram_gb ~ pc_dummy * year,
                   data = pre_only,
                   vcov = "HC1")

cat("If the interaction term (pc_dummy:year) is NOT significant,\n")
cat("PC and console requirements followed similar trends pre-shock.\n\n")
summary(pre_trend)


# ── 6. Export Results ─────────────────────────────────────────────────────────

# Save regression table as a text file for your thesis appendix
sink("did_results.txt")
cat("DiD Regression Results\n")
cat("Thesis: Hardware Cannibalization and Software Strategy\n")
cat("Author: Salvatore Caldara, Tilburg University 2025-2026\n\n")
summary(m1)
summary(m2)
summary(m3)

cat("Results saved: did_results.txt\n")
cat("\nDone. Check did_plot.png and did_results.txt in your dram-tracker folder.\n")