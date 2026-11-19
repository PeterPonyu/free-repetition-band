#!/usr/bin/env Rscript
# make_E1_new_figs_r.R — NEW standalone E1 figures from previously-unused data.
#
# These figures surface measured-but-unplotted data for Paper E1:
#   E1-1  Large-capacity completion: excess-loss + canary-onset vs n for the now
#         FULLY-COVERED large-capacity row (low/med/high, n in {1,2,4,10,20,40}).
#         This row was previously partial; the completed sweep overturns the
#         manuscript's stated large-capacity limitation.
#   E1-2  R_free vs model scale (param count), with the 4-10 free band shaded and
#         the large-scale ~4-epoch anchor (Muennighoff et al.) marked; small-cap
#         per-seed spread at the n=10 decision point folded in as scatter.
#   E1-3  Within-run divergence trajectory: train vs validation loss over epochs
#         for a free cell (n=4) and a damaged cell (n=20), showing WHEN within a
#         run repetition turns harmful.
#
# NUMBERS RED LINE: every plotted value is computed here directly from the raw
# per-run *.jsonl logs (median over seeds), replicating analyze_repeat.py:
#   excess(n)   = median(final_val_loss at n) - median(final_val_loss at n=1)
#   R_free      = largest n with median excess < 0.05 nats
#   decay_onset = smallest n>1 with median excess >= 0.05
#   mem_onset   = smallest n with median final_canary_gap >= 0.10
#
# Output: papers/figs/<name>.png (300 dpi ragg, 6.5in wide) + evidence_r/<name>.svg

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
`%||%` <- function(x, y) if (is.null(x) || length(x) == 0) y else x


# --- paths ---
root   <- normalizePath(file.path(getwd()))
figdir <- file.path(root, 'papers', 'figs')
evdir  <- file.path(figdir, 'evidence_r')
resdir <- file.path(root, 'experiments', 'results')
dir.create(evdir, showWarnings = FALSE, recursive = TRUE)
source(file.path(figdir, 'fig_pipeline.R'))
source(file.path(figdir, 'E1_panel_contract.R'))

# Raw-log source dirs (same set analyze_repeat.py merges, plus the large dir that
# completes the large-capacity row).
SRC_DIRS <- c(
  file.path(resdir, 'repeated_data'),
  file.path(resdir, 'repeated_data_ultragoal_seed_audit'),
  file.path(resdir, 'repeated_data_ultragoal_large')
)

BUDGET     <- 20000000
FREE_EPS   <- 0.05    # nats; "nearly free" excess threshold
CANARY_EPS <- 0.10    # canary-gap memorization threshold
N_GRID     <- c(1, 2, 4, 10, 20, 40)

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

# --- professional paper theme (matches make_E1_figs_r.R) ---
paper_theme <- function(base_size = 9) {
  theme_minimal(base_size = base_size, base_family = 'TeX Gyre Termes') +
    theme(
      panel.grid.minor   = element_blank(),
      panel.grid.major.x = element_blank(),
      panel.grid.major.y = element_line(linewidth = 0.25, colour = '#d9dde3'),
      axis.title  = element_text(family = 'TeX Gyre Termes', colour = '#1a202c', size = 9),
      axis.text   = element_text(family = 'TeX Gyre Termes', colour = '#2d3748', size = 8.5),
      plot.title  = element_text(family = 'TeX Gyre Termes', face = 'plain', colour = '#111827', size = 10),
      legend.position = 'right',
      legend.title    = element_text(family = 'TeX Gyre Termes', size = 8.5),
      legend.text     = element_text(family = 'TeX Gyre Termes', size = 8.5),
      strip.text      = element_text(family = 'TeX Gyre Termes', face = 'plain', colour = '#1a202c'),
      plot.margin     = margin(5.5, 6, 5.5, 6)
    )
}
tag_theme <- theme(
  plot.tag          = element_text(face = 'bold', size = 11),
  plot.tag.position = c(0.02, 0.98)
)

save_both <- function(p, name, w = 6.5, h = 4.0) {
  pngp <- file.path(figdir, paste0(name, '.png'))
  svgp <- file.path(evdir,  paste0(name, '.svg'))
  ragg::agg_png(pngp, width = w, height = h, units = 'in', res = 300, scaling = 1)
  print(p)
  dev.off()
  svglite::svglite(svgp, width = w, height = h)
  print(p)
  dev.off()
  emit_vector(p, name, w, h)
  cat('saved', pngp, '\n      ', svgp, '\n')
}

# ============================================================
# Raw-log loaders (numbers red line)
# ============================================================

# Read the trailing _summary record of one run file.
read_summary <- function(path) {
  ls <- readLines(path, warn = FALSE)
  ls <- ls[nzchar(trimws(ls))]
  if (length(ls) == 0) return(NULL)
  rec <- tryCatch(fromJSON(ls[length(ls)], simplifyVector = TRUE), error = function(e) NULL)
  if (is.null(rec) || is.null(rec[['_summary']])) return(NULL)
  rec[['_summary']]
}

# Read all per-epoch records of one run file (drops _meta / _summary lines).
read_epochs <- function(path) {
  ls <- readLines(path, warn = FALSE)
  ls <- ls[nzchar(trimws(ls))]
  rows <- list()
  for (l in ls) {
    d <- tryCatch(fromJSON(l, simplifyVector = TRUE), error = function(e) NULL)
    if (!is.null(d) && !is.null(d$epoch)) rows[[length(rows) + 1]] <- d
  }
  if (length(rows) == 0) return(NULL)
  bind_rows(lapply(rows, function(d) data.frame(
    epoch      = d$epoch,
    train_loss = d$train_loss,
    val_loss   = d$val_loss,
    fresh_loss = if (!is.null(d$fresh_loss)) d$fresh_loss else NA_real_,
    canary_gap = if (!is.null(d$canary_gap)) d$canary_gap else NA_real_
  )))
}

