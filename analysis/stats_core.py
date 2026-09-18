"""Statistical primitives used by the octoplus analysis.

Implemented directly on numpy/scipy so the pipeline has no dependency
beyond what the environment provides. Every function documents the
assumption it makes, because the assumptions are what a reader of the
report has to be able to check.
"""
import numpy as np
from scipy import stats

RNG = np.random.default_rng(20260918)


def bootstrap_ci(values, statistic=np.mean, n_boot=10_000, alpha=0.05):
    """Percentile bootstrap CI.

    Used rather than a t interval because survival-rate is bounded at
    0 and 100 and is strongly skewed in the harsher conditions, so the
    normal approximation is not safe near the bounds.
    """
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if values.size == 0:
        return np.nan, np.nan, np.nan
    point = statistic(values)
    if values.size == 1:
        return point, point, point
    idx = RNG.integers(0, values.size, size=(n_boot, values.size))
    draws = statistic(values[idx], axis=1)
    lo, hi = np.percentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, lo, hi


def cliffs_delta(a, b):
    """Cliff's delta: P(a > b) - P(a < b), in [-1, 1].

    A non-parametric effect size. Chosen over Cohen's d because the
    outcome distributions are bounded and often bimodal (many runs end
    at either total survival or extinction), which makes a
    standardised mean difference hard to interpret.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if a.size == 0 or b.size == 0:
        return np.nan
    # Rank-based computation, O(n log n) rather than the O(n*m) pairwise form.
    combined = np.concatenate([a, b])
    ranks = stats.rankdata(combined)
    rank_a = ranks[:a.size].sum()
    u = rank_a - a.size * (a.size + 1) / 2.0
    return 2.0 * u / (a.size * b.size) - 1.0


def delta_magnitude(d):
    """Romano et al. (2006) thresholds for interpreting Cliff's delta."""
    if np.isnan(d):
        return "undefined"
    ad = abs(d)
    if ad < 0.147:
        return "negligible"
    if ad < 0.33:
        return "small"
    if ad < 0.474:
        return "medium"
    return "large"


def paired_test(a, b):
    """Wilcoxon signed-rank on paired observations.

    Pairing is by random seed: within one environment cell, every
    strategy is run against the identical generated world and the
    identical initial placement, so the pairs are matched on every
    source of variation except the strategy itself. This removes
    environment variance from the comparison and is far more powerful
    than an unpaired test on the same data.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    mask = ~(np.isnan(a) | np.isnan(b))
    a, b = a[mask], b[mask]
    if a.size < 2 or np.all(a == b):
        return dict(n=int(a.size), statistic=np.nan, p=np.nan,
                    median_diff=float(np.median(a - b)) if a.size else np.nan)
    res = stats.wilcoxon(a, b, zero_method="wilcox", alternative="two-sided")
    return dict(n=int(a.size), statistic=float(res.statistic),
                p=float(res.pvalue), median_diff=float(np.median(a - b)))


def holm_correct(pvalues):
    """Holm-Bonferroni step-down adjustment.

    The design produces many comparisons, so unadjusted p-values would
    overstate significance. Holm is used rather than Bonferroni because
    it is uniformly more powerful and needs no independence assumption.
    """
    p = np.asarray(pvalues, dtype=float)
    valid = ~np.isnan(p)
    out = np.full(p.shape, np.nan)
    pv = p[valid]
    m = pv.size
    if m == 0:
        return out
    order = np.argsort(pv)
    adjusted = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pv[idx])
        adjusted[idx] = min(1.0, running)
    out[valid] = adjusted
    return out


def omega_squared(groups):
    """Omega-squared effect size for a one-way layout.

    Reported instead of eta-squared because eta-squared is biased
    upward, and with 9,720 runs almost any effect is "significant" —
    the question that matters is how much variance a factor explains.
    """
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g[~np.isnan(g)] for g in groups]
    groups = [g for g in groups if g.size > 0]
    if len(groups) < 2:
        return np.nan
    all_values = np.concatenate(groups)
    n = all_values.size
    k = len(groups)
    grand = all_values.mean()
    ss_between = sum(g.size * (g.mean() - grand) ** 2 for g in groups)
    ss_total = ((all_values - grand) ** 2).sum()
    ss_within = ss_total - ss_between
    if n - k <= 0 or ss_total <= 0:
        return np.nan
    ms_within = ss_within / (n - k)
    denom = ss_total + ms_within
    if denom <= 0:
        return np.nan
    return float((ss_between - (k - 1) * ms_within) / denom)


def kaplan_meier(times, observed):
    """Kaplan-Meier estimate of the survival function.

    `times` is the extinction tick; `observed` is True when extinction
    actually happened and False when the run hit its time limit with
    prey still alive. Censoring matters here: treating a censored run
    as if the population died at the time limit would badly understate
    the survival of the better strategies.
    """
    times = np.asarray(times, dtype=float)
    observed = np.asarray(observed, dtype=bool)
    order = np.argsort(times, kind="mergesort")
    times, observed = times[order], observed[order]

    n_at_risk = times.size
    survival = 1.0
    xs, ys = [0.0], [1.0]
    i = 0
    while i < times.size:
        t = times[i]
        j = i
        events = 0
        while j < times.size and times[j] == t:
            events += int(observed[j])
            j += 1
        censored_and_events = j - i
        if events > 0 and n_at_risk > 0:
            survival *= (1.0 - events / n_at_risk)
            xs.append(float(t))
            ys.append(float(survival))
        n_at_risk -= censored_and_events
        i = j
    return np.array(xs), np.array(ys)


def logrank(times_a, obs_a, times_b, obs_b):
    """Two-sample log-rank test comparing survival curves."""
    times = np.concatenate([times_a, times_b]).astype(float)
    obs = np.concatenate([obs_a, obs_b]).astype(bool)
    group = np.concatenate([np.zeros(len(times_a)), np.ones(len(times_b))])

    event_times = np.unique(times[obs])
    o_minus_e = 0.0
    variance = 0.0
    for t in event_times:
        at_risk = times >= t
        n = at_risk.sum()
        n_a = (at_risk & (group == 0)).sum()
        d = (obs & (times == t)).sum()
        d_a = (obs & (times == t) & (group == 0)).sum()
        if n <= 1:
            continue
        expected = d * n_a / n
        o_minus_e += d_a - expected
        variance += (d * (n_a / n) * (1 - n_a / n) * (n - d) / (n - 1))
    if variance <= 0:
        return np.nan, np.nan
    chi2 = o_minus_e ** 2 / variance
    return float(chi2), float(stats.chi2.sf(chi2, df=1))
