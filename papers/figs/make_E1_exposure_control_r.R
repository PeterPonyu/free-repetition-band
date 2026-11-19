#!/usr/bin/env Rscript
# make_E1_exposure_control_r.R — E1 exposure-control battery (E1-C, 324 runs).
# Four-panel contract figure from the persisted verdict:
#   (a) plant-rate comparison r1 vs r4 (paired onsets per cell)
#   (b) ordering on the nominal epoch axis (order tally)
#   (c) ordering on the gradient-exposure axis (nominal vs exposure tally)
#   (d) free-band invariance (R_free per cell by rate)
# Data source: experiments/revision2026/gpu2026/e1c/e1c_verdict.json (read here,
# never hardcoded). Run from repo root: Rscript papers/figs/make_E1_exposure_control_r.R

ver <- paste(R.version$major, sub('\\..*', '', R.version$minor), sep = '.')
userlib <- file.path(Sys.getenv('HOME'), 'R', 'x86_64-pc-linux-gnu-library', ver)
.libPaths(c(userlib, .libPaths()))

suppressPackageStartupMessages({
  library(jsonlite)
  library(ggplot2)
  library(dplyr)
  library(tidyr)
  library(scales)
  library(patchwork)
  library(ragg)
  library(svglite)
})
`%||%` <- function(x, y) if (is.null(x) || length(x) == 0) y else x

root   <- normalizePath(file.path(getwd()))
figdir <- file.path(root, 'papers', 'figs')
evdir  <- file.path(figdir, 'evidence_r')
dir.create(evdir, showWarnings = FALSE, recursive = TRUE)
source(file.path(figdir, 'fig_pipeline.R'))
source(file.path(figdir, 'E1_panel_contract.R'))

CB <- list(blue = '#0072B2', orange = '#E69F00', vermillion = '#D55E00',
           green = '#009E73', skyblue = '#56B4E9', grey = '#999999',
           black = '#000000')

paper_theme <- function(base_size = 9) {
  theme_minimal(base_size = base_size, base_family = 'TeX Gyre Termes') +
    theme(
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_blank(),
      panel.grid.major.y = element_line(linewidth = 0.25, colour = '#d9dde3'),
      axis.title = element_text(family = 'TeX Gyre Termes', colour = '#1a202c', size = base_size),
      axis.text = element_text(family = 'TeX Gyre Termes', colour = '#2d3748', size = base_size - 0.5),
      legend.position = 'top',
      legend.title = element_text(family = 'TeX Gyre Termes', size = base_size - 0.5),
      legend.text = element_text(family = 'TeX Gyre Termes', size = base_size - 0.5),
      strip.text = element_text(family = 'TeX Gyre Termes', face = 'plain', colour = '#1a202c')
    )
}

save_both <- function(p, name, w = 7.2, h = 5.2) {
  png_path <- file.path(figdir, paste0(name, '.png'))
  svg_path <- file.path(evdir, paste0(name, '.svg'))
  ragg::agg_png(png_path, width = w, height = h, units = 'in', res = 300, scaling = 1)
  print(p); dev.off()
  svglite::svglite(svg_path, width = w, height = h)
  print(p); dev.off()
  emit_vector(p, name, w, h)
  cat(sprintf('  saved %s  (%d bytes)\n', png_path, file.info(png_path)$size))
}

read_json_r <- function(path, simplifyVector = TRUE) {
  txt <- paste(readLines(path, warn = FALSE), collapse = '\n')
  txt <- gsub('\\bNaN\\b', 'null', txt)
  txt <- gsub('\\bInfinity\\b', 'null', txt)
  jsonlite::fromJSON(txt, simplifyVector = simplifyVector)
}

cat('=== make_E1_exposure_control_r.R ===\n')
v <- read_json_r(file.path(root, 'experiments', 'revision2026', 'gpu2026', 'e1c',
                           'e1c_verdict.json'),
                 simplifyVector = FALSE)

# cells are named '<capacity>/<entropy>/<rate>' e.g. 'large/high/1'
cells <- v$cells
df <- bind_rows(lapply(names(cells), function(k) {
  parts <- strsplit(k, '/')[[1]]
  x <- cells[[k]]
  data.frame(cell      = paste(parts[1], parts[2], sep = '/'),
             rate      = as.integer(parts[3]),
             R_free    = as.numeric(x$R_free),
             mem_onset = as.numeric(x$mem_onset),
             decay_onset = as.numeric(x$decay_onset),
             order_nominal = as.character(x$order_nominal),
             order_exposure = as.character(x$order_exposure),
             seeds     = as.integer(x$n_seeds_pooled %||% NA),
             stringsAsFactors = FALSE)
}))
df$cell <- factor(df$cell, levels = unique(df$cell))