# Collect every run summary across the source dirs (skipping probe_* helpers).
load_all_summaries <- function() {
  out <- list()
  for (d in SRC_DIRS) {
    fs <- list.files(d, pattern = '\\.jsonl$', full.names = TRUE)
    fs <- fs[!grepl('^probe_', basename(fs))]
    for (f in fs) {
      s <- read_summary(f)
      if (is.null(s)) next
      out[[length(out) + 1]] <- data.frame(
        file        = basename(f),
        capacity    = s$capacity,
        entropy     = s$entropy_level,
        budget      = s$total_budget,
        n_epochs    = s$n_epochs,
        n_params    = if (!is.null(s$n_params)) s$n_params else NA_real_,
        val_loss    = s$final_val_loss,
        canary_gap  = if (!is.null(s$final_canary_gap)) s$final_canary_gap else NA_real_,
        stringsAsFactors = FALSE
      )
    }
  }
  bind_rows(out)
}

# Per-cell curve: median val / canary at each n, excess vs n=1, R_free & onsets.
cell_verdict <- function(summ, cap, ent) {
  s <- summ %>% filter(budget == BUDGET, capacity == cap, entropy == ent)
  if (nrow(s) == 0) return(NULL)
  agg <- s %>% group_by(n_epochs) %>%
    summarise(val = median(val_loss),
              canary = median(canary_gap, na.rm = TRUE),
              nseed = dplyr::n(), .groups = 'drop') %>%
    arrange(n_epochs)
  if (!(1 %in% agg$n_epochs)) return(NULL)
  fresh <- agg$val[agg$n_epochs == 1]
  agg$excess <- agg$val - fresh
  free_ns <- agg$n_epochs[agg$excess < FREE_EPS]
  R_free  <- if (length(free_ns)) max(free_ns) else 1
  dec     <- agg$n_epochs[agg$n_epochs > 1 & agg$excess >= FREE_EPS]
  decay_onset <- if (length(dec)) min(dec) else NA_integer_
  mem     <- agg$n_epochs[!is.na(agg$canary) & agg$canary >= CANARY_EPS]
  mem_onset <- if (length(mem)) min(mem) else NA_integer_
  list(cell = paste0(cap, '/', ent), fresh = fresh, agg = agg,
       R_free = R_free, decay_onset = decay_onset, mem_onset = mem_onset,
       coverage_full = setequal(agg$n_epochs, N_GRID),
       n_params = median(s$n_params, na.rm = TRUE))
}

