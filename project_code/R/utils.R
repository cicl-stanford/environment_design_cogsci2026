# utils.R
# Shared plotting theme, color palette, and helper functions for R analyses.

library(ggplot2)

# ============================================================================
# PLOT THEME
# ============================================================================
plot_theme <- theme(
  plot.title = element_text(
    face = "plain", size = 32, family = "Helvetica Neue",
    margin = margin(b = 0.5, unit = "line")
  ),
  plot.subtitle = element_text(
    face = "plain", size = 24, family = "Helvetica Neue",
    margin = margin(b = 0.5, unit = "line")
  ),
  axis.title.y = element_text(
    face = "plain", size = 28, family = "Helvetica Neue",
    margin = margin(r = 0.5, unit = "line")
  ),
  axis.title.x = element_text(
    face = "plain", size = 28, family = "Helvetica Neue",
    margin = margin(t = 0.5, unit = "line")
  ),
  axis.text.x = element_text(
    size = 17, face = "plain", family = "Helvetica Neue",
    color = "#5E5E5E", margin = margin(t = 0.5, unit = "line")
  ),
  axis.text.y = element_text(
    size = 17, face = "plain", family = "Helvetica Neue",
    color = "#5E5E5E", margin = margin(r = 0.5, unit = "line")
  ),
  legend.title = element_text(face = "plain", size = 24, family = "Helvetica Neue", color = "#5E5E5E"),
  legend.text = element_text(size = 22, face = "plain", family = "Helvetica Neue", color = "#5E5E5E"),
  legend.position = "right",
  legend.key = element_rect(colour = "transparent", fill = "transparent"),
  legend.key.size = unit(0.8, "lines"),
  strip.text = element_text(size = 20, face = "plain", family = "Helvetica Neue"),
  strip.background = element_blank(),
  panel.background = element_blank(),
  panel.grid = element_blank(),
  panel.grid.major = element_blank(),
  panel.grid.minor = element_blank(),
  axis.line = element_line(color = "black", linewidth = 0.5)
)

