#!/usr/bin/env Rscript
# make_E1_figs_r.R — Professional R/ggplot2 renderers for all 5 E1 figures.
# Data sources: synthetic Markov corpus repeat-verdict summaries (figures-013),
#               real-text 50M-token budget results (repeated_data_realtext),
#               and real-text threshold robustness manifests (figures-redteam).
# Outputs: papers/figs/<name>.png (300 dpi ragg) + papers/figs/evidence_r/<name>.svg

# --- library path setup ---
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

# --- paths ---
root    <- normalizePath(file.path(getwd()))
figdir  <- file.path(root, 'papers', 'figs')
evdir   <- file.path(figdir, 'evidence_r')
dir.create(evdir, showWarnings = FALSE, recursive = TRUE)
source(file.path(figdir, 'fig_pipeline.R'))
source(file.path(figdir, 'E1_panel_contract.R'))

# --- Okabe-Ito colourblind-safe palette ---
CB <- list(
  blue       = '#0072B2',
  orange     = '#E69F00',
  vermillion = '#D55E00',
  green      = '#009E73',
  skyblue    = '#56B4E9',
  yellow     = '#F0E442',
  purple     = '#CC79A7',
  grey       = '#999999',
  black      = '#000000'
)

# --- 9-cell colour/shape mapping ---
CELL_COLOURS <- c(
  'small/low'  = '#0072B2',
  'small/med'  = '#E69F00',
  'small/high' = '#009E73',
  'med/low'    = '#D55E00',
  'med/med'    = '#CC79A7',
  'med/high'   = '#000000',
  'large/low'  = '#56B4E9',
  'large/med'  = '#CC79A7',
  'large/high' = '#999999'
)
CELL_SHAPES <- c(
  'small/low'  = 16,
  'small/med'  = 15,
  'small/high' = 17,
  'med/low'    = 18,
  'med/med'    = 25,
  'med/high'   = 8,
  'large/low'  = 4,
  'large/med'  = 11,
  'large/high' = 10
)

# --- professional paper theme ---
# Tag (a)(b) labels: bold 11pt; title: plain 10pt; axis.title: 9pt; axis.text/legend: 8.5pt
paper_theme <- function(base_size = 8.5) {
  theme_minimal(base_size = base_size, base_family = 'TeX Gyre Termes') +
    theme(
      panel.grid.minor     = element_blank(),
      panel.grid.major.x   = element_blank(),
      panel.grid.major.y   = element_line(linewidth = 0.25, colour = '#d9dde3'),
      axis.title           = element_text(family = 'TeX Gyre Termes', colour = '#1a202c', size = 9),
      axis.text            = element_text(family = 'TeX Gyre Termes', colour = '#2d3748', size = 8.5),
      plot.title           = element_text(family = 'TeX Gyre Termes', face = 'plain', colour = '#111827', size = 10),
      plot.subtitle        = element_text(family = 'TeX Gyre Termes', colour = '#1a1a1a', size = base_size - 0.5),
      legend.position      = 'right',
      legend.title         = element_text(family = 'TeX Gyre Termes', size = 8.5),
      legend.text          = element_text(family = 'TeX Gyre Termes', size = 8.5),
      strip.text           = element_text(family = 'TeX Gyre Termes', face = 'plain', colour = '#1a202c'),
      plot.margin          = margin(5.5, 6, 5.5, 6)
    )
}

# --- uniform patchwork tag theme: panel labels (a)(b) bold 11pt ---
tag_theme <- theme(
  plot.tag          = element_text(face = 'bold', size = 11),
  plot.tag.position = c(0.02, 0.98)
)

# --- save_both: ragg 300dpi PNG + svglite SVG ---
save_both <- function(p, name, w = 7.2, h = 4.2) {
  pngp <- file.path(figdir, paste0(name, '.png'))
  svgp <- file.path(evdir,  paste0(name, '.svg'))
  ragg::agg_png(pngp, width = w, height = h, units = 'in', res = 300, scaling = 1)
  print(p)
  dev.off()
  svglite::svglite(svgp, width = w, height = h)
  print(p)
  dev.off()
  emit_vector(p, name, w, h)
  cat('saved', pngp, '\n     ', svgp, '\n')
}