# ============================================================
# E1-4 : xl/xxl capacity extension (2026-07-10; sec:capxl)
#   Data: experiments/results/repeated_data_capxl/*.jsonl (44 runs).
#   No fresh n=1 arm in this grid: excess is referenced to the n=2 cell
#   (main-grid median excess(2) <= 0.008 nats bounds the bias). Every value
#   computed here from the raw jsonls (median over seeds), numbers red line.
# ============================================================
make_E1_capxl <- function() {
  cat('\n--- E1-4 xl/xxl capacity extension ---\n')
  src <- file.path(resdir, 'repeated_data_capxl')
  fs <- list.files(src, pattern = '\\.jsonl$', full.names = TRUE)
  stopifnot(length(fs) == 44)
  rows <- list()
  for (f in fs) {
    s <- read_summary(f)
    # capxl files end with the _summary line itself (no trailing meta), but be
    # defensive: scan all lines if the tail read misses it.
    if (is.null(s)) {
      for (l in rev(readLines(f, warn = FALSE))) {
        d <- tryCatch(fromJSON(l, simplifyVector = TRUE), error = function(e) NULL)
        if (!is.null(d) && !is.null(d[['_summary']])) { s <- d[['_summary']]; break }
      }
    }
    stopifnot(!is.null(s))
    rows[[length(rows) + 1]] <- data.frame(
      capacity = s$capacity, entropy = s$entropy_level, n_epochs = s$n_epochs,
      val_loss = s$final_val_loss, canary_gap = s$final_canary_gap)
  }
  d <- bind_rows(rows) %>%
    mutate(cell = paste0(capacity, '/', entropy)) %>%
    group_by(cell, n_epochs) %>%
    summarise(val = median(val_loss), canary = median(canary_gap),
              nseed = dplyr::n(), .groups = 'drop') %>%
    arrange(cell, n_epochs)
  d <- d %>% group_by(cell) %>%
    mutate(excess = val - val[n_epochs == 2]) %>% ungroup()
  for (cl in unique(d$cell)) {
    dd <- d %>% filter(cell == cl)
    cat(sprintf('  %-8s :: %s\n', cl,
        paste(sprintf('n=%d exc=%+.4f cg=%.3f(x%d)', dd$n_epochs, dd$excess, dd$canary, dd$nseed), collapse = '  ')))
  }
  CELLS <- c('xl/low', 'xl/med', 'xl/high', 'xxl/med')
  CELL_LAB <- c('xl/low' = 'xl / low entropy', 'xl/med' = 'xl / medium',
                'xl/high' = 'xl / high', 'xxl/med' = 'xxl / medium')
  CELL_COL <- c(CB$blue, CB$vermillion, CB$green, CB$purple); names(CELL_COL) <- CELL_LAB[CELLS]
  CELL_SHP <- c(16, 15, 17, 18); names(CELL_SHP) <- CELL_LAB[CELLS]
  d$cell <- factor(CELL_LAB[d$cell], levels = CELL_LAB[CELLS])
  NGRID2 <- c(2, 4, 10, 20)
  d$excess_plot <- pmax(d$excess, 1e-3)
  d$canary_plot <- pmax(d$canary, 1e-3)

  # Use compact labels and extra bottom room so the four categories remain
  # separable in the composite at paper width.
  axis_cell_theme <- theme(axis.text.x = element_text(size = 6.8, angle = 35, hjust = 1),
                           plot.margin = margin(5.5, 6, 18, 6))

  pa <- ggplot(d, aes(n_epochs, excess_plot, colour = cell, shape = cell)) +
    annotate('rect', xmin = 1.8, xmax = 4 * 1.08, ymin = 1e-3, ymax = 12,
             fill = CB$green, alpha = 0.07) +
    geom_hline(yintercept = FREE_EPS, colour = CB$grey, linetype = 'dashed', linewidth = 0.45) +
    geom_vline(xintercept = 4, colour = CB$green, linetype = 'dotted', linewidth = 0.45) +
    geom_line(linewidth = 0.85, alpha = 0.9) +
    geom_point(size = 2.6, alpha = 0.95) +
    annotate('text', x = 1.85, y = FREE_EPS * 2.0,
             label = '0.05-nat threshold', size = 2.7, colour = 'black', hjust = 0) +
    scale_x_log10(breaks = NGRID2, labels = as.character(NGRID2)) +
    scale_y_log10(labels = label_number(accuracy = 0.001)) +
    scale_colour_manual(values = CELL_COL, name = NULL) +
    scale_shape_manual(values = CELL_SHP, name = NULL) +
    labs(title = 'Excess validation loss',
         x = 'Epoch count n = B/U', y = 'Excess val loss (nats)') +
    paper_theme() + tag_theme + axis_cell_theme +
    theme(legend.position = 'top', legend.key.size = unit(0.7, 'lines'))

  pb <- ggplot(d, aes(n_epochs, canary_plot, colour = cell, shape = cell)) +
    geom_hline(yintercept = CANARY_EPS, colour = CB$grey, linetype = 'dashed', linewidth = 0.45) +
    geom_vline(xintercept = 4, colour = CB$green, linetype = 'dotted', linewidth = 0.45) +
    geom_line(linewidth = 0.85, alpha = 0.9) +
    geom_point(size = 2.6, alpha = 0.95) +
    annotate('text', x = 1.85, y = CANARY_EPS * 1.35,
             label = '0.10-nat threshold', size = 2.7, colour = 'black', hjust = 0) +
    scale_x_log10(breaks = NGRID2, labels = as.character(NGRID2)) +
    scale_y_log10(labels = label_number(accuracy = 0.001)) +
    scale_colour_manual(values = CELL_COL, name = NULL) +
    scale_shape_manual(values = CELL_SHP, name = NULL) +
    labs(title = 'Canary memorization gap',
         x = 'Epoch count n = B/U', y = 'Canary memorization gap (nats)') +
    paper_theme() + tag_theme + axis_cell_theme +
    theme(legend.position = 'top', legend.key.size = unit(0.7, 'lines'))

  # (c) R_free per cell against the 4-10 band (computed from the same medians)
  rf <- d %>% group_by(cell) %>%
    summarise(R_free = max(n_epochs[excess < FREE_EPS]), .groups = 'drop')
  pc <- ggplot(rf, aes(cell, R_free)) +
    annotate('rect', xmin = -Inf, xmax = Inf, ymin = 4, ymax = 10,
             fill = CB$green, alpha = 0.10) +
    geom_col(fill = '#2c6fb0', width = 0.55) +
    geom_text(aes(label = R_free), vjust = -0.4, size = 2.8, colour = '#1a1a1a') +
    labs(title = 'R_free per xl/xxl cell', x = NULL, y = expression(R[free])) +
    paper_theme() + tag_theme + axis_cell_theme

  # (d) onset ordering per cell: first n with canary gap >= 0.10 vs first n
  #     with excess >= 0.05 (xl/high's canary leads at n=4, matching the
  #     lead-or-coincide ordering of the main grid)
  ons <- d %>% group_by(cell) %>%
    summarise(decay_on = min(n_epochs[excess >= FREE_EPS]),
              mem_on  = min(n_epochs[canary >= CANARY_EPS]), .groups = 'drop') %>%
    mutate(verdict = ifelse(mem_on <= decay_on, 'leads/coincides', 'lags'))
  ons_long <- rbind(
    ons %>% transmute(cell, qty = 'decay onset', n = decay_on),
    ons %>% transmute(cell, qty = 'memorization onset', n = mem_on))
  pd <- ggplot(ons_long, aes(cell, n, colour = qty, shape = qty, group = qty)) +
    geom_line(linewidth = 0.8, colour = '#666666') +
    geom_point(size = 2.8) +
    scale_colour_manual(values = c('decay onset' = CB$blue, 'memorization onset' = CB$vermillion),
                        name = NULL) +
    scale_shape_manual(values = c('decay onset' = 16, 'memorization onset' = 17),
                       name = NULL) +
    labs(title = 'Onset ordering', x = NULL, y = 'Onset epoch n') +
    paper_theme() + tag_theme + axis_cell_theme +
    theme(legend.position = 'top')

  p <- compose_E1_four_panel(list(pa, pb, pc, pd), 'E1_capxl', 7.2, 5.4, root)
  save_both(p, 'E1_capxl', w = 7.2, h = 5.4)
}