# ============================================================================
# COLOR PALETTE
# ============================================================================
color_palette <- list(
  # Light hues (effort estimation)
  cooks_light = "#8ecff8",
  dish_light = "#f19e95",

  # Darker hues (intention inference)
  cooks_dark = "#4a9ee2",
  dish_dark = "#e15a4f",

  # Aliases
  cooks_condition = "#8ecff8",
  dish_condition = "#f19e95",
  cooks_intention = "#4a9ee2",
  dish_intention = "#e15a4f",

  # Model comparison
  model_simulation = "#2C3E50",
  model_simulation_plus = "#5D6D7E",
  model_heuristic = "#95A5A6",

  # Generic
  human_data = "#2C3E50"
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

#' Standardized scatterplot with r/RMSE annotations
make_scatterplot <- function(data, x_var, y_var,
                             x_label, y_label,
                             title = NULL, subtitle = NULL,
                             color = color_palette$cooks_condition,
                             ci_color = NULL,
                             add_ci_x = FALSE, add_ci_y = TRUE,
                             x_ci_lower = NULL, x_ci_upper = NULL,
                             y_ci_lower = "ci_lower", y_ci_upper = "ci_upper",
                             xlim = c(0, 100), ylim = c(0, 100),
                             add_secondary_axis = FALSE,
                             secondary_labels = NULL,
                             point_size = 5) {
  if (is.null(ci_color)) ci_color <- color

  fit <- lm(data[[y_var]] ~ data[[x_var]])
  r_value <- cor(data[[y_var]], data[[x_var]], use = "complete.obs")
  rmse_value <- sqrt(mean(residuals(fit)^2))

  p <- ggplot(data, aes(x = .data[[x_var]], y = .data[[y_var]])) +
    geom_abline(color = "black", linewidth = 0.75, linetype = "dashed")

  if (add_ci_y && !is.null(y_ci_lower) && !is.null(y_ci_upper)) {
    p <- p + geom_errorbar(
      aes(ymin = .data[[y_ci_lower]], ymax = .data[[y_ci_upper]]),
      width = 0, linewidth = 0.825, color = ci_color
    )
  }

  if (add_ci_x && !is.null(x_ci_lower) && !is.null(x_ci_upper)) {
    p <- p + geom_errorbarh(
      aes(xmin = .data[[x_ci_lower]], xmax = .data[[x_ci_upper]]),
      height = 0, linewidth = 0.825, color = ci_color
    )
  }

  p <- p + geom_point(size = point_size, alpha = 1,
                       fill = color, color = "black",
                       shape = 21, stroke = 0.5)

  x_pos <- xlim[1] + 0.05 * diff(xlim)
  p <- p +
    geom_text(
      x = x_pos, y = ylim[2] - 0.07 * diff(ylim),
      label = sprintf("r = %.2f", r_value),
      hjust = 0, size = 7.5, family = "Helvetica Neue", color = "#5E5E5E"
    ) +
    geom_text(
      x = x_pos, y = ylim[2] - 0.14 * diff(ylim),
      label = sprintf("RMSE = %.2f", rmse_value),
      hjust = 0, size = 7.5, family = "Helvetica Neue", color = "#5E5E5E"
    )

  p <- p +
    scale_x_continuous(
      name = x_label, limits = xlim,
      breaks = seq(xlim[1], xlim[2], by = 25)
    ) +
    scale_y_continuous(
      name = y_label, limits = ylim,
      breaks = seq(ylim[1], ylim[2], by = 25)
    )

  if (add_secondary_axis && !is.null(secondary_labels)) {
    p <- p + scale_y_continuous(
      name = y_label, limits = ylim,
      breaks = seq(ylim[1], ylim[2], by = 25),
      sec.axis = sec_axis(~ ., breaks = c(ylim[1], ylim[2]),
                           labels = secondary_labels)
    )
  }

  p <- p + labs(title = title, subtitle = subtitle)

  p <- p + plot_theme +
    theme(
      axis.ticks = element_blank(),
      axis.text.x = element_blank(),
      axis.text.y = element_blank(),
      axis.title.x = element_blank(),
      axis.title.y = element_blank()
    )

  return(p)
}

#' Grouped scatterplot with different shapes per group
make_grouped_scatterplot <- function(data, x_var, y_var, group_var,
                                     x_label, y_label,
                                     title = NULL, subtitle = NULL,
                                     color = color_palette$cooks_condition,
                                     ci_color = NULL,
                                     shape_values = c(21, 24),
                                     group_labels = NULL,
                                     add_ci_y = FALSE,
                                     y_ci_lower = "ci_lower", y_ci_upper = "ci_upper",
                                     xlim = c(0, 100), ylim = c(0, 100),
                                     legend_position = c(0.85, 0.15),
                                     point_size = 5) {
  if (is.null(ci_color)) ci_color <- color

  fit <- lm(data[[y_var]] ~ data[[x_var]])
  r_value <- cor(data[[y_var]], data[[x_var]], use = "complete.obs")
  rmse_value <- sqrt(mean(residuals(fit)^2))

  p <- ggplot(data, aes(x = .data[[x_var]], y = .data[[y_var]],
                         shape = .data[[group_var]])) +
    geom_abline(color = "black", linewidth = 0.75, linetype = "dashed")

  if (add_ci_y && !is.null(y_ci_lower) && !is.null(y_ci_upper)) {
    p <- p + geom_errorbar(
      aes(ymin = .data[[y_ci_lower]], ymax = .data[[y_ci_upper]]),
      width = 0, linewidth = 0.825, color = ci_color
    )
  }

  p <- p +
    geom_point(size = point_size, alpha = 1,
               fill = color, color = "black", stroke = 0.5) +
    scale_shape_manual(values = shape_values,
                       labels = if (!is.null(group_labels)) group_labels)

  x_pos <- xlim[1] + 0.05 * diff(xlim)
  p <- p +
    geom_text(
      x = x_pos, y = ylim[2] - 0.07 * diff(ylim),
      label = sprintf("r = %.2f", r_value),
      hjust = 0, size = 7.5, family = "Helvetica Neue", color = "#5E5E5E"
    ) +
    geom_text(
      x = x_pos, y = ylim[2] - 0.14 * diff(ylim),
      label = sprintf("RMSE = %.2f", rmse_value),
      hjust = 0, size = 7.5, family = "Helvetica Neue", color = "#5E5E5E"
    )

  p <- p +
    scale_x_continuous(
      name = x_label, limits = xlim,
      breaks = seq(xlim[1], xlim[2], by = 25)
    ) +
    scale_y_continuous(
      name = y_label, limits = ylim,
      breaks = seq(ylim[1], ylim[2], by = 25)
    )

  p <- p + labs(title = title, subtitle = subtitle, shape = NULL)

  p <- p + plot_theme +
    theme(
      axis.ticks = element_blank(),
      axis.text.x = element_blank(),
      axis.text.y = element_blank(),
      axis.title.x = element_blank(),
      axis.title.y = element_blank(),
      legend.position = legend_position,
      legend.background = element_rect(fill = "transparent")
    )

  return(p)
}