# ============================================================
# Figure 1: E1_case — case study (med/med cell)
#   Data: repeat-verdict summary JSON, cell med/med
#   Two panels: (a) excess val loss vs n, (b) canary gap vs n
# ============================================================
make_E1_case <- function() {
  cat('\n--- E1_case ---\n')
  verd <- fromJSON(file.path(root, 'experiments', 'results', 'figures-013', 'repeat_verdicts.json'),
                   simplifyVector = FALSE)
  cell <- verd$cells[['med/med']]
  free_eps   <- verd$free_eps_nats   # 0.05
  canary_eps <- verd$canary_eps       # 0.10
  R_free_n   <- cell$R_free_epochs    # 4
  decay_on   <- cell$decay_onset      # 10
  mem_on     <- cell$mem_onset        # 10
  ns <- as.integer(names(cell$excess))
  excess <- as.numeric(unlist(cell$excess))
  canary <- as.numeric(unlist(cell$canary))

  cat(sprintf('  med/med: R_free=%d, free_eps=%.2f, canary_eps=%.2f\n', R_free_n, free_eps, canary_eps))
  cat(sprintf('  decay_onset=%d, mem_onset=%d, coincide=%s\n',
              decay_on, mem_on, as.character(cell$onset_coincide)))
  cat('  n:', ns, '\n')
  cat('  excess:', round(excess, 4), '\n')
  cat('  canary:', round(canary, 4), '\n')

  df_ex <- data.frame(n = ns, excess = excess)
  df_ca <- data.frame(n = ns, canary = canary)

  # Clamp zeros/negatives to a small positive for log-scale y; panel (a) uses log-log
  df_ex$excess_plot <- pmax(df_ex$excess, 3e-3)

  # Point labels: nudge right so they don't sit on the data points
  df_label <- df_ex[df_ex$n %in% c(4, 10), ]

  pa <- ggplot(df_ex, aes(n, excess_plot)) +
    annotate('rect', xmin = 0.8, xmax = R_free_n * 1.08,
             ymin = 3e-3, ymax = 12, fill = CB$green, alpha = 0.08) +
    geom_hline(yintercept = free_eps, colour = CB$green, linetype = 'dashed', linewidth = 0.45) +
    geom_vline(xintercept = R_free_n, colour = CB$green, linetype = 'dotted', linewidth = 0.45) +
    geom_line(colour = CB$blue, linewidth = 1.1) +
    geom_point(colour = CB$blue, size = 2.8) +
    # Threshold label at left edge, above the dashed line
    annotate('text', x = 0.85, y = free_eps * 2.2,
             label = sprintf('ε = %.2f nats', free_eps),
             size = 2.7, colour = 'black', hjust = 0) +
    # R_free label placed LEFT of the dotted vertical to avoid right-edge clipping
    annotate('text', x = R_free_n * 0.72, y = 0.3,
             label = 'R[free]==4', parse = TRUE,
             size = 2.7, colour = 'black', hjust = 1) +
    scale_x_log10(breaks = c(1, 2, 4, 10, 20, 40), labels = c('1','2','4','10','20','40')) +
    scale_y_log10(labels = label_number(accuracy = 0.001)) +
    labs(title = 'Excess validation loss', x = 'Epoch count n', y = 'Excess val loss (nats)') +
    paper_theme() + tag_theme

  pb <- ggplot(df_ca, aes(n, canary)) +
    annotate('rect', xmin = 0.8, xmax = R_free_n * 1.08,
             ymin = min(df_ca$canary) - 0.05, ymax = max(df_ca$canary) + 0.3,
             fill = CB$green, alpha = 0.08) +
    geom_hline(yintercept = canary_eps, colour = CB$orange, linetype = 'dashed', linewidth = 0.45) +
    geom_vline(xintercept = cell$mem_onset, colour = CB$orange, linetype = 'dotted', linewidth = 0.45) +
    geom_line(colour = CB$vermillion, linewidth = 1.1) +
    geom_point(colour = CB$vermillion, size = 2.8) +
    # Memorization onset label: place LEFT of the dotted vertical to avoid right-edge clipping
    annotate('text', x = cell$mem_onset * 0.72, y = max(df_ca$canary) * 0.28,
             label = sprintf('mem. onset\nn=%d', cell$mem_onset),
             size = 2.7, colour = 'black', hjust = 1, lineheight = 0.9) +
    # Threshold label at left edge, above line
    annotate('text', x = 0.85, y = canary_eps + 0.22,
             label = sprintf('ε = %.2f', canary_eps),
             size = 2.7, colour = 'black', hjust = 0) +
    scale_x_log10(breaks = c(1, 2, 4, 10, 20, 40), labels = c('1','2','4','10','20','40')) +
    labs(title = 'Canary memorization gap', x = 'Epoch count n', y = 'Canary memorization gap') +
    paper_theme() + tag_theme

  # Panel (c): decay onset == memorization onset, shown on a SHARED n-axis.
  # Each metric is normalised to its own threshold (excess/eps_free, canary/eps_canary)
  # so both curves cross 1.0 exactly at their onset. The two onsets coincide at n=10,
  # which the two-panel view above cannot show because (a) and (b) have separate axes.
  df_co <- rbind(
    data.frame(n = ns, ratio = excess / free_eps,   metric = 'decay'),
    data.frame(n = ns, ratio = canary / canary_eps,  metric = 'memorization')
  )
  df_co$metric <- factor(df_co$metric, levels = c('decay', 'memorization'),
                         labels = c('val-loss decay', 'canary memorization'))
  # Clamp for log-y: smallest positive ratio used as floor for non-positive values.
  df_co$ratio_plot <- pmax(df_co$ratio, 0.02)
  coincide_lab <- if (isTRUE(cell$onset_coincide))
    sprintf('decay onset == mem. onset\nn = %d', decay_on) else
    sprintf('decay n=%d / mem n=%d', decay_on, mem_on)

  pc <- ggplot(df_co, aes(n, ratio_plot, colour = metric, shape = metric)) +
    # Free zone (n <= R_free) shaded for cross-reference with panel (a)
    annotate('rect', xmin = 0.8, xmax = R_free_n * 1.08,
             ymin = 0.02, ymax = max(df_co$ratio_plot) * 1.4,
             fill = CB$green, alpha = 0.07) +
    # Threshold-crossing line: ratio == 1 is the onset for BOTH metrics
    geom_hline(yintercept = 1, colour = CB$grey, linetype = 'dashed', linewidth = 0.45) +
    # Coincident onsets: decay (n=10) and mem (n=10) fall on the SAME vertical
    geom_vline(xintercept = decay_on, colour = CB$purple, linetype = 'dotted', linewidth = 0.6) +
    geom_line(linewidth = 1.0) +
    geom_point(size = 2.6) +
    annotate('text', x = 1, y = 1.45, label = 'onset (ratio = 1)',
             size = 2.6, colour = 'black', family = 'TeX Gyre Termes', hjust = 0) +
    scale_x_log10(breaks = c(1, 2, 4, 10, 20, 40), labels = c('1','2','4','10','20','40')) +
    scale_y_log10(labels = label_number(accuracy = 0.01)) +
    scale_colour_manual(values = c(CB$blue, CB$vermillion), name = NULL) +
    scale_shape_manual(values = c(16, 17), name = NULL) +
    labs(title = 'Onset coincidence (shared axis)', x = 'Epoch count n',
         y = 'Metric / threshold') +
    paper_theme() + tag_theme +
    theme(legend.position = c(0.03, 0.99), legend.justification = c(0, 1),
          # Transparent legend backing: the former alpha-0.7 white panel tinted the
          # val-loss line where it passed beneath, producing a pale-blue "ghost"
          # stroke near n=20-40. The legend sits in the empty top-left triangle
          # above both rising curves, so no backing is needed.
          legend.background = element_rect(fill = NA, colour = NA),
          legend.key = element_rect(fill = NA, colour = NA),
          legend.key.height = unit(9, 'pt'),
          legend.spacing.y = unit(1, 'pt'))

  # Panel (d): exposure-matched control for THIS cell (E1-C, 324 runs): the
  # free band is probe-invariant (R_free identical at plant rates 4 and 1)
  # while the onset ordering inverts (coincides at r4, lags at r1)
  e1c <- fromJSON(file.path(root, 'experiments', 'revision2026', 'gpu2026', 'e1c',
                            'e1c_verdict.json'), simplifyVector = FALSE)
  mm <- e1c$paired_cells[['med/med']]
  c4 <- e1c$cells[['med/med/4']]
  c1 <- e1c$cells[['med/med/1']]
  rf4 <- c4$R_free; rf1 <- c1$R_free
  ctrl_long <- rbind(
    data.frame(arm = 'r4 (published)', qty = 'decay onset', n = mm$r4_decay_onset),
    data.frame(arm = 'r4 (published)', qty = 'memorization onset', n = mm$r4_mem_onset),
    data.frame(arm = 'r1 (exposure-matched)', qty = 'decay onset', n = mm$r1_decay_onset),
    data.frame(arm = 'r1 (exposure-matched)', qty = 'memorization onset', n = mm$r1_mem_onset))
  ctrl_long$arm <- factor(ctrl_long$arm,
                          levels = c('r4 (published)', 'r1 (exposure-matched)'))
  pd <- ggplot(ctrl_long, aes(arm, n, colour = qty, shape = qty, group = qty)) +
    geom_line(linewidth = 0.8) +
    geom_point(size = 3) +
    annotate('text', x = 1.5, y = 21.5,
             label = sprintf('R_free identical (%d vs %d);\norder: %s -> %s',
                             rf4, rf1, mm$r4_order_nominal, mm$r1_order_nominal),
             size = 2.6, colour = 'black', family = 'TeX Gyre Termes') +
    scale_colour_manual(values = c(CB$blue, CB$vermillion), name = NULL) +
    scale_shape_manual(values = c(16, 17), name = NULL) +
    coord_cartesian(ylim = c(0, 24)) +
    labs(title = '(d) Exposure-matched control', x = NULL, y = 'Onset epoch n') +
    paper_theme() + tag_theme +
    theme(legend.position = 'top', axis.text.x = element_text(size = 7, angle = 15, hjust = 1))

  # Strip mode: patchwork tags collide with the top tick labels once the
  # title band is stripped (same failure as E1_repeat / E1_large_completion).
  # Route the tags through the title slot, which the stripper preserves.
  p <- compose_E1_four_panel(list(pa, pb, pc, pd), 'E1_case', 7.2, 5.4, root)
  save_both(p, 'E1_case', w = 7.2, h = 5.4)
}