# ============================================================
# E1-1 : Large-capacity completion (TOP, main body)
# ============================================================
make_E1_large_completion <- function(summ) {
  cat('\n--- E1-1 large-capacity completion ---\n')
  ents <- c('low', 'med', 'high')
  ent_lab <- c(low = 'low entropy', med = 'medium entropy', high = 'high entropy')
  ent_col <- c('low' = CB$blue, 'med' = CB$vermillion, 'high' = CB$green)
  ent_shp <- c('low' = 16, 'med' = 15, 'high' = 17)

  ex_rows <- list(); ca_rows <- list()
  for (ent in ents) {
    v <- cell_verdict(summ, 'large', ent)
    if (is.null(v)) stop('missing large/', ent)
    a <- v$agg
    cat(sprintf('  large/%-4s fresh=%.4f R_free=%d decay_onset=%s mem_onset=%s full=%s\n',
                ent, v$fresh, v$R_free, v$decay_onset, v$mem_onset, v$coverage_full))
    for (i in seq_len(nrow(a))) {
      cat(sprintf('     n=%2d nseed=%d val=%.4f excess=%+.4f canary=%.4f\n',
                  a$n_epochs[i], a$nseed[i], a$val[i], a$excess[i], a$canary[i]))
      ex_rows[[length(ex_rows)+1]] <- data.frame(
        ent = ent, n = a$n_epochs[i], excess = a$excess[i])
      ca_rows[[length(ca_rows)+1]] <- data.frame(
        ent = ent, n = a$n_epochs[i], canary = a$canary[i])
    }
  }
  ex <- bind_rows(ex_rows); ca <- bind_rows(ca_rows)
  ex$ent <- factor(ex$ent, levels = ents, labels = ent_lab[ents])
  ca$ent <- factor(ca$ent, levels = ents, labels = ent_lab[ents])
  names(ent_col) <- ent_lab[names(ent_col)]
  names(ent_shp) <- ent_lab[names(ent_shp)]

  # Clamp for log-y; smallest positive excess kept visible.
  ex$excess_plot <- pmax(ex$excess, 1e-3)
  # Same log-y clamp for the canary panel (matches E1_repeat panel (b)) so the
  # 0.10 onset line and small canary gaps are readable; display only, the
  # underlying canary-gap values are unchanged.
  ca$canary_plot <- pmax(ca$canary, 1e-3)

  pa <- ggplot(ex, aes(n, excess_plot, colour = ent, shape = ent)) +
    annotate('rect', xmin = 0.85, xmax = 4 * 1.08, ymin = 1e-3, ymax = 12,
             fill = CB$green, alpha = 0.07) +
    geom_hline(yintercept = FREE_EPS, colour = CB$grey, linetype = 'dashed', linewidth = 0.45) +
    geom_vline(xintercept = 4, colour = CB$green, linetype = 'dotted', linewidth = 0.45) +
    geom_line(linewidth = 0.85, alpha = 0.9) +
    geom_point(size = 2.6, alpha = 0.95) +
    annotate('text', x = 0.88, y = FREE_EPS * 2.0,
             label = '0.05-nat threshold', size = 2.7, colour = 'black', hjust = 0) +
    annotate('text', x = 3.6, y = 6.5,
             label = 'free band', size = 2.7, colour = 'black', hjust = 1) +
    scale_x_log10(breaks = N_GRID, labels = as.character(N_GRID)) +
    scale_y_log10(labels = label_number(accuracy = 0.001)) +
    scale_colour_manual(values = ent_col, name = NULL) +
    scale_shape_manual(values = ent_shp, name = NULL) +
    labs(title = 'Excess val. loss (high-capacity)',
         x = 'Epoch count n = B/U',
         y = 'Excess val loss (nats)') +
    paper_theme() + tag_theme +
    theme(legend.position = 'top', legend.key.size = unit(0.7, 'lines'))

  pb <- ggplot(ca, aes(n, canary_plot, colour = ent, shape = ent)) +
    geom_hline(yintercept = CANARY_EPS, colour = CB$grey, linetype = 'dashed', linewidth = 0.45) +
    geom_vline(xintercept = 4, colour = CB$green, linetype = 'dotted', linewidth = 0.45) +
    geom_line(linewidth = 0.85, alpha = 0.9) +
    geom_point(size = 2.6, alpha = 0.95) +
    annotate('text', x = 0.88, y = CANARY_EPS * 1.25,
             label = '0.10-nat threshold', size = 2.7, colour = 'black', hjust = 0) +
    scale_x_log10(breaks = N_GRID, labels = as.character(N_GRID)) +
    scale_y_log10(labels = label_number(accuracy = 0.001)) +
    scale_colour_manual(values = ent_col, name = NULL) +
    scale_shape_manual(values = ent_shp, name = NULL) +
    labs(title = 'Copied-canary memorization gap',
         x = 'Epoch count n = B/U',
         y = 'Canary memorization gap (nats)') +
    paper_theme() + tag_theme +
    theme(legend.position = 'top', legend.key.size = unit(0.7, 'lines'))

  # (c) R_free per entropy cell with the band (from the cell verdicts)
  rf <- bind_rows(lapply(ents, function(ent) {
    v <- cell_verdict(summ, 'large', ent)
    data.frame(ent = ent_lab[[ent]], R_free = v$R_free, stringsAsFactors = FALSE)
  }))
  rf$ent <- factor(rf$ent, levels = ent_lab[ents])
  pc <- ggplot(rf, aes(ent, R_free)) +
    annotate('rect', xmin = -Inf, xmax = Inf, ymin = 4, ymax = 10,
             fill = CB$green, alpha = 0.10) +
    geom_col(fill = '#2c6fb0', width = 0.55) +
    geom_text(aes(label = R_free), vjust = -0.4, size = 2.8, colour = '#1a1a1a') +
    labs(title = 'R_free per large-capacity cell', x = NULL, y = expression(R[free])) +
    paper_theme() + tag_theme +
    theme(axis.text.x = element_text(size = 7.5, angle = 20, hjust = 1))

  # (d) onset coincidence per cell (decay vs memorization onset from verdicts)
  ons <- bind_rows(lapply(ents, function(ent) {
    v <- cell_verdict(summ, 'large', ent)
    rbind(data.frame(ent = ent_lab[[ent]], qty = 'decay onset',
                     n = as.numeric(v$decay_onset)),
          data.frame(ent = ent_lab[[ent]], qty = 'memorization onset',
                     n = as.numeric(v$mem_onset)))
  }))
  ons$ent <- factor(ons$ent, levels = ent_lab[ents])
  pd <- ggplot(ons, aes(ent, n, colour = qty, shape = qty, group = qty)) +
    geom_line(linewidth = 0.8, colour = '#666666') +
    geom_point(size = 2.8) +
    scale_colour_manual(values = c('decay onset' = CB$blue, 'memorization onset' = CB$vermillion),
                        name = NULL) +
    scale_shape_manual(values = c('decay onset' = 16, 'memorization onset' = 17),
                       name = NULL) +
    labs(title = 'Onset coincidence', x = NULL, y = 'Onset epoch n') +
    paper_theme() + tag_theme +
    theme(legend.position = 'top',
          axis.text.x = element_text(size = 7.5, angle = 20, hjust = 1))

  # Strip mode: patchwork tags at npc y~0.98 collide with the collected top
  # legend once titles are stripped (same failure as E1_repeat). Route tags
  # through the title slot, which the stripper preserves as its own band.
  p <- compose_E1_four_panel(list(pa, pb, pc, pd), 'E1_large_completion', 7.2, 5.4, root)
  save_both(p, 'E1_large_completion', w = 7.2, h = 5.4)
}

