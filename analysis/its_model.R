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

df %>% filter(post == 0) %>% summarise(mean(min_ram_gb))
df %>% filter(post == 1) %>% summarise(mean(min_ram_gb))

ggplot(df_chow, aes(x = time_index, y = min_ram_gb, color = factor(break_dummy))) +
  geom_point() +
  geom_smooth(method = "lm", se = FALSE) +
  scale_color_manual(values = c("0" = "steelblue", "1" = "coral"),
                     labels = c("Pre-shock", "Post-shock")) +
  labs(title = "Chow Test: Structural Break in PC RAM Requirements",
       x = "Time Index", y = "Minimum RAM (GB)", color = "Period") +
  theme_minimal()

# ── H2: Upscaling Adoption Logistic Regression ───────────────────────────────
cat("\n=== H2: AI Upscaling Adoption ===\n")

library(DBI)
library(RSQLite)

conn <- dbConnect(RSQLite::SQLite(), "dram_tracker.db")

upscaling <- dbGetQuery(conn, "
    SELECT 
        g.title, g.genre, g.release_date, g.min_ram_gb,
        u.has_upscaling
    FROM game_requirements g
    JOIN upscaling_support u ON g.app_id = u.app_id
    WHERE g.min_ram_gb IS NOT NULL
    AND u.source != 'pending'
")

dbDisconnect(conn)

# Parse year and assign period
upscaling$year <- as.integer(substr(upscaling$release_date, 
                                    nchar(upscaling$release_date)-3, 
                                    nchar(upscaling$release_date)))
upscaling$year <- as.integer(gsub(".*([0-9]{4}).*", "\\1", upscaling$release_date))
upscaling <- upscaling[!is.na(upscaling$year) & upscaling$year >= 2015 & upscaling$year <= 2026,]
upscaling <- upscaling[upscaling$year != 2022,]
upscaling$post <- as.integer(upscaling$year >= 2023)
upscaling$time_index <- upscaling$year - 2015

# Descriptive
cat("Upscaling adoption by period:\n")
print(tapply(upscaling$has_upscaling, 
             ifelse(upscaling$post==1, "ai_intensive", "pre_ai"), 
             mean))

# H2: Logistic regression
h2_m1 <- glm(has_upscaling ~ post, 
             data = upscaling, family = binomial)

h2_m2 <- glm(has_upscaling ~ post + genre, 
             data = upscaling, family = binomial)

h2_m3 <- glm(has_upscaling ~ time_index + post, 
             data = upscaling, family = binomial)

cat("\nModel 1 - Basic (post only):\n")
summary(h2_m1)

cat("\nModel 2 - With genre controls:\n")
summary(h2_m2)

cat("\nModel 3 - With time trend:\n")
summary(h2_m3)

cat("\nOdds ratios Model 1:\n")
print(exp(coef(h2_m1)))

# Save
sink("analysis/h2_results.txt")
cat("H2: AI Upscaling Adoption Results\n\n")
cat("Adoption rates:\n")
print(tapply(upscaling$has_upscaling, 
             ifelse(upscaling$post==1, "ai_intensive", "pre_ai"), mean))
cat("\nModel 1:\n"); summary(h2_m1)
cat("\nModel 2:\n"); summary(h2_m2)
cat("\nModel 3:\n"); summary(h2_m3)
cat("\nOdds ratios:\n"); print(exp(coef(h2_m1)))
sink()
cat("H2 results saved to analysis/h2_results.txt\n")

# ── H4: DRAM Prices and Upscaling Adoption ───────────────────────────────────
cat("\n=== H4: DRAM Price Proxy vs Upscaling Adoption ===\n")

conn <- dbConnect(RSQLite::SQLite(), "dram_tracker.db")

ppi_annual <- dbGetQuery(conn, "
    SELECT substr(date,1,4) as year, AVG(value) as ppi_value
    FROM dram_prices
    WHERE series_name = 'semiconductor_ppi'
    GROUP BY substr(date,1,4)
") 

dbDisconnect(conn)

ppi_annual$year <- as.integer(ppi_annual$year)

# Merge upscaling data with PPI by release year
h4_df <- merge(upscaling, ppi_annual, by = "year")
h4_df <- h4_df[h4_df$year >= 2019,]  # PPI relevant from 2019 onwards

cat("H4 sample size:", nrow(h4_df), "games\n")
cat("PPI range:", round(min(h4_df$ppi_value),1), "to", 
    round(max(h4_df$ppi_value),1), "\n\n")

# H4 Model 1: Basic logistic — upscaling ~ PPI
h4_m1 <- glm(has_upscaling ~ ppi_value,
             data = h4_df, family = binomial)

# H4 Model 2: With genre controls
h4_m2 <- glm(has_upscaling ~ ppi_value + genre,
             data = h4_df, family = binomial)

# H4 Model 3: With time trend to separate PPI effect from general trend
h4_m3 <- glm(has_upscaling ~ ppi_value + time_index,
             data = h4_df, family = binomial)

cat("Model 1 - Basic:\n")
summary(h4_m1)

cat("\nModel 2 - With genre controls:\n")
summary(h4_m2)

cat("\nModel 3 - With time trend:\n")
summary(h4_m3)

cat("\nOdds ratios Model 1:\n")
print(exp(coef(h4_m1)))

# Note on direction
cat("\nNOTE: PPI is a broad semiconductor index — a declining PPI\n")
cat("represents falling manufacturing costs. H4 predicts higher prices\n")
cat("drive upscaling adoption, so expect a NEGATIVE coefficient\n")
cat("(higher PPI = lower prices = less pressure = less adoption).\n")
cat("A negative significant coefficient would SUPPORT H4.\n\n")

# Save
sink("analysis/h4_results.txt")
cat("H4: DRAM Price Proxy vs Upscaling Adoption\n\n")
cat("NOTE: Semiconductor PPI used as proxy — see limitations\n\n")
summary(h4_m1)
summary(h4_m2)
summary(h4_m3)
cat("\nOdds ratios:\n")
print(exp(coef(h4_m1)))
sink()
cat("H4 results saved to analysis/h4_results.txt\n")

# ── H4 Alternative: NVIDIA DC Revenue as AI Demand Proxy ─────────────────────
cat("\n=== H4 Alternative: NVIDIA DC Revenue vs Upscaling Adoption ===\n")
cat("Exploratory — tests reduced-form AI demand → upscaling relationship\n\n")

conn <- dbConnect(RSQLite::SQLite(), "dram_tracker.db")

nvidia_annual <- dbGetQuery(conn, "
    SELECT substr(period,1,4) as year, SUM(revenue_usd)/1e9 as dc_revenue
    FROM nvidia_financials
    WHERE segment = 'data_center'
    GROUP BY substr(period,1,4)
")

dbDisconnect(conn)

nvidia_annual$year <- as.integer(nvidia_annual$year)

# Merge with upscaling data
h4b_df <- merge(upscaling, nvidia_annual, by = "year")
h4b_df <- h4b_df[h4b_df$year >= 2019,]

cat("H4 alternative sample:", nrow(h4b_df), "games\n")
cat("NVIDIA DC revenue range: $", round(min(h4b_df$dc_revenue),1), 
    "bn to $", round(max(h4b_df$dc_revenue),1), "bn\n\n")

# Models
h4b_m1 <- glm(has_upscaling ~ dc_revenue,
              data = h4b_df, family = binomial)

h4b_m2 <- glm(has_upscaling ~ dc_revenue + genre,
              data = h4b_df, family = binomial)

h4b_m3 <- glm(has_upscaling ~ dc_revenue + time_index,
              data = h4b_df, family = binomial)

cat("Model 1 - Basic:\n")
summary(h4b_m1)

cat("\nModel 2 - With genre controls:\n")
summary(h4b_m2)

cat("\nModel 3 - With time trend:\n")
summary(h4b_m3)

cat("\nOdds ratios Model 1:\n")
print(exp(coef(h4b_m1)))

# Append to H4 results file
sink("analysis/h4_results.txt", append = TRUE)
cat("\n\n=== H4 Alternative: NVIDIA DC Revenue Proxy ===\n")
cat("Exploratory reduced-form test\n\n")
summary(h4b_m1)
summary(h4b_m2)
summary(h4b_m3)
cat("\nOdds ratios:\n")
print(exp(coef(h4b_m1)))
sink()
cat("H4 alternative results appended to analysis/h4_results.txt\n")

# ── H2 Bar Chart ──────────────────────────────────────────────────────────────
library (tidyverse)

adoption_df <- data.frame(
  period = c("Pre-Shock\n(2015–2021)", "AI-Intensive\n(2023–2026)"),
  adoption = c(
    round(mean(upscaling$has_upscaling[upscaling$year < 2022]) * 100, 1),
    round(mean(upscaling$has_upscaling[upscaling$year >= 2023]) * 100, 1)
  )
)

ggplot(adoption_df, aes(x = period, y = adoption, fill = period)) +
  geom_bar(stat = "identity", width = 0.5) +
  geom_text(aes(label = paste0(adoption, "%")), 
            vjust = -0.5, size = 5, fontface = "bold") +
  scale_fill_manual(values = c("#00b4d8", "#f4a261")) +
  scale_y_continuous(limits = c(0, 95), 
                     labels = function(x) paste0(x, "%")) +
  labs(
    title = "AI Upscaling Adoption Rate by Period",
    subtitle = "Share of AAA PC games supporting DLSS, FSR, or XeSS",
    x = NULL,
    y = "Adoption Rate (%)",
    caption = "Source: Author's own compilation. N = 113 games."
  ) +
  theme_minimal(base_size = 14) +
  theme(
    legend.position = "none",
    plot.title = element_text(face = "bold"),
    plot.subtitle = element_text(color = "gray40")
  )

ggsave("analysis/h2_adoption_chart.png", width = 6, height = 5, dpi = 300)
cat("H2 bar chart saved to analysis/h2_adoption_chart.png\n")

df %>%
  group_by(genre, period) %>%
  summarise(
    n = n(),
    mean_ram = round(mean(min_ram_gb), 2),
    .groups = "drop"
  ) %>%
  arrange


cat("Post adoption:", mean(upscaling$has_upscaling[upscaling$year >= 2023]), "\n")
cat("Pre adoption:", mean(upscaling$has_upscaling[upscaling$year < 2022]), "\n")
cat("N:", nrow(upscaling), "\n")

getwd()

df_chow <- df %>% mutate(break_dummy = as.integer(year >= 2023))
m_restricted   <- lm(min_ram_gb ~ time_index, data = df_chow)
m_unrestricted <- lm(min_ram_gb ~ time_index * break_dummy, data = df_chow)
anova(m_restricted, m_unrestricted)

summary(m1)
summary(m2)
summary(m3)