# ============================================================
# Figure 2: E1_grid — full capacity x entropy grid heatmap + onset scatter
#   Data: repeat-verdict summary JSON (all 9 cells)
#   Two panels: (a) R_free heatmap (3x3 grid), (b) onset coincidence scatter
#   IMPORTANT: large/med has R_free=1 from a single n-point — mark with asterisk/NA
# ============================================================
make_E1_grid <- function() {
  cat('\n--- E1_grid ---\n')
  verd <- fromJSON(file.path(root, 'experiments', 'results', 'figures-013', 'repeat_verdicts.json'),
                   simplifyVector = FALSE)
  caps <- c('small', 'med', 'large')
  ents <- c('low', 'med', 'high')

  # Build a long data frame for heatmap
  hm_rows <- list()
  onset_rows <- list()
  for (cap in caps) {
    for (ent in ents) {
      key <- paste0(cap, '/', ent)
      cell <- verd$cells[[key]]
      if (is.null(cell)) next
      R <- cell$R_free_epochs
      cov <- isTRUE(cell$coverage_full)
      n_pts <- length(cell$n_points)
      # large/med: n_points = [1] only — single-point artifact
      single_point <- (!cov && n_pts <= 1)
      hm_rows[[length(hm_rows)+1]] <- data.frame(
        cap = cap, ent = ent,
        R_free = R,
        coverage_full = cov,
        single_point = single_point,
        label = ifelse(single_point, paste0(R, '*'), as.character(R)),
        stringsAsFactors = FALSE
      )
      do <- cell$decay_onset
      mo <- cell$mem_onset
      if (!is.null(do) && !is.null(mo)) {
        onset_rows[[length(onset_rows)+1]] <- data.frame(
          key = key, cap = cap, ent = ent,
          decay_onset = as.numeric(do),
          mem_onset   = as.numeric(mo),
          coincide    = (do == mo),
          stringsAsFactors = FALSE
        )
      }
    }
  }
  hm_df  <- bind_rows(hm_rows)
  ons_df <- bind_rows(onset_rows)

  # Factor ordering
  hm_df$cap  <- factor(hm_df$cap,  levels = caps)
  hm_df$ent  <- factor(hm_df$ent,  levels = ents)
  ons_df$key <- factor(ons_df$key, levels = sapply(caps, function(c) paste0(c,'/',ents)) |> as.vector())

  cat('R_free range:', verd$p1_R_free_range[[1]], 'to', verd$p1_R_free_range[[2]], '\n')
  cat('n_coincide:', verd$p3_n_coincide, '\n')
  cat('Cells:\n')
  for (r in seq_len(nrow(hm_df))) {
    cat(sprintf('  %s/%s: R_free=%d coverage=%s single_point=%s\n',
                hm_df$cap[r], hm_df$ent[r], hm_df$R_free[r],
                hm_df$coverage_full[r], hm_df$single_point[r]))
  }

  # Discrete colour scale: R_free bins  {1} red, {4} green, {10} blue
  rfree_colour <- function(r) {
    dplyr::case_when(
      r == 1  ~ '#c0392b',
      r == 4  ~ '#3a8a3a',
      r == 10 ~ '#2c6fb0',
      TRUE    ~ '#888888'
    )
  }
  hm_df$fill_col <- rfree_colour(hm_df$R_free)
  # NA-out single-point cells for fill so they show as grey
  hm_df$fill_col[hm_df$single_point] <- '#cccccc'

  pa <- ggplot(hm_df, aes(ent, cap)) +
    geom_tile(aes(fill = fill_col), colour = 'white', linewidth = 1.2) +
    geom_text(aes(label = label), colour = 'white', fontface = 'plain', size = 3.5) +
    scale_fill_identity(
      guide = guide_legend(title = expression(R[free])),
      breaks = c('#c0392b', '#3a8a3a', '#2c6fb0', '#cccccc'),
      labels = c('1 (single-point*)', '4', '10', 'partial coverage'),
      name   = expression(R[free])
    ) +
    scale_x_discrete(position = 'bottom') +
    scale_y_discrete(limits = rev(caps)) +
    labs(
      title = 'R<sub>free</sub> per cell (20M-token budget)',
      x     = 'Entropy level',
      y     = 'Capacity'
    ) +
    paper_theme(base_size = 8.5) +
    tag_theme +
    theme(legend.position = 'bottom',
          legend.title = element_text(size = 8.5),
          legend.text  = element_text(size = 8.5),
          axis.text    = element_text(size = 8.5),
          axis.text.x  = element_text(size = 8.5),
          panel.grid   = element_blank())

  # Onset scatter: decay_onset vs mem_onset per cell
  idx_df <- data.frame(idx = seq_len(nrow(ons_df)), key = ons_df$key,
                        decay_onset = ons_df$decay_onset, mem_onset = ons_df$mem_onset,
                        coincide = ons_df$coincide)
  idx_long <- tidyr::pivot_longer(idx_df, cols = c('decay_onset','mem_onset'),
                                   names_to = 'type', values_to = 'onset_n')
  idx_long$type <- factor(idx_long$type,
                           levels = c('decay_onset', 'mem_onset'),
                           labels = c('Decay onset (excess ≥ 0.05)', 'Memorization onset (canary gap)'))

  # Vertical offset so decay (orange, filled circle) and mem (purple, open square) are distinguishable
  idx_long$onset_plot <- ifelse(idx_long$type == 'Decay onset (excess ≥ 0.05)',
                                 idx_long$onset_n + 0.55,
                                 idx_long$onset_n - 0.55)

  # Annotation for the one miss — placed at top-left, away from data
  pb <- ggplot(idx_long, aes(idx, onset_plot, colour = type, shape = type)) +
    geom_line(data = idx_long %>% group_by(type) %>% arrange(idx),
              aes(group = type), linewidth = 0.9, alpha = 0.8) +
    geom_point(size = 3) +
    geom_point(data = idx_df[idx_df$coincide, ],
               aes(x = idx, y = decay_onset + 0.55),
               shape = 1, size = 4.2, colour = '#1f9e3a', stroke = 1.0,
               alpha = 0.75, inherit.aes = FALSE) +
    scale_colour_manual(values = c('#d97b29', '#7d3c98'), name = NULL) +
    scale_shape_manual(values = c(16, 0), name = NULL) +   # 16=filled circle, 0=open square
    scale_x_continuous(breaks = seq_len(nrow(ons_df)), labels = ons_df$key) +
    scale_y_continuous(breaks = c(10, 20), limits = c(8.5, 27)) +
    # Annotation for the one miss: placed in top margin away from data lines
    annotate('text', x = 5.8, y = 25.5,
             label = 'small/low:\ndecay n=20\nmem n=10', size = 2.2, colour = 'black',
             family = 'TeX Gyre Termes', hjust = 1, lineheight = 0.9) +
    # Green-ring legend note: ring marks cells where the two onsets coincide
    annotate('point', x = 1.0, y = 23.2,
             shape = 1, size = 4.2, colour = '#1f9e3a', stroke = 1.0,
             alpha = 0.75) +
    annotate('text', x = 1.55, y = 23.2,
             label = sprintf('= onset\ncoincidence (%d/%d)',
                             sum(idx_df$coincide), nrow(idx_df)),
             size = 2.4, colour = 'black', family = 'TeX Gyre Termes', hjust = 0,
             lineheight = 0.95) +
    labs(
      title = 'Decay onset vs. memorization onset',
      x     = NULL,
      y     = 'Onset epoch n = B/U'
    ) +
    paper_theme(base_size = 8.5) +
    tag_theme +
    theme(axis.text.x = element_text(angle = 40, hjust = 1, size = 8.0),
          legend.position = 'bottom',
          legend.text = element_text(size = 8.5))

  # Panel (c): R_free per cell as bars against the 4-10 band
  band_df <- hm_df %>% mutate(cell = paste0(cap, '/', ent))
  band_df$cell <- factor(band_df$cell,
                         levels = sapply(caps, function(c) paste0(c, '/', ents)) |> as.vector())
  pc <- ggplot(band_df, aes(cell, R_free)) +
    annotate('rect', xmin = -Inf, xmax = Inf, ymin = 4, ymax = 10,
             fill = CB$green, alpha = 0.08) +
    geom_col(fill = '#2c6fb0', width = 0.62) +
    geom_text(aes(label = R_free), vjust = -0.4, size = 2.7, colour = '#1a1a1a') +
    scale_y_continuous(expand = expansion(mult = c(0.02, 0.18))) +
    annotate('text', x = 2.8, y = 8.0, label = '4-10 free band', hjust = 0,
             size = 2.6, colour = 'black', family = 'TeX Gyre Termes') +
    labs(title = 'R_free per cell against the band', x = NULL, y = expression(R[free])) +
    paper_theme(base_size = 8.5) +
    theme(axis.text.x = element_text(angle = 40, hjust = 1, size = 8.0))

  # Panel (d): exposure-matched control summary (E1-C, 324 runs): R_free is
  # identical at both plant rates in 9/9 cells; the nominal ordering inverts
  # in 6/9 (this is the headline robustness result for the whole grid)
  e1c <- fromJSON(file.path(root, 'experiments', 'revision2026', 'gpu2026', 'e1c',
                            'e1c_verdict.json'), simplifyVector = FALSE)
  inv_rows <- bind_rows(lapply(names(e1c$paired_cells), function(k) {
    x <- e1c$paired_cells[[k]]
    data.frame(cell = k,
               r4_order = x$r4_order_nominal,
               r1_order = x$r1_order_nominal,
               inverted = isTRUE(x$inverted), stringsAsFactors = FALSE)
  }))
  inv_df <- inv_rows %>%
    mutate(verdict = factor(ifelse(inverted, 'inverts to lags', 'still coincides'),
                            levels = c('still coincides', 'inverts to lags')))
  inv_df$cell <- factor(inv_df$cell,
                        levels = sapply(caps, function(c) paste0(c, '/', ents)) |> as.vector())
  pd <- ggplot(inv_df, aes(cell, 1, fill = verdict)) +
    geom_col(width = 0.62) +
    geom_text(aes(label = ifelse(inverted, 'lags', 'coinc.')),
              angle = 90, hjust = -0.15, size = 2.3, colour = '#1a1a1a') +
    scale_fill_manual(values = c('still coincides' = '#3a8a3a', 'inverts to lags' = '#d97b29'),
                      name = NULL) +

    coord_cartesian(ylim = c(0, 1.28)) +
    labs(title = 'Exposure-matched control (r1 vs r4)', x = NULL, y = NULL) +
    paper_theme(base_size = 8.5) +
    theme(axis.text.x = element_text(angle = 40, hjust = 1, size = 8.0),
          axis.text.y = element_blank(), axis.ticks.y = element_blank(),
          legend.position = 'bottom')

  p <- compose_E1_four_panel(list(pa, pb, pc, pd), 'E1_grid', 7.2, 5.8, root)

  save_both(p, 'E1_grid', w = 7.2, h = 5.8)
}