# ============================================================
# E1-2 : R_free vs model scale (param count) + small-cap seed spread
# ============================================================
make_E1_scale_band <- function(summ) {
  cat('\n--- E1-2 R_free vs scale ---\n')
  # R_free per full-coverage synthetic cell, plotted against param count.
  caps <- c('small', 'med', 'large'); ents <- c('low', 'med', 'high')
  ent_col <- c('low' = CB$blue, 'med' = CB$vermillion, 'high' = CB$green)
  ent_lab <- c(low = 'low entropy', med = 'medium entropy', high = 'high entropy')
  pts <- list()
  for (cap in caps) for (ent in ents) {
    v <- cell_verdict(summ, cap, ent)
    if (is.null(v) || !v$coverage_full) next
    cat(sprintf('  %-6s/%-4s  params=%.2fM  R_free=%d\n',
                cap, ent, v$n_params / 1e6, v$R_free))
    pts[[length(pts)+1]] <- data.frame(
      cap = cap, ent = ent, params_M = v$n_params / 1e6, R_free = v$R_free)
  }
  df <- bind_rows(pts)
  df$ent <- factor(df$ent, levels = ents, labels = ent_lab[ents])
  names(ent_col) <- ent_lab[names(ent_col)]
  # Deterministic per-entropy dodge so co-located entropy points (many cells
  # share R_free=4 at the same param count) are all visible rather than stacked.
  df$ent_idx      <- as.integer(df$ent) - 2          # -1 / 0 / +1 for low/med/high
  df$params_dodge <- df$params_M * (1.17 ^ df$ent_idx)  # symmetric offset on log-x
  df$R_free_dodge <- df$R_free + df$ent_idx * 0.16      # small vertical fan-out

  # Small-cap per-seed spread at the n=10 decision point (the R_free=10 corner).
  # Compute per-seed excess at n=10 for small/low and small/med.
  seed_pts <- list()
  for (ent in c('low', 'med')) {
    s <- summ %>% filter(budget == BUDGET, capacity == 'small', entropy == ent)
    fresh <- median(s$val_loss[s$n_epochs == 1])
    s10 <- s %>% filter(n_epochs == 10)
    pm <- median(s$n_params, na.rm = TRUE) / 1e6
    cat(sprintf('  small/%-4s n=10 per-seed excess (nseed=%d): %s\n', ent, nrow(s10),
                paste(sprintf('%.4f', sort(s10$val_loss - fresh)), collapse = ' ')))
    for (i in seq_len(nrow(s10))) {
      seed_pts[[length(seed_pts)+1]] <- data.frame(
        params_M = pm, excess10 = s10$val_loss[i] - fresh)
    }
  }
  sp <- bind_rows(seed_pts)
  # Map the n=10 free/not-free decision to R_free on the same axis: a seed sits
  # at R_free=10 if its n=10 excess is below threshold, else effectively at 4.
  sp$Rfree_seed <- ifelse(sp$excess10 < FREE_EPS, 10, 4)
  cat(sprintf('  small-cap n=10 seeds below 0.05: %d / %d\n',
              sum(sp$Rfree_seed == 10), nrow(sp)))

  # x positions jittered slightly so overplotted seed points are visible.
  set.seed(1)
  sp$params_jit <- sp$params_M * (1 + runif(nrow(sp), -0.05, 0.05))

  p <- ggplot(df, aes(params_M, R_free)) +
    annotate('rect', xmin = 1.5, xmax = 12000, ymin = 4, ymax = 10,
             fill = CB$skyblue, alpha = 0.12) +
    annotate('text', x = 2.0, y = 9.4, label = '4-10 free band',
             size = 2.8, colour = 'black', hjust = 0) +
    # large-scale anchor (Muennighoff et al.): ~4 epochs at 8.7B = 8700M params
    annotate('point', x = 8700, y = 4, shape = 18, size = 4, colour = '#444444') +
    # one line at y=4.5: two lines at 4.7 collided with the grey audit block
    annotate('text', x = 8700, y = 4.55,
             label = 'large-scale anchor (~4)', size = 2.5, colour = 'black',
             hjust = 0.5) +
    # make the empty 12M–8.7B stretch self-explanatory: it is an untested span
    # between this work's grid and the published LLM-scale anchor, not missing ink
    annotate('text', x = 300, y = 7,
             label = 'untested span\n(3-12M vs 8.7B)',
             size = 2.6, colour = '#6b7280', hjust = 0.5, lineheight = 0.9) +
    # small-cap per-seed spread at the n=10 decision
    geom_point(data = sp, aes(params_jit, Rfree_seed),
               shape = 4, size = 1.8, colour = CB$grey, stroke = 0.7,
               inherit.aes = FALSE, alpha = 0.8) +
    annotate('text', x = 2.6, y = 5.4,
             label = '\u00d7 per-seed R_free\n(small-capacity audit)',
             size = 2.4, colour = '#6b7280', hjust = 0, lineheight = 0.9) +
    geom_point(data = df, aes(params_dodge, R_free_dodge, colour = ent, shape = ent),
               size = 3, alpha = 0.9, stroke = 0.6, inherit.aes = FALSE) +
    scale_x_log10(breaks = c(1, 3, 10, 30, 100, 300, 1000, 8700),
                  labels = c('1', '3', '10', '30', '100', '300', '1000', '8700'),
                  limits = c(1.5, 15000)) +
    scale_y_continuous(breaks = c(4, 10), limits = c(3.5, 10.5)) +
    scale_colour_manual(values = ent_col, name = NULL) +
    scale_shape_manual(values = c(16, 17, 15), name = NULL) +
    labs(title = 'Free-repetition count R<sub>free</sub> vs model size',
         x = 'Model size (million parameters, log scale)',
         y = expression('Free epochs '*R[free])) +
    paper_theme() + tag_theme +
    theme(legend.position = 'top', legend.key.size = unit(0.7, 'lines'))

  # (b) per-entropy R_free strips (the cell distribution behind panel (a))
  p_b <- ggplot(df, aes(ent, R_free, colour = ent, shape = ent)) +
    annotate('rect', xmin = -Inf, xmax = Inf, ymin = 4, ymax = 10,
             fill = CB$skyblue, alpha = 0.12) +
    stat_summary(fun = median, geom = 'crossbar', width = 0.45, colour = '#1a1a1a') +
    geom_point(position = position_jitter(width = 0.08, height = 0, seed = 71),
               size = 2.4, alpha = 0.85) +
    scale_colour_manual(values = ent_col, name = NULL) +
    scale_shape_manual(values = c(16, 17, 15), name = NULL) +
    scale_y_continuous(breaks = c(4, 10), limits = c(3.5, 10.5)) +
    labs(title = '(b) Per-entropy cell distribution',
         x = NULL, y = expression('Free epochs '*R[free])) +
    paper_theme() + tag_theme +
    theme(legend.position = 'none',
          axis.text.x = element_text(size = 7, angle = 20, hjust = 1))

  # (c) real-text + capxl + PCFG overlay on the scale axis: the band holds on
  #     real bytes and across families
  rt_rows <- list()
  add_rt <- function(label, params_M, R_free, family) {
    rt_rows[[length(rt_rows)+1]] <<- data.frame(
      label = label, params_M = params_M, R_free = R_free, family = family,
      stringsAsFactors = FALSE)
  }
  for (f in list.files(file.path(resdir, 'repeated_data_realtext'),
                       pattern = 'med_b50M_s.*\\.json', full.names = TRUE)) {
    d <- fromJSON(f, simplifyVector = FALSE)
    add_rt('WikiText (5.6M)', d$n_params / 1e6, d$R_free, 'real bytes')
  }
  for (f in list.files(file.path(resdir, 'repeated_data_realtext_code'),
                       pattern = 'med_b50M_s.*\\.json', full.names = TRUE)) {
    d <- fromJSON(f, simplifyVector = FALSE)
    add_rt('code, as collected', d$n_params / 1e6, d$R_free, 'real bytes')
  }
  for (f in list.files(file.path(resdir, 'repeated_data_realtext_shards'),
                       pattern = 'code_v2_shard.*\\.json', full.names = TRUE)) {
    d <- fromJSON(f, simplifyVector = FALSE)
    add_rt('code, near-dedup', d$n_params / 1e6, d$R_free, 'real bytes')
  }
  # capxl cells: xl (29.9M) and xxl (57.1M), R_free recomputed from summaries
  capxl_fs <- list.files(file.path(resdir, 'repeated_data_capxl'),
                         pattern = '\\.jsonl$', full.names = TRUE)
  capxl_rows <- bind_rows(lapply(capxl_fs, function(f) {
    lines <- readLines(f, warn = FALSE)
    s <- NULL
    for (l in rev(lines)) {
      dd <- tryCatch(fromJSON(l, simplifyVector = TRUE), error = function(e) NULL)
      if (!is.null(dd) && !is.null(dd[['_summary']])) { s <- dd[['_summary']]; break }
    }
    if (is.null(s)) return(NULL)
    data.frame(capacity = s$capacity, entropy = s$entropy_level, n = s$n_epochs,
               val = s$final_val_loss, params = s$n_params, stringsAsFactors = FALSE)
  }))
  capxl_rf <- capxl_rows %>%
    group_by(capacity, entropy, params) %>%
    mutate(fresh = median(val[n == 2])) %>%
    summarise(R_free = max(n[(val - fresh) < FREE_EPS]), params = first(params),
              .groups = 'drop') %>%
    mutate(label = paste0('capxl ', capacity, '/', entropy))
  for (i in seq_len(nrow(capxl_rf)))
    add_rt(capxl_rf$label[i], capxl_rf$params[i] / 1e6, capxl_rf$R_free[i], 'capxl')
  # PCFG family: R_free recomputed per capacity (family-specific ~20)
  pcfg_fs <- list.files(file.path(resdir, 'repeated_data_pcfg'),
                        pattern = '\\.jsonl$', full.names = TRUE)
  pcfg_rows <- bind_rows(lapply(pcfg_fs, function(f) {
    lines <- readLines(f, warn = FALSE)
    s <- NULL
    for (l in rev(lines)) {
      dd <- tryCatch(fromJSON(l, simplifyVector = TRUE), error = function(e) NULL)
      if (!is.null(dd) && !is.null(dd[['_summary']])) { s <- dd[['_summary']]; break }
    }
    if (is.null(s)) return(NULL)
    data.frame(capacity = s$capacity %||% 'large', U = s$unique_tokens %||% NA,
               E = s$epochs %||% s$n_epochs, val = s$final_val_loss,
               params = s$n_params %||% NA_real_, stringsAsFactors = FALSE)
  }))
  if (nrow(pcfg_rows)) {
    pcfg_rf <- pcfg_rows %>%
      group_by(capacity) %>%
      mutate(fresh = median(val[E == min(E)], na.rm = TRUE)) %>%
      summarise(R_free = max(E[(val - fresh) < FREE_EPS], na.rm = TRUE),
                params = median(params, na.rm = TRUE), .groups = 'drop') %>%
      filter(is.finite(R_free))
    for (i in seq_len(nrow(pcfg_rf)))
      add_rt(paste0('PCFG ', pcfg_rf$capacity[i]), pcfg_rf$params[i] / 1e6,
             pcfg_rf$R_free[i], 'PCFG family')
  }
  rt <- bind_rows(rt_rows)
  fam_col <- c('real bytes' = CB$orange, 'capxl' = CB$skyblue, 'PCFG family' = CB$pink)
  p_c <- ggplot(rt, aes(params_M, R_free, colour = family, shape = family)) +
    annotate('rect', xmin = 1.5, xmax = 1500, ymin = 4, ymax = 10,
             fill = CB$skyblue, alpha = 0.12) +
    geom_point(size = 2.8, alpha = 0.9, stroke = 0.6,
               position = position_jitter(width = 0, height = 0.15, seed = 73)) +
    scale_x_log10(breaks = c(1, 3, 10, 30, 100, 300, 1000),
                  labels = c('1', '3', '10', '30', '100', '300', '1000')) +
    scale_colour_manual(values = fam_col, name = NULL) +
    scale_shape_manual(values = c(16, 17, 15), name = NULL) +
    labs(title = '(c) Real bytes, capxl, and PCFG on the scale axis',
         x = 'Model size (million parameters, log scale)',
         y = expression('Free epochs '*R[free])) +
    paper_theme() + tag_theme +
    theme(legend.position = 'top')

  # (d) small-capacity per-seed audit at the n=10 decision point
  p_d <- ggplot(sp, aes(factor(Rfree_seed), excess10)) +
    geom_hline(yintercept = FREE_EPS, colour = CB$grey, linetype = 'dashed',
               linewidth = 0.5) +
    geom_point(position = position_jitter(width = 0.12, height = 0, seed = 75),
               size = 2.0, colour = CB$grey, alpha = 0.8) +
    labs(title = '(d) Small-cap n=10 seed audit',
         x = expression('Seed-level '*R[free]*' verdict'), y = 'Excess at n = 10 (nats)') +
    paper_theme() + tag_theme

  p_all <- compose_E1_four_panel(list(p, p_b, p_c, p_d), 'E1_scale_band', 7.2, 5.2, root)

  save_both(p_all, 'E1_scale_band', w = 7.2, h = 5.2)
}