# (a) plant-rate comparison: paired onsets r1 vs r4 per cell
wide <- df %>%
  select(cell, rate, mem_onset, decay_onset, R_free) %>%
  pivot_wider(names_from = rate,
              values_from = c(mem_onset, decay_onset, R_free))
onset_long <- bind_rows(
  wide %>% transmute(cell, r1 = mem_onset_1, r4 = mem_onset_4, qty = 'memorization onset'),
  wide %>% transmute(cell, r1 = decay_onset_1, r4 = decay_onset_4, qty = 'decay onset')
)
pa <- ggplot(onset_long, aes(r1, r4, colour = qty)) +
  geom_abline(slope = 1, intercept = 0, colour = '#888888', linetype = 'dashed',
              linewidth = 0.5) +
  geom_point(size = 2.6, alpha = 0.9) +
  scale_colour_manual(values = c('memorization onset' = CB$vermillion,
                                 'decay onset' = CB$blue), name = NULL) +
  labs(title = 'Plant-rate comparison (r1 vs r4 onsets)',
       x = 'Onset epoch, rate 1', y = 'Onset epoch, rate 4') +
  paper_theme() + theme(legend.position = 'top')

# (b) ordering on the nominal epoch axis: order tally per rate
tally_nom <- df %>% count(rate, order_nominal) %>%
  mutate(order_nominal = factor(order_nominal))
pb <- ggplot(tally_nom, aes(factor(rate), n, fill = order_nominal)) +
  geom_col(width = 0.55, colour = 'white', linewidth = 0.2) +
  geom_text(aes(label = n), position = position_stack(vjust = 0.5),
            size = 2.6, colour = 'white') +
  scale_fill_manual(values = c(CB$blue, CB$orange, CB$green, CB$vermillion,
                               CB$skyblue, CB$grey)[seq_len(nlevels(tally_nom$order_nominal))],
                    name = NULL) +
  labs(title = 'Ordering on the nominal epoch axis',
       x = 'Plant rate', y = 'Cells') +
  paper_theme() + theme(legend.position = 'top')

# (c) ordering on the gradient-exposure axis: nominal vs exposure tally
tally_exp <- df %>% count(order_nominal, order_exposure) %>%
  mutate(order_exposure = factor(order_exposure),
         order_nominal = factor(order_nominal))
pc <- ggplot(tally_exp, aes(order_nominal, n, fill = order_exposure)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62,
           colour = 'white', linewidth = 0.2) +
  scale_fill_manual(values = c(CB$blue, CB$orange, CB$green, CB$vermillion,
                               CB$skyblue, CB$grey)[seq_len(nlevels(tally_exp$order_exposure))],
                    name = NULL) +
  labs(title = 'Ordering on the gradient-exposure axis',
       x = 'Nominal-axis order', y = 'Cells') +
  paper_theme() + theme(legend.position = 'top',
                        axis.text.x = element_text(size = 6.4, angle = 35, hjust = 1),
                        plot.margin = margin(5.5, 6, 20, 6))

# (d) free-band invariance: R_free per cell by rate
pd <- ggplot(df, aes(cell, R_free, fill = factor(rate))) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62,
           colour = 'white', linewidth = 0.2) +
  scale_fill_manual(values = c('1' = CB$blue, '4' = CB$orange), name = 'rate') +
  scale_y_continuous(breaks = c(0, 4, 10, 20)) +
  labs(title = 'Free band invariance (R_free by cell and rate)',
       x = NULL, y = expression(R[free])) +
  paper_theme() + theme(legend.position = 'top',
                        axis.text.x = element_text(size = 6.4, angle = 35, hjust = 1),
                        plot.margin = margin(5.5, 6, 20, 6))

p_all <- compose_E1_four_panel(list(pa, pb, pc, pd), 'E1_exposure_control',
                               7.2, 5.2, root)
save_both(p_all, 'E1_exposure_control', 7.2, 5.2)

cat('=== done make_E1_exposure_control_r.R ===\n')