# ============================================================
# Figure 3: E1_realtext_threshold
#   Data: real-text threshold robustness manifest (3 seeds, 10M WikiText)
#   Two panels: (a) excess val loss curves, (b) R_free by threshold bar chart
# ============================================================
make_E1_realtext_threshold <- function() {
  cat('\n--- E1_realtext_threshold ---\n')
  man_path <- file.path(root, 'experiments','results','figures-redteam', 'redteam_e1_manifest.json')
  man <- fromJSON(man_path, simplifyVector = FALSE)

  # Combine fullattack and redteam items
  items <- c(man$fullattack, man$redteam)
  cat('  Seeds found:', paste(sapply(items, function(x) x$seed), collapse=', '), '\n')

  # Seed colours: 3 seeds
  seed_cols <- c('#2563eb', '#059669', '#7c3aed')

  curve_rows <- list()
  rfree_rows <- list()
  for (i in seq_along(items)) {
    it <- items[[i]]
    sd <- paste0('s', it$seed)
    ns <- as.integer(names(it$excess))
    ex <- as.numeric(unlist(it$excess))
    cat(sprintf('  %s: excess=%s, R_free_by_threshold=%s\n', sd,
                paste(round(ex, 4), collapse=' '),
                paste(names(it$R_free_by_threshold), unlist(it$R_free_by_threshold), sep='=', collapse=' ')))
    for (j in seq_along(ns)) {
      curve_rows[[length(curve_rows)+1]] <- data.frame(
        seed = sd, n = ns[j], excess = ex[j], col_idx = i, stringsAsFactors = FALSE)
    }
    for (thr in names(it$R_free_by_threshold)) {
      rfree_rows[[length(rfree_rows)+1]] <- data.frame(
        seed = sd, threshold = thr,
        R_free = as.integer(it$R_free_by_threshold[[thr]]),
        stringsAsFactors = FALSE)
    }
  }
  curve_df <- bind_rows(curve_rows)
  rfree_df <- bind_rows(rfree_rows)
  # Clamp the n=1 baseline (excess == 0 by construction) to 1e-3 for log-y
  # display only; all other excess values are strictly positive. Underlying
  # values are unchanged.
  curve_df$excess_plot <- pmax(curve_df$excess, 1e-3)
  # Relabel factor levels to two-decimal display strings so the legend reads
  # "0.02"/"0.05"/"0.10" consistently (raw '0.1' key rendered as a clipped "0").
  rfree_df$threshold <- factor(rfree_df$threshold, levels = c('0.02', '0.05', '0.1'),
                               labels = c('0.02', '0.05', '0.10'))

  n_seeds <- length(unique(curve_df$seed))
  col_map  <- setNames(seed_cols[seq_len(n_seeds)], unique(curve_df$seed))

  # Panel (a): threshold labels at right margin, staggered vertically to avoid overlap
  pa <- ggplot(curve_df, aes(n, excess_plot, colour = seed)) +
    geom_hline(yintercept = c(0.02, 0.05, 0.1), linetype = 'dashed',
               linewidth = 0.45, colour = '#9ca3af') +
    # Threshold labels at x=0.85 (left side), staggered; on log-y so the three
    # 0.02/0.05/0.10 reference lines separate cleanly (all excess values > 0).
    annotate('text', x = 0.85, y = 0.0175, label = '0.02', size = 2.7, colour = 'black', hjust = 0) +
    annotate('text', x = 0.85, y = 0.044, label = '0.05', size = 2.7, colour = 'black', hjust = 0) +
    annotate('text', x = 0.85, y = 0.088, label = '0.10', size = 2.7, colour = 'black', hjust = 0) +
    geom_line(linewidth = 0.85) +
    geom_point(size = 2.4) +
    scale_x_log10(breaks = c(1, 2, 4, 10, 20), labels = c('1','2','4','10','20')) +
    scale_y_log10(labels = label_number(accuracy = 0.001)) +
    scale_colour_manual(values = col_map, name = '10M seed') +
    labs(
      title = '10M-token WikiText bytes',
      x     = 'Reuse count n',
      y     = 'Excess validation loss (nats)'
    ) +
    paper_theme() + tag_theme + theme(legend.position = 'top')

  pb <- ggplot(rfree_df, aes(seed, R_free, fill = threshold)) +
    geom_col(position = position_dodge(width = 0.72), width = 0.58,
             colour = '#1f2937', linewidth = 0.2) +
    scale_fill_manual(
      values = c('0.02' = '#93c5fd', '0.05' = '#2563eb', '0.10' = '#1e3a8a'),
      name   = 'Threshold (nats)'
    ) +
    scale_y_continuous(breaks = c(0, 4, 10), limits = c(0, 12)) +
    labs(
      title = 'Threshold sensitivity',
      x     = NULL,
      y     = expression(R[free])
    ) +
    paper_theme() + tag_theme +
    # Tighten the top legend so all three labels (incl. "0.10") fit without
    # the last one clipping at the right panel edge.
    theme(legend.position = 'top',
          legend.key.size = unit(0.32, 'cm'),
          legend.spacing.x = unit(0.12, 'cm'),
          legend.text = element_text(family = 'TeX Gyre Termes', size = 8, margin = margin(r = 4)),
          plot.margin = margin(5.5, 10, 5.5, 6))

  p <- (pa | pb) +
    plot_annotation(tag_levels = 'a', tag_prefix = '(', tag_suffix = ')')
  save_both(p, 'E1_realtext_threshold', w = 5.0, h = 3.4)
}