# ============================================================
# E1-3 : Within-run divergence trajectory (train vs validation)
# ============================================================
make_E1_within_run <- function() {
  cat('\n--- E1-3 within-run divergence (four-panel) ---\n')
  # Representative high-capacity medium-entropy cell, seed 0:
  #   free run  n=4  (U=5M)   -> train and val stay locked
  #   damaged   n=20 (U=1M)   -> train falls (memorizes) while val climbs
  ld <- file.path(resdir, 'repeated_data_ultragoal_large')
  free <- read_epochs(file.path(ld, 'large_med_U5M_E4_s0.jsonl'))
  dam  <- read_epochs(file.path(ld, 'large_med_U1M_E20_s0.jsonl'))
  free$run <- 'n = 4 (within free band)'
  dam$run  <- 'n = 20 (past free band)'
  df <- bind_rows(free, dam)
  df$run <- factor(df$run, levels = c('n = 4 (within free band)',
                                      'n = 20 (past free band)'))

  # (a) reuse schedule: repeats n and corpus size U per run (schedule doc)
  sched <- data.frame(
    run    = factor(levels(df$run), levels = levels(df$run)),
    n      = c(4, 20),
    U      = c(5, 1))
  sched_long <- sched %>%
    pivot_longer(c(n, U), names_to = 'what', values_to = 'value') %>%
    mutate(what = factor(what, levels = c('n', 'U'),
                         labels = c('repeats n (x/epoch)', 'corpus U (M tokens)')))
  pa <- ggplot(sched_long, aes(run, value, fill = what)) +
    geom_col(position = position_dodge(width = 0.72), width = 0.62) +
    scale_fill_manual(values = c('repeats n (x/epoch)' = CB$orange,
                                 'corpus U (M tokens)' = CB$blue), name = NULL) +
    labs(title = 'Reuse schedule of the two runs',
         x = NULL, y = 'Schedule value') +
    scale_x_discrete(labels = c('n = 4 (within free band)' = 'n=4 (free)',
                                'n = 20 (past free band)' = 'n=20 (past)')) +
    paper_theme() + theme(legend.position = 'top',
                          axis.text.x = element_text(size = 7, angle = 0, hjust = 0.5))

  # (b) validation loss during reuse (the divergence that motivates the figure)
  pb <- ggplot(df, aes(epoch, val_loss, colour = run)) +
    geom_line(linewidth = 0.9) +
    geom_point(size = 1.4, alpha = 0.8) +
    scale_colour_manual(values = c('n = 4 (within free band)' = CB$blue,
                                   'n = 20 (past free band)' = CB$vermillion),
                        name = 'run') +
    labs(title = 'Validation loss during reuse',
         x = 'Training epoch', y = 'Validation loss (nats)') +
    paper_theme() + theme(legend.position = 'none')

  # (c) accumulated repeated-data exposure (repeats x epoch) per run
  expo <- df %>% mutate(exposure = epoch * ifelse(run == levels(run)[1], 4, 20))
  pc <- ggplot(expo, aes(epoch, exposure, colour = run)) +
    geom_line(linewidth = 0.9) +
    scale_colour_manual(values = c('n = 4 (within free band)' = CB$blue,
                                   'n = 20 (past free band)' = CB$vermillion),
                        name = 'run') +
    labs(title = 'Accumulated repeated-data exposure',
         x = 'Training epoch', y = 'Cumulative repeats') +
    paper_theme() + theme(legend.position = 'none')

  # (d) within-run failure mode: train-val gap trajectory per run
  gap <- df %>% mutate(gap = val_loss - train_loss)
  pd <- ggplot(gap, aes(epoch, gap, colour = run)) +
    geom_hline(yintercept = 0, colour = '#888888', linetype = 'dashed',
               linewidth = 0.5) +
    geom_line(linewidth = 0.9) +
    geom_point(size = 1.4, alpha = 0.8) +
    scale_colour_manual(values = c('n = 4 (within free band)' = CB$blue,
                                   'n = 20 (past free band)' = CB$vermillion),
                        name = 'run') +
    labs(title = 'Train-validation gap (failure mode)',
         x = 'Training epoch', y = 'val - train (nats)') +
    paper_theme() + theme(legend.position = 'none')

  p <- compose_E1_four_panel(list(pa, pb, pc, pd), 'E1_within_run', 7.2, 5.2, root)
  save_both(p, 'E1_within_run', w = 7.2, h = 5.2)
}

