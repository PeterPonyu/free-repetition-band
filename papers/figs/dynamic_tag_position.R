# papers/figs/dynamic_tag_position.R
# Dynamic panel label positioning based on title length

compute_tag_position_for_figure <- function(panels, threshold = 55) {
  if (!is.list(panels)) {
    stop("panels must be a list", call. = FALSE)
  }

  # Find maximum title length across all panels
  max_len <- 0
  for (panel in panels) {
    if (inherits(panel, "ggplot")) {
      title <- panel$labels$title
      if (!is.null(title) && is.character(title) && length(title) == 1L) {
        # Strip (a)/(b)/(c)/(d) prefix if present
        clean_title <- gsub("^\\([a-d]\\)\\s*", "", title)
        len <- nchar(clean_title)
        max_len <- max(max_len, len)
      }
    }
  }

  # Decide placement based on longest title
  if (max_len > threshold) {
    # Long title: external placement
    list(
      position = c(-0.03, 1.01),           # Outside top-left corner
      margin_adjust = c(12, 12, 10, 14)    # Larger top/left margins
    )
  } else {
    # Short title: internal placement
    list(
      position = c(0.01, 0.985),           # Inside top-left, away from edge
      margin_adjust = c(10, 12, 10, 12)    # Standard margins
    )
  }
}