# ============================================================
# Figure 4: E1_repeat — full cell sweep (all 9 cells with data)
#   Data: repeat-verdict summary JSON
#   Two panels: (a) excess val loss vs n, (b) canary gap vs n
#   Only full-coverage cells plotted
# ============================================================
make_E1_repeat <- function() {
  cat('\n--- E1_repeat ---\n')
  verd <- fromJSON(file.path(root, 'experiments', 'results', 'figures-013', 'repeat_verdicts.json'),
                   simplifyVector = FALSE)
  free_eps <- verd$free_eps_nats

  ex_rows <- list()
  ca_rows <- list()
  for (key in names(verd$cells)) {
    cell <- verd$cells[[key]]
    if (!isTRUE(cell$coverage_full)) next   # only full-coverage
    # The high-capacity row has its own dedicated figure (E1_large_completion);
    # this figure stays scoped to the small- and medium-capacity cells it was
    # built for, so the panel does not duplicate the large row.
    if (startsWith(key, 'large/')) next
    ns <- cell$n_points
    for (n in ns) {
      ex_rows[[length(ex_rows)+1]] <- data.frame(
        cell = key, n = n,
        excess = as.numeric(cell$excess[[as.character(n)]]),
        stringsAsFactors = FALSE)
      ca_val <- cell$canary[[as.character(n)]]
      if (!is.null(ca_val) && !is.na(ca_val)) {
        ca_rows[[length(ca_rows)+1]] <- data.frame(
          cell = key, n = n,
          canary = as.numeric(ca_val),
          stringsAsFactors = FALSE)
      }
    }
  }
  ex_df <- bind_rows(ex_rows)
  ca_df <- bind_rows(ca_rows)

  # Log-y for both panels so the "free" band (small excess / small canary gap)
  # and the 0.05 / 0.10 reference lines are not crushed by the large past-band
  # values (excess up to ~7.86). Clamp zeros/negatives to 1e-3 for log display
  # only; underlying values are unchanged.
  ex_df$excess_plot <- pmax(ex_df$excess, 1e-3)
  ca_df$canary_plot <- pmax(ca_df$canary, 1e-3)

  full_cells <- unique(ex_df$cell)
  cat('  Full-coverage cells:', paste(full_cells, collapse=', '), '\n')

  # Assign shapes and colours from CELL_COLOURS / CELL_SHAPES (subset to what's present)
  col_vals   <- CELL_COLOURS[full_cells]
  shape_vals <- CELL_SHAPES[full_cells]

  pa <- ggplot(ex_df, aes(n, excess_plot, colour = cell, shape = cell)) +
    geom_hline(yintercept = free_eps, colour = CB$grey, linetype = 'dashed', linewidth = 0.45) +
    geom_vline(xintercept = 4, colour = CB$grey, linetype = 'dotted', linewidth = 0.45,
               alpha = 0.8) +
    # Label placed just right of the dotted vertical, near the top of the log range
    annotate('text', x = 4.5, y = 4.0,
             label = expression(R[free] %~~% 4),
             size = 2.5, colour = 'black', hjust = 0) +
    geom_line(linewidth = 0.8, alpha = 0.85) +
    geom_point(size = 2.5, alpha = 0.9) +
    scale_x_log10(breaks = c(1, 2, 4, 10, 20, 40), labels = c('1','2','4','10','20','40')) +
    scale_y_log10(labels = label_number(accuracy = 0.001)) +
    scale_colour_manual(values = col_vals, name = 'cell') +
    scale_shape_manual(values  = shape_vals, name = 'cell') +
    labs(
      title = 'Excess validation loss',
      x     = 'Epoch count n = B/U',
      y     = 'Excess val loss (nats)'
    ) +
    paper_theme() +
    tag_theme +
    theme(legend.position = 'right', legend.text = element_text(size = 8.5),
          legend.key.size = unit(0.6, 'lines'))

  pb <- ggplot(ca_df, aes(n, canary_plot, colour = cell, shape = cell)) +
    geom_hline(yintercept = verd$canary_eps, colour = CB$grey, linetype = 'dashed', linewidth = 0.45) +
    geom_vline(xintercept = 4, colour = CB$grey, linetype = 'dotted', linewidth = 0.45, alpha = 0.8) +
    geom_line(linewidth = 0.8, alpha = 0.85) +
    geom_point(size = 2.5, alpha = 0.9) +
    scale_x_log10(breaks = c(1, 2, 4, 10, 20, 40), labels = c('1','2','4','10','20','40')) +
    scale_y_log10(labels = label_number(accuracy = 0.001)) +
    scale_colour_manual(values = col_vals, name = 'cell') +
    scale_shape_manual(values  = shape_vals, name = 'cell') +
    labs(
      title = 'Canary memorization gap',
      x     = 'Epoch count n = B/U',
      y     = 'Canary memorization gap'
    ) +
    paper_theme() +
    tag_theme +
    theme(legend.position = 'right', legend.text = element_text(size = 8.5),
          legend.key.size = unit(0.6, 'lines'))

  # (c) canary gap at each cell's own decay-onset rung: a >=0.10-nat
  #     memorization signal is already present at or before decay onset
  gap_rows <- list()
  for (key in names(verd$cells)) {
    cell <- verd$cells[[key]]
    if (!isTRUE(cell$coverage_full)) next
    if (startsWith(key, 'large/')) next
    don <- cell$decay_onset
    gv <- cell$canary[[as.character(don)]]
    if (is.null(gv)) next
    gap_rows[[length(gap_rows)+1]] <- data.frame(
      cell = key, gap = as.numeric(gv), stringsAsFactors = FALSE)
  }
  gap_df <- bind_rows(gap_rows)
  gap_df$cell <- factor(gap_df$cell, levels = sort(gap_df$cell))
  pc <- ggplot(gap_df, aes(cell, gap)) +
    geom_hline(yintercept = verd$canary_eps, colour = CB$grey, linetype = 'dashed',
               linewidth = 0.45) +
    geom_col(fill = CB$vermillion, width = 0.6) +
    geom_text(aes(label = sprintf('%.2f', gap)), vjust = -0.4, size = 2.6,
              colour = '#1a1a1a') +
    labs(title = 'Canary gap at decay onset (per cell)', x = NULL,
         y = 'Canary gap (nats)') +
    paper_theme() +
    theme(axis.text.x = element_text(angle = 40, hjust = 1, size = 7.5))

  # (d) R_free per cell with the 4-10 band
  rf_rows <- list()
  for (key in names(verd$cells)) {
    cell <- verd$cells[[key]]
    if (!isTRUE(cell$coverage_full)) next
    if (startsWith(key, 'large/')) next
    rf_rows[[length(rf_rows)+1]] <- data.frame(cell = key, R_free = cell$R_free_epochs)
  }
  rf_df <- bind_rows(rf_rows)
  rf_df$cell <- factor(rf_df$cell, levels = sort(rf_df$cell))
  pd <- ggplot(rf_df, aes(cell, R_free)) +
    annotate('rect', xmin = -Inf, xmax = Inf, ymin = 4, ymax = 10,
             fill = CB$green, alpha = 0.10) +
    geom_col(fill = '#2c6fb0', width = 0.6) +
    geom_text(aes(label = R_free), vjust = -0.4, size = 2.7, colour = '#1a1a1a') +
    labs(title = 'R_free per cell (band shaded)', x = NULL, y = expression(R[free])) +
    paper_theme() +
    theme(axis.text.x = element_text(angle = 40, hjust = 1, size = 7.5))

  # Strip mode: patchwork tags at npc y=0.98 collide with the top y-tick
  # label ("10.000") once the title band is stripped away. Route the tags
  # through the title slot instead — the stripper keeps a leading "(a)" and
  # the title row gives it its own band. Canonical output is unchanged.
  p <- compose_E1_four_panel(list(pa, pb, pc, pd), 'E1_repeat', 7.2, 5.4, root)
  save_both(p, 'E1_repeat', w = 7.2, h = 5.4)
}

