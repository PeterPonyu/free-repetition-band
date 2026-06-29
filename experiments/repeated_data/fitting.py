"""Direction 013 — decay-law fitters for the repeated-data value problem.

We observe a loss-vs-budget surface: for each (unique-token count U, epochs E)
cell at a FIXED total token budget B = U * E and fixed model capacity, we measure
the converged loss L. The question is how the *value* of repeated tokens decays
as E grows at fixed B (i.e. as U shrinks).

MUENNIGHOFF FORM (the paper's faithful functional form)
-------------------------------------------------------
Muennighoff et al., "Scaling Data-Constrained Language Models" (NeurIPS 2023,
arXiv:2305.16264), Eq. (6) defines the *effective* data under repetition. With
U unique tokens processed for a total of D = U * E tokens (so the number of
REPEAT passes is the excess over the first pass, R_D = D/U - 1 = E - 1), the
effective unique-data count is

    D' = U + U * R*_D * ( 1 - exp( - R_D / R*_D ) )                    (Eq. 6)

where R*_D is the per-paper "half-life"-style decay constant for *data* (the
larger R*_D, the more value each extra repeat epoch retains; as R*_D -> inf the
exponential -> linear and repeats are as good as fresh data; as R*_D -> 0 only
the first pass U counts). The loss then follows a Chinchilla-style data term on
the EFFECTIVE data,

    L(U, E) = E0 + A_D / (D')^alpha_D                                  (data term)

(Eq. 2/6 of the paper; the parameter term is constant here because model size is
fixed per fit, so it is absorbed into the offset E0.) This module fits
(E0, A_D, alpha_D, R*_D) by nonlinear least squares over the measured (U, E, L)
points.

EXPONENTIAL ALTERNATIVE (InfoLaw 2605.02364, the competing hypothesis)
----------------------------------------------------------------------
The competing claim is that repeated-epoch value decays as a *pure exponential
in the loss reduction* rather than via a saturating effective-data count:

    L(U, E) = L_inf(U) + Delta(U) * exp( - (E - 1) / tau )

i.e. each extra epoch multiplies the residual excess loss by a constant factor
exp(-1/tau). At fixed budget we parameterize L_inf and Delta through U the same
Chinchilla way so the two models have a comparable parameter count:

    L(U, E) = E0 + A_D / U^alpha_D * ( g + (1 - g) * exp( -(E-1)/tau ) )

Here the U^{-alpha_D} sets the fresh-data floor, g in [0,1] is the asymptotic
fraction of that floor retained after infinitely many repeats, and tau is the
exponential decay constant. The hyperbolic/effective-data form and this
exponential form are the two hypotheses the study adjudicates.

MODEL SELECTION
---------------
`compare_models` fits both forms and returns Delta(AIC) and Delta(BIC)
(exponential minus Muennighoff, so NEGATIVE favors the exponential and POSITIVE
favors Muennighoff), plus per-model AIC/BIC/RSS and the fitted parameters.

Self-test (`python fitting.py`): synthesize loss surfaces from EACH form (plus
Gaussian noise), confirm the fitter (a) recovers the GENERATING form by the sign
of Delta(AIC), and (b) recovers the planted decay constant (R*_D or tau) within
tolerance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import curve_fit


# ---------------------------------------------------------------------------
# Functional forms
# ---------------------------------------------------------------------------
def effective_data(U: np.ndarray, E: np.ndarray, R_star: float) -> np.ndarray:
    """Muennighoff effective data D' (Eq. 6). R_D = E - 1 repeat passes."""
    R_D = np.maximum(E - 1.0, 0.0)
    R_star = max(R_star, 1e-9)
    return U + U * R_star * (1.0 - np.exp(-R_D / R_star))


def muennighoff_loss(UE: tuple, E0: float, A: float, alpha: float,
                     R_star: float) -> np.ndarray:
    """L = E0 + A / (D')^alpha with D' the saturating effective-data count."""
    U, E = UE
    Dp = effective_data(np.asarray(U, float), np.asarray(E, float), R_star)
    return E0 + A / np.power(np.maximum(Dp, 1e-9), alpha)


def exponential_loss(UE: tuple, E0: float, A: float, alpha: float,
                     g: float, tau: float) -> np.ndarray:
    """L = E0 + A/U^alpha * ( g + (1-g) * exp(-(E-1)/tau) ) (InfoLaw form)."""
    U, E = UE
    U = np.asarray(U, float)
    E = np.asarray(E, float)
    tau = max(tau, 1e-9)
    g = min(max(g, 0.0), 1.0)
    floor = A / np.power(np.maximum(U, 1e-9), alpha)
    return E0 + floor * (g + (1.0 - g) * np.exp(-(E - 1.0) / tau))


# ---------------------------------------------------------------------------
# Fit result container + information criteria
# ---------------------------------------------------------------------------
@dataclass
class FitResult:
    name: str
    params: dict
    rss: float          # residual sum of squares
    n: int              # number of data points
    k: int              # number of free parameters
    aic: float
    bic: float
    success: bool


def _aic_bic(rss: float, n: int, k: int) -> tuple[float, float]:
    """Gaussian-likelihood AIC/BIC from residual sum of squares.

    AIC = n*ln(RSS/n) + 2k ; BIC = n*ln(RSS/n) + k*ln(n). (The additive constant
    n*(1+ln 2pi) cancels in any model-to-model comparison, so it is omitted.)
    """
    rss = max(rss, 1e-300)
    ll_term = n * math.log(rss / n)
    return ll_term + 2 * k, ll_term + k * math.log(n)


