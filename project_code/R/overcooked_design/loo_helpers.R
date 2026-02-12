# loo_helpers.R
#
# Helper functions for computing LOO-CV with lapse mixture for multinomial choice models.

compute_loglik_with_lapse <- function(fit, data_subset, epsilon = 0.01, K = 12) {
  #' Compute log-likelihood with lapse mixture for multinomial choice
  #'
  #' Takes a Poisson-trick brms fit and computes proper softmax probabilities
  #' with lapse mixture, then returns log-likelihood matrix for LOO.
  #'
  #' @param fit brms fit object (using Poisson trick)
  #' @param data_subset The data used for fitting (to identify chosen alternatives)
  #' @param epsilon Lapse rate (default 0.01 = 1%)
  #' @param K Number of alternatives per choice (default 12)
  #' @return Matrix of log-likelihoods: samples x choice occasions

  # Extract linear predictor (log scale, before exp)
  linpred <- posterior_linpred(fit, transform = FALSE)

  n_samples <- nrow(linpred)  # posterior samples
  n_obs <- ncol(linpred)      # total observations
  n_choices <- n_obs / K      # number of choice occasions

  # Validate structure
  if (n_obs %% K != 0) {
    stop(sprintf("Number of observations (%d) not divisible by K (%d)",
                 n_obs, K))
  }

  cat(sprintf("  Computing softmax + lapse mixture (epsilon=%.3f)\n", epsilon))
  cat(sprintf("  Input: %d samples x %d observations\n", n_samples, n_obs))
  cat(sprintf("  Output: %d samples x %d choice occasions\n", n_samples, n_choices))

  # Initialize log-likelihood matrix
  log_lik_lapse <- matrix(NA, nrow = n_samples, ncol = n_choices)

  # For each choice occasion
  for (i in 1:n_choices) {
    # Get the K alternatives for this choice occasion
    idx <- ((i-1)*K + 1):(i*K)

    # Linear predictors for all K alternatives: samples x K matrix
    eta <- linpred[, idx, drop = FALSE]

    # Compute softmax probabilities with numerical stability
    # softmax(x) = exp(x - log_sum_exp(x))
    log_sum_exp_eta <- apply(eta, 1, function(x) log(sum(exp(x))))
    log_softmax <- sweep(eta, 1, log_sum_exp_eta, "-")
    softmax_probs <- exp(log_softmax)  # samples x K matrix

    # Add lapse mixture: p = (1-epsilon) * p_softmax + epsilon/K
    probs_with_lapse <- (1 - epsilon) * softmax_probs + epsilon / K

    # Which alternative was chosen?
    chosen_idx <- which(data_subset$y[idx] == 1)

    # Log-likelihood for chosen alternative
    log_lik_lapse[, i] <- log(probs_with_lapse[, chosen_idx])
  }

  # Free memory
  rm(linpred, log_sum_exp_eta, log_softmax, softmax_probs, probs_with_lapse)
  gc()

  return(log_lik_lapse)
}