# ============================================================
# Run
# ============================================================
cat('=== make_E1_new_figs_r.R: new E1 figures from unused data ===\n')
cat('working dir:', getwd(), '\n')
summ <- load_all_summaries()
cat(sprintf('loaded %d run summaries from %d source dirs\n', nrow(summ), length(SRC_DIRS)))

only_fig <- Sys.getenv('ONLY_FIG', unset = '')
run_all <- !nzchar(only_fig)
if (run_all || identical(only_fig, 'E1_large_completion')) make_E1_large_completion(summ)
if (run_all || identical(only_fig, 'E1_scale_band')) make_E1_scale_band(summ)
if (run_all || identical(only_fig, 'E1_within_run')) make_E1_within_run()
if (run_all || identical(only_fig, 'E1_capxl')) make_E1_capxl()

cat('\n=== verification ===\n')
expected <- if (nzchar(only_fig)) only_fig else c('E1_large_completion', 'E1_scale_band', 'E1_within_run', 'E1_capxl')
all_ok <- TRUE
for (nm in expected) {
  fp <- file.path(figdir, paste0(nm, '.png'))
  sz <- if (file.exists(fp)) file.info(fp)$size else 0L
  st <- if (sz > 10000L) 'OK' else 'MISSING/TINY'
  cat(sprintf('  %-32s %s (%d bytes)\n', paste0(nm, '.png'), st, sz))
  if (sz <= 10000L) all_ok <- FALSE
}
if (!all_ok) stop('one or more figures missing/too small')
cat('\nall new E1 figures written.\n')