# ============================================================
# Figure 5: E1_scale — real-text (WikiText byte) repetition law (50M budget, 2 seeds)
#   Data: real-text 50M-token budget results
#   Single panel: excess val loss vs n for both seeds + threshold line
# ============================================================
make_E1_scale <- function() {
  cat('\n--- E1_scale ---\n')
  specs <- list(
    list(name = 'wiki',      dir = file.path(root, 'experiments', 'results', 'repeated_data_realtext'),
         pat = 'med_b50M_s.*\\.json'),
    list(name = 'code_raw',  dir = file.path(root, 'experiments', 'results', 'repeated_data_realtext_code'),
         pat = 'med_b50M_s.*\\.json'),
    list(name = 'code_dedup', dir = file.path(root, 'experiments', 'results', 'repeated_data_realtext_shards'),
         pat = 'code_v2_shard.*\\.json'))
  rows_list <- list()
  for (sp in specs) {
    files <- sort(list.files(sp$dir, pattern = sp$pat, full.names = TRUE))
    if (length(files) == 0) stop('No realtext data files found in ', sp$dir)
    for (f in files) {
      d <- fromJSON(f, simplifyVector = FALSE)
      ns  <- as.integer(names(d$rows))
      ex  <- sapply(d$rows, function(r) as.numeric(r$excess))
      run_label <- if (grepl('shard', f)) sub('.*_shard(\\d).*', 'corpus draw \\1', f) else
        sub('_s', 'seed ', regmatches(f, regexpr('_s(\\d+)', f)))
      cat(sprintf('  %s %s: R_free=%s, excess=%s\n', sp$name, run_label, d$R_free,
                  paste(round(ex, 4), collapse=' ')))
      for (j in seq_along(ns)) {
        rows_list[[length(rows_list)+1]] <- data.frame(
          corpus = sp$name, seed = run_label, n = ns[j], excess = ex[j],
          stringsAsFactors = FALSE)
      }
    }
  }
  df <- bind_rows(rows_list)
  df$corpus <- factor(df$corpus, levels = c('wiki', 'code_raw', 'code_dedup'),
                      labels = c('WikiText',
                                 'Python raw',
                                 'Python dedup'))
  # Series styling: sorted labels are the three "corpus draw" runs first, then
  # the five "seed" runs. Corpus draws (facet c) and seeds (facets a/b) never
  # share a panel, so hues may repeat ACROSS the groups but must be separable
  # WITHIN each. The former palette ended in '#7d3c98'/'#CC79A7' (purple/pink),
  # a pair too close at print size — replaced with well-separated hues, and
  # every series additionally gets its own linetype + point shape so adjacent
  # colours stay distinguishable in grayscale/print.
  seed_cols <- c(CB$blue, CB$vermillion, CB$green, CB$orange, CB$skyblue,
                 '#7d3c98', '#555555', CB$black)
  seed_ltys <- rep(c('solid', 'dashed', 'dotted'), length.out = length(seed_cols))
  seed_shps <- rep(c(16, 17, 15), length.out = length(seed_cols))
  seeds     <- sort(unique(df$seed))
  if (length(seeds) > length(seed_cols)) stop('palette too small for run labels')
  col_map   <- setNames(seed_cols[seq_along(seeds)], seeds)
  lty_map   <- setNames(seed_ltys[seq_along(seeds)], seeds)
  shp_map   <- setNames(seed_shps[seq_along(seeds)], seeds)
  all_ns    <- sort(unique(df$n))

  # Log-y so the load-bearing "free" region and the 0.05 threshold separate
  # from the large n=40 values. Clamp rare negative excesses (n=2 sampling
  # dips below fresh) to 1e-3 for log display only.
  df$excess_plot <- pmax(df$excess, 1e-3)

  # per-facet last-free grid point: n=4 wiki, n=2 as-collected code, n=4 dedup
  vlines <- data.frame(corpus = levels(df$corpus), xint = c(4, 2, 4))
  vlines$corpus <- factor(vlines$corpus, levels = levels(df$corpus))

  p <- ggplot(df, aes(n, excess_plot, colour = seed, linetype = seed, shape = seed)) +
    geom_hline(yintercept = 0.05, colour = 'black', linetype = 'dotted',
               linewidth = 0.45, alpha = 0.8) +
    annotate('text', x = max(all_ns) * 0.68, y = 0.085,
             label = '0.05 nats', size = 2.4, colour = 'black', hjust = 1) +
    geom_vline(data = vlines, aes(xintercept = xint), colour = CB$grey,
               linetype = 'dashed', linewidth = 0.45, alpha = 0.7,
               inherit.aes = FALSE) +
    geom_line(linewidth = 0.8, alpha = 0.9) +
    geom_point(size = 2.2, alpha = 0.9) +
    facet_wrap(~ corpus, nrow = 1) +
    scale_x_log10(breaks = c(1, 4, 10, 40)) +
    scale_y_log10(labels = label_number(accuracy = 0.001)) +
    scale_colour_manual(values = col_map, name = NULL) +
    scale_linetype_manual(values = lty_map, name = NULL) +
    scale_shape_manual(values = shp_map, name = NULL) +
    labs(
      title = 'Real-byte excess loss vs repeats (50M-token budget)',
      x = 'Epochs n (= budget / unique tokens)',
      y = 'Excess val loss vs fresh (nats)'
    ) +
    paper_theme() +
    # 8.5pt legend/axis type matches the sibling figures (the old 8pt legend at
    # a 7.0in design width rendered visibly smaller once scaled into the text
    # block); key spacing + label margin keep markers off the next label, and a
    # wider key shows the full dash pattern.
    theme(legend.position = 'top',
          legend.text = element_text(size = 8.5, margin = margin(l = 4, r = 7)),
          legend.key.spacing.x = unit(6, 'pt'),
          legend.key.width = unit(1.2, 'lines'))

  # Panel (d): threshold robustness (merged from E1_realtext_threshold):
  # R_free by threshold for the three 10M WikiText audit seeds — the
  # real-text band is threshold-robust below the declared 0.05 nats
  man_path <- file.path(root, 'experiments','results','figures-redteam',
                        'redteam_e1_manifest.json')
  man <- fromJSON(man_path, simplifyVector = FALSE)
  items <- c(man$fullattack, man$redteam)
  rfree_rows <- list()
  for (i in seq_along(items)) {
    it <- items[[i]]
    sd <- paste0('s', it$seed)
    for (thr in names(it$R_free_by_threshold)) {
      rfree_rows[[length(rfree_rows)+1]] <- data.frame(
        seed = sd, threshold = thr,
        R_free = as.integer(it$R_free_by_threshold[[thr]]),
        stringsAsFactors = FALSE)
    }
  }
  rfree_df <- bind_rows(rfree_rows)
  rfree_df$threshold <- factor(rfree_df$threshold, levels = c('0.02', '0.05', '0.1'),
                               labels = c('0.02', '0.05', '0.10'))
  pd <- ggplot(rfree_df, aes(seed, R_free, fill = threshold)) +
    geom_col(position = position_dodge(width = 0.72), width = 0.58,
             colour = '#1f2937', linewidth = 0.2) +
    scale_fill_manual(
      values = c('0.02' = '#93c5fd', '0.05' = '#2563eb', '0.10' = '#1e3a8a'),
      name   = 'Threshold (nats)'
    ) +
    scale_y_continuous(breaks = c(0, 4, 10), limits = c(0, 12)) +
    labs(title = '(d) Threshold robustness (10M audit seeds)',
         x = NULL, y = expression(R[free])) +
    paper_theme() +
    theme(legend.position = 'top',
          legend.key.size = unit(0.32, 'cm'),
          legend.text = element_text(family = 'TeX Gyre Termes', size = 8))

  # Panel (b): real-text onset (last free n per corpus, the vlines data)
  onset_df <- data.frame(corpus = levels(df$corpus), R_free = c(4, 2, 4))
  onset_df$corpus <- factor(onset_df$corpus, levels = levels(df$corpus))
  pb <- ggplot(onset_df, aes(corpus, R_free)) +
    geom_col(fill = CB$blue, width = 0.55) +
    geom_text(aes(label = R_free), vjust = -0.4, size = 2.8, colour = '#1a1a1a') +
    scale_y_continuous(breaks = c(0, 2, 4), limits = c(0, 5)) +
    labs(title = 'Real-text onset (last free n)',
         x = NULL, y = expression(R[free])) +
    paper_theme() +
    theme(axis.text.x = element_text(size = 6.8, angle = 15, hjust = 1))

  # Panel (c): seed variation of R_free within each corpus (from the same df)
  rf_seed <- df %>%
    group_by(corpus, seed) %>%
    summarise(R_free = max(n[excess < 0.05], na.rm = TRUE), .groups = 'drop') %>%
    filter(is.finite(R_free))
  pc <- ggplot(rf_seed, aes(corpus, R_free, colour = corpus)) +
    stat_summary(fun = median, geom = 'crossbar', width = 0.45, colour = '#1a1a1a') +
    geom_point(position = position_jitter(width = 0.09, height = 0, seed = 41),
               size = 1.8, alpha = 0.85, show.legend = FALSE) +
    scale_colour_manual(values = c('WikiText' = CB$blue,
                                   'Python raw' = CB$orange,
                                   'Python dedup' = CB$green), guide = 'none') +
    scale_y_continuous(breaks = c(0, 2, 4), limits = c(0, 5)) +
    labs(title = 'Seed variation of R_free',
         x = NULL, y = expression(R[free])) +
    paper_theme() +
    theme(axis.text.x = element_text(size = 6.8, angle = 15, hjust = 1))

  pd <- pd + labs(title = 'Transfer boundary by threshold (10M audit seeds)')

  p_all <- compose_E1_four_panel(list(p, pb, pc, pd), 'E1_scale', 7.2, 5.4, root)
  save_both(p_all, 'E1_scale', w = 7.2, h = 5.4)
}

# ============================================================
# Run all 5 figures
# ============================================================
cat('=== make_E1_figs_r.R: generating 5 E1 figures ===\n')
cat('Working directory:', getwd(), '\n')
cat('fig dir:', figdir, '\n')
cat('svg dir:', evdir, '\n\n')

make_E1_case()
make_E1_grid()
make_E1_realtext_threshold()
make_E1_repeat()
make_E1_scale()

# --- Verify all 5 PNGs were written and are non-trivial ---
cat('\n=== Verification ===\n')
expected <- c('E1_case', 'E1_grid', 'E1_realtext_threshold', 'E1_repeat', 'E1_scale')
all_ok <- TRUE
for (nm in expected) {
  fp <- file.path(figdir, paste0(nm, '.png'))
  sz <- if (file.exists(fp)) file.info(fp)$size else 0L
  status <- if (sz > 10000L) 'OK' else 'MISSING/TINY'
  cat(sprintf('  %-40s %s  (%d bytes)\n', paste0(nm, '.png'), status, sz))
  if (sz <= 10000L) all_ok <- FALSE
}
if (all_ok) {
  cat('\nAll 5 E1 figures written successfully.\n')
} else {
  stop('One or more figures missing or too small — check output above.')
}
