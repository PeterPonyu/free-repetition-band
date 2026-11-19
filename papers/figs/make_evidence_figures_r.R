suppressPackageStartupMessages({library(jsonlite); library(ggplot2); library(dplyr); library(tidyr); library(scales); library(patchwork); library(svglite); library(ragg)})
figdir <- 'papers/figs'; evdir <- 'experiments/results/figures-deepcheck'; svgdir <- 'papers/figs/evidence_r'; dir.create(figdir, showWarnings=FALSE, recursive=TRUE); dir.create(svgdir, showWarnings=FALSE, recursive=TRUE)
theme_paper <- function(base=9) theme_minimal(base_size=base, base_family='TeX Gyre Termes') + theme(
  panel.grid.minor=element_blank(),
  plot.title=element_text(face='plain', size=base+1),
  plot.subtitle=element_blank(),
  strip.text=element_text(face='plain', size=base),
  legend.position='bottom', legend.text=element_text(size=base-1), legend.title=element_text(size=base-1),
  axis.text=element_text(size=base-1), axis.title=element_text(size=base),
  plot.tag=element_text(face='bold', size=11), plot.tag.position=c(0.02, 0.98)
)
source(file.path(figdir, 'fig_pipeline.R'))  # emit_vector(): tikz/.tex + cairo_pdf/.pdf
source(file.path(figdir, 'E1_panel_contract.R'))
save_both <- function(p, name, w=5.0, h=3.5){ pngp <- file.path(figdir, paste0(name,'.png')); svgp <- file.path(svgdir, paste0(name,'.svg')); ragg::agg_png(pngp, width=w, height=h, units='in', res=300, scaling=1); print(p); dev.off(); svglite::svglite(svgp, width=w, height=h); print(p); dev.off(); emit_vector(p, name, w, h); cat('saved', pngp, svgp, '\n') }

# E1: Real-text capacity bridge (4-panel)
E1 <- fromJSON(file.path(evdir,'e1_capacity_bridge_summary.json'), simplifyVector=FALSE)
e1_df <- bind_rows(lapply(E1$records, function(r) bind_rows(lapply(r$rows, function(v) data.frame(capacity=r$capacity, seed=r$seed, n=v$n, excess=v$excess, val_loss=v$val_loss))))) %>% mutate(seed=factor(seed), n=factor(n, levels=c(1,2,4,10,20)))
e1_first_facet <- levels(factor(e1_df$capacity))[1]
e1_thresh_lab <- data.frame(capacity=e1_first_facet,
                            n=factor(1, levels=c(1,2,4,10,20)),
                            excess=c(.05, .10), lab=c('0.05', '0.10'))
pE1a <- ggplot(e1_df, aes(n, excess, group=seed, color=seed)) +
  geom_hline(yintercept=.05, linetype='dashed', color='grey40') +
  geom_hline(yintercept=.1, linetype='dotted', color='grey40') +
  geom_text(data=e1_thresh_lab, aes(x=n, y=excess, label=lab), color='black', size=2.7,
            hjust=0, vjust=-0.4, inherit.aes=FALSE) +
  geom_line(linewidth=0.75) +
  geom_point(size=2.2) +
  facet_wrap(~capacity, nrow=1) +
  scale_y_continuous(labels=number_format(accuracy=.01)) +
  labs(title='(a) Excess loss vs repeat count (large vs small capacity)', x='repeat count n', y='excess validation loss vs n=1') +
  theme_paper(9)
# (b) R_free by threshold (0.05 vs 0.10) per seed per capacity
e1_rf <- e1_df %>% group_by(capacity, seed) %>%
  summarise(R05 = max(as.integer(as.character(n))[excess < .05]),
            R10 = max(as.integer(as.character(n))[excess < .10]), .groups='drop') %>%
  pivot_longer(c(R05, R10), names_to='thr', values_to='R_free') %>%
  mutate(thr = recode(thr, R05='0.05 nats', R10='0.10 nats'))
pE1b <- ggplot(e1_rf, aes(seed, R_free, fill=thr)) +
  geom_col(position=position_dodge(.72), width=.62, colour='white', linewidth=.2) +
  facet_wrap(~capacity, nrow=1) +
  scale_fill_manual(values=c('0.05 nats'='#2563eb', '0.10 nats'='#1e3a8a'), name=NULL) +
  scale_y_continuous(breaks=c(0,4,10,20), limits=c(0,22)) +
  labs(title='(b) R_free by threshold', x=NULL, y='R_free (epochs)') +
  theme_paper(9) + theme(legend.position='top')
# (c) per-seed excess at the two decision rungs (n=4 and n=10)
e1_dec <- e1_df %>% filter(n %in% c(4,10))
pE1c <- ggplot(e1_dec, aes(n, excess, colour=seed, group=seed)) +
  geom_hline(yintercept=.05, linetype='dashed', color='grey40') +
  geom_line(linewidth=.8) + geom_point(size=2.4) +
  facet_wrap(~capacity, nrow=1) +
  scale_y_continuous(labels=number_format(accuracy=.01)) +
  labs(title='(c) Decision rungs n=4 / n=10', x='repeat count n', y='excess (nats)') +
  theme_paper(9) + theme(legend.position='none')
# (d) cost at n=20 (the consistently-costly end) per seed
 e1_20 <- e1_df %>% filter(n == 20)
pE1d <- ggplot(e1_20, aes(seed, excess, colour=seed)) +
  geom_point(size=2.6, show.legend=FALSE) +
  stat_summary(fun=median, geom='crossbar', width=.45, colour='#1a1a1a') +
  facet_wrap(~capacity, nrow=1) +
  labs(title='(d) Cost at n=20', x='seed', y='excess (nats)') +
  theme_paper(9) + theme(legend.position='none')
pE1 <- compose_E1_four_panel(list(pE1a, pE1b, pE1c, pE1d), 'E1_capacity_bridge', 7.2, 5.2, root = getwd())
save_both(pE1, 'E1_capacity_bridge', 7.2, 5.2)