def _fit(form, p0, bounds, U, E, L, names, label) -> FitResult:
    """Least-squares fit of one form; robust to optimizer failure."""
    U = np.asarray(U, float)
    E = np.asarray(E, float)
    L = np.asarray(L, float)
    n = L.size
    k = len(p0)
    try:
        popt, _ = curve_fit(form, (U, E), L, p0=p0, bounds=bounds, maxfev=200000)
        pred = form((U, E), *popt)
        rss = float(np.sum((L - pred) ** 2))
        success = True
        params = dict(zip(names, [float(x) for x in popt]))
    except Exception as exc:  # fit diverged / failed -> record as worst-case
        rss = float(np.sum((L - L.mean()) ** 2))
        success = False
        params = {nm: float("nan") for nm in names}
        params["_error"] = str(exc)
    aic, bic = _aic_bic(rss, n, k)
    return FitResult(label, params, rss, n, k, aic, bic, success)


def fit_muennighoff(U, E, L) -> FitResult:
    """Fit L = E0 + A/(D')^alpha with D' the saturating effective-data count."""
    L = np.asarray(L, float)
    Lmin, Lspan = float(L.min()), float(max(L.max() - L.min(), 1e-3))
    Umax = float(np.max(U))
    p0 = [Lmin, Lspan * Umax ** 0.3, 0.3, 5.0]
    bounds = ([0.0, 1e-6, 1e-3, 1e-3], [Lmin + 1e-6 + L.max(), 1e12, 3.0, 1e6])
    return _fit(muennighoff_loss, p0, bounds, U, E, L,
                ["E0", "A", "alpha", "R_star"], "muennighoff")


def fit_exponential(U, E, L) -> FitResult:
    """Fit the InfoLaw exponential-decay alternative."""
    L = np.asarray(L, float)
    Lmin, Lspan = float(L.min()), float(max(L.max() - L.min(), 1e-3))
    Umax = float(np.max(U))
    p0 = [Lmin, Lspan * Umax ** 0.3, 0.3, 0.5, 3.0]
    bounds = ([0.0, 1e-6, 1e-3, 0.0, 1e-3],
              [Lmin + 1e-6 + L.max(), 1e12, 3.0, 1.0, 1e6])
    return _fit(exponential_loss, p0, bounds, U, E, L,
                ["E0", "A", "alpha", "g", "tau"], "exponential")


def compare_models(U, E, L) -> dict:
    """Fit both forms; return per-model fits + Delta(AIC)/Delta(BIC).

    Delta = exponential - muennighoff. NEGATIVE Delta favors the exponential
    (InfoLaw) form; POSITIVE Delta favors the Muennighoff hyperbolic form.
    """
    fm = fit_muennighoff(U, E, L)
    fe = fit_exponential(U, E, L)
    d_aic = fe.aic - fm.aic
    d_bic = fe.bic - fm.bic
    preferred = "muennighoff" if d_aic > 0 else "exponential"
    return {
        "muennighoff": fm,
        "exponential": fe,
        "delta_aic": d_aic,
        "delta_bic": d_bic,
        "preferred": preferred,
    }


# ---------------------------------------------------------------------------
# Self-test: recover the generating form (sign of Delta-AIC) + planted constant.
# ---------------------------------------------------------------------------
def _make_grid():
    """A budget-style (U, E) grid: fixed budget B=U*E over a spread of U."""
    Us = np.array([0.5, 1, 2, 5, 10, 20], dtype=float) * 1e6
    B = 20e6
    U_list, E_list = [], []
    for U in Us:
        E = max(1.0, round(B / U))
        U_list.append(U)
        E_list.append(E)
    # add a couple of higher-epoch points at the small-U end to constrain decay
    for U in [0.5e6, 1e6]:
        for E in [40, 80]:
            U_list.append(U)
            E_list.append(float(E))
    return np.array(U_list), np.array(E_list)


def _self_test() -> int:
    rng = np.random.default_rng(0)
    U, E = _make_grid()
    ok = True

    # --- 1. data generated by the MUENNIGHOFF form ---
    true_R = 8.0
    L_m = muennighoff_loss((U, E), E0=1.0, A=200.0, alpha=0.30, R_star=true_R)
    L_m_noisy = L_m + rng.normal(0, 0.01, size=L_m.shape)
    cmp_m = compare_models(U, E, L_m_noisy)
    R_hat = cmp_m["muennighoff"].params.get("R_star", float("nan"))
    m_picks_m = cmp_m["delta_aic"] > 0
    R_recovered = abs(R_hat - true_R) / true_R < 0.5
    print("SELF-TEST decay-law fitters")
    print(f"  [gen=muennighoff] delta_aic={cmp_m['delta_aic']:+.2f} "
          f"(>0 => picks muennighoff: {m_picks_m})  "
          f"R*_hat={R_hat:.3f} (true {true_R}, recovered: {R_recovered})")
    if not (m_picks_m and R_recovered):
        ok = False

    # --- 2. data generated by the EXPONENTIAL form ---
    true_tau = 4.0
    L_e = exponential_loss((U, E), E0=1.0, A=200.0, alpha=0.30, g=0.2,
                           tau=true_tau)
    L_e_noisy = L_e + rng.normal(0, 0.01, size=L_e.shape)
    cmp_e = compare_models(U, E, L_e_noisy)
    tau_hat = cmp_e["exponential"].params.get("tau", float("nan"))
    e_picks_e = cmp_e["delta_aic"] < 0
    tau_recovered = abs(tau_hat - true_tau) / true_tau < 0.5
    print(f"  [gen=exponential] delta_aic={cmp_e['delta_aic']:+.2f} "
          f"(<0 => picks exponential: {e_picks_e})  "
          f"tau_hat={tau_hat:.3f} (true {true_tau}, recovered: {tau_recovered})")
    if not (e_picks_e and tau_recovered):
        ok = False

    print("FITTING SELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_self_test())
