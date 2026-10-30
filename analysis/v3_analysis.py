"""Analysis of the v3 experiments (environment-sweep, social-alarm, sensitivity).

Usage:  python3 analysis/v3_analysis.py
Reads:  results/v3/environment-sweep.csv, results/v3/social-alarm.csv,
        results/v3/sensitivity/*.csv (optional)
Writes: analysis/v3/tables/*.csv, analysis/v3/figures/*.pdf|png, analysis/v3/findings.json

Statistics (all two-sided, alpha = 0.05):
- 95% CIs are percentile bootstrap intervals (10,000 resamples).
- Policies are compared on matched seeds: within one environment, seed s gives every
  policy the same world and the same starting positions. Omnibus test: Friedman
  (blocks = seeds). Post hoc: Wilcoxon signed-rank on the paired runs, Holm-corrected,
  effect size = matched-pairs rank-biserial correlation r (-1..1).
- Uniform vs patchy worlds are different worlds, so that comparison is unpaired:
  Mann-Whitney U, effect size Cliff's delta, Holm-corrected.
- Normality is checked with Shapiro-Wilk first; it fails often, so we use rank tests.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
from stats_core import bootstrap_ci, cliffs_delta, holm_correct, kaplan_meier  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results" / "v3"
OUT = ROOT / "analysis" / "v3"
TAB = OUT / "tables"
FIG = OUT / "figures"

POLICIES = ["adaptive-dmas", "flee", "hide", "still", "seek-cover", "experimental-assigned"]
LABEL = {"adaptive-dmas": "Adaptive", "flee": "Flee", "hide": "Hide", "still": "Still",
         "seek-cover": "Seek cover", "experimental-assigned": "Mixed"}
# Validated categorical palette (dataviz reference slots 1, 2, 3, 4, 7, 6), fixed per policy.
COLOR = {"adaptive-dmas": "#2a78d6", "flee": "#eb6834", "hide": "#1baf7a", "still": "#eda100",
         "seek-cover": "#6250d6", "experimental-assigned": "#008300"}
DASH = {"adaptive-dmas": "-", "flee": "--", "hide": "-", "still": ":", "seek-cover": "-.",
        "experimental-assigned": (0, (5, 1, 1, 1))}
COVERS = ["low", "medium", "high"]
ARRANGEMENTS = ["uniform", "patchy"]
INK, INK_SOFT, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
DURATION = 2000

FINDINGS = {}


# ----------------------------------------------------------------------------- loading
def load(path):
    df = pd.read_csv(path, skiprows=6)
    df = df.rename(columns={
        "octopus-strategy-mode": "policy", "cover-amount-category": "cover",
        "cover-arrangement": "arrangement", "experiment-seed": "seed", "social-alarm?": "alarm",
        "count octopuses": "final_pop", "extinction-time": "ext_time",
        "late-mean-population": "late_mean", "late-population-cv": "late_cv",
        "total-births": "births", "total-captures": "captures",
        'time-share "forage"': "share_forage", 'time-share "still"': "share_still",
        'time-share "hide"': "share_hide", 'time-share "flee"': "share_flee",
        'time-share "seek-cover"': "share_seek", "population-history": "history",
    })
    df["alarm"] = df["alarm"].astype(str).str.lower() == "true"
    df["extinct"] = df["ext_time"] >= 0
    if "history" in df:
        df["history"] = df["history"].map(parse_history)
    return df


def parse_history(s):
    """Population after each tick, padded with zeros after extinction to DURATION ticks."""
    h = np.array(s.strip("[]").split(), dtype=float)
    return np.concatenate([h, np.zeros(max(0, DURATION - h.size))])[:DURATION]


# ----------------------------------------------------------------------------- statistics
def rank_biserial_paired(a, b):
    """Matched-pairs rank-biserial r = (sum of positive ranks - sum of negative) / total."""
    d = np.asarray(a, float) - np.asarray(b, float)
    d = d[d != 0]
    if d.size == 0:
        return 0.0
    r = stats.rankdata(np.abs(d))
    return float((r[d > 0].sum() - r[d < 0].sum()) / r.sum())


def wilcoxon_p(a, b):
    d = np.asarray(a, float) - np.asarray(b, float)
    if np.all(d == 0):
        return 1.0
    return float(stats.wilcoxon(a, b, zero_method="wilcox").pvalue)


def mean_ci(v):
    m, lo, hi = bootstrap_ci(v)
    return float(m), float(lo), float(hi)


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0, c - h), min(1, c + h)


def paired_matrix(df, cell_cols, value="late_mean"):
    """Policy x seed table for one cell; checks that every policy has the same seeds."""
    w = df.pivot_table(index="seed", columns="policy", values=value, aggfunc="first")
    assert not w.isna().any().any(), f"unmatched seeds in {cell_cols}"
    return w


# ----------------------------------------------------------------------------- style
def style():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": "#b9b8b3",
        "axes.labelcolor": INK_SOFT, "axes.titlesize": 9, "axes.titleweight": "semibold",
        "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "xtick.color": INK_SOFT, "ytick.color": INK_SOFT, "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5, "legend.frameon": False, "legend.fontsize": 7.5,
        "lines.linewidth": 1.6, "axes.spines.top": False, "axes.spines.right": False,
    })


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def policy_legend(fig, policies=POLICIES, y=1.0, ncol=6):
    handles = [plt.Line2D([], [], color=COLOR[p], ls=DASH[p], lw=2) for p in policies]
    fig.legend(handles, [LABEL[p] for p in policies], loc="lower center",
               bbox_to_anchor=(0.5, y), ncol=ncol, handlelength=2.6, columnspacing=1.4)


# ----------------------------------------------------------------------------- RQ1 + RQ2
def environment_sweep(df):
    n_cells = df.groupby(["policy", "cover", "arrangement"]).size()
    FINDINGS["sweep_runs"] = int(len(df))
    FINDINGS["sweep_runs_per_cell"] = sorted(set(int(x) for x in n_cells))

    # summary table
    rows = []
    for (p, c, a), g in df.groupby(["policy", "cover", "arrangement"]):
        m, lo, hi = mean_ci(g.late_mean)
        surv = g[~g.extinct]
        rows.append(dict(policy=p, cover=c, arrangement=a, n=len(g), mean=m, sd=g.late_mean.std(),
                         ci_lo=lo, ci_hi=hi, median=g.late_mean.median(),
                         extinct=int(g.extinct.sum()),
                         cv_survivors=surv.late_cv.mean() if len(surv) else np.nan,
                         births=g.births.mean(), captures=g.captures.mean(),
                         share_forage=g.share_forage.mean()))
    summ = pd.DataFrame(rows)
    summ["policy"] = pd.Categorical(summ.policy, POLICIES, ordered=True)
    summ["cover"] = pd.Categorical(summ.cover, COVERS, ordered=True)
    summ["arrangement"] = pd.Categorical(summ.arrangement, ARRANGEMENTS, ordered=True)
    summ = summ.sort_values(["arrangement", "cover", "policy"])
    summ.to_csv(TAB / "sweep_summary.csv", index=False, float_format="%.3f")

    # best policy per environment
    best = {}
    for (a, c), g in summ.groupby(["arrangement", "cover"], observed=True):
        g = g.sort_values("mean", ascending=False)
        best[f"{a}-{c}"] = [str(g.iloc[0].policy), round(float(g.iloc[0]["mean"]), 1),
                            str(g.iloc[1].policy), round(float(g.iloc[1]["mean"]), 1)]
    FINDINGS["best_per_environment"] = best

    # pooled over environments
    pooled = []
    for p in POLICIES:
        g = df[df.policy == p]
        m, lo, hi = mean_ci(g.late_mean)
        k = int(g.extinct.sum())
        wlo, whi = wilson(k, len(g))
        surv = g[~g.extinct]
        pooled.append(dict(policy=p, n=len(g), mean=m, ci_lo=lo, ci_hi=hi, sd=g.late_mean.std(),
                           extinct=k, extinct_share=k / len(g), ext_ci_lo=wlo, ext_ci_hi=whi,
                           cv_survivors=surv.late_cv.mean(), share_forage=g.share_forage.mean()))
    pooled = pd.DataFrame(pooled)
    pooled.to_csv(TAB / "sweep_pooled.csv", index=False, float_format="%.3f")
    FINDINGS["pooled"] = {r.policy: dict(mean=round(r["mean"], 1), ci=[round(r.ci_lo, 1), round(r.ci_hi, 1)],
                                         extinct=int(r.extinct), n=int(r.n),
                                         cv=round(r.cv_survivors, 3))
                          for _, r in pooled.iterrows()}

    # normality
    sw = []
    for (p, c, a), g in df.groupby(["policy", "cover", "arrangement"]):
        if g.late_mean.nunique() > 2:
            sw.append(stats.shapiro(g.late_mean).pvalue)
    FINDINGS["shapiro_groups"] = dict(n=len(sw), rejected=int(sum(p < 0.05 for p in sw)))

    # omnibus Friedman per environment + all pairwise Wilcoxon, Holm over the whole family
    omni, pairs = [], []
    for a in ARRANGEMENTS:
        for c in COVERS:
            cell = df[(df.arrangement == a) & (df.cover == c)]
            w = paired_matrix(cell, (a, c))[POLICIES]
            chi2, p = stats.friedmanchisquare(*[w[x] for x in POLICIES])
            n = len(w)
            omni.append(dict(arrangement=a, cover=c, n=n, chi2=chi2, df=len(POLICIES) - 1, p=p,
                             kendall_w=chi2 / (n * (len(POLICIES) - 1))))
            for i, x in enumerate(POLICIES):
                for y in POLICIES[i + 1:]:
                    d = (w[x] - w[y]).values
                    m, lo, hi = mean_ci(d)
                    pairs.append(dict(arrangement=a, cover=c, a=x, b=y, n=n, mean_diff=m,
                                      ci_lo=lo, ci_hi=hi, median_diff=float(np.median(d)),
                                      r=rank_biserial_paired(w[x], w[y]), p=wilcoxon_p(w[x], w[y])))
    omni = pd.DataFrame(omni)
    omni["p_holm"] = holm_correct(omni.p)
    omni.to_csv(TAB / "sweep_friedman.csv", index=False, float_format="%.4g")
    pairs = pd.DataFrame(pairs)
    pairs["p_holm"] = holm_correct(pairs.p)
    pairs.to_csv(TAB / "sweep_pairwise.csv", index=False, float_format="%.4g")
    FINDINGS["friedman"] = {f"{r.arrangement}-{r.cover}": dict(chi2=round(r.chi2, 1), p_holm=float(f"{r.p_holm:.3g}"),
                                                              W=round(r.kendall_w, 2))
                            for _, r in omni.iterrows()}

    # shapiro on the paired differences we test
    swd = [stats.shapiro(df[(df.arrangement == r.arrangement) & (df.cover == r.cover) & (df.policy == r.a)]
                         .sort_values("seed").late_mean.values
                         - df[(df.arrangement == r.arrangement) & (df.cover == r.cover) & (df.policy == r.b)]
                         .sort_values("seed").late_mean.values).pvalue
           for _, r in pairs.iterrows() if r.median_diff != 0 or r.mean_diff != 0]
    FINDINGS["shapiro_paired_diffs"] = dict(n=len(swd), rejected=int(sum(p < 0.05 for p in swd)))

    key = pairs[((pairs.a == "flee") & (pairs.b == "hide")) | (pairs.a == "adaptive-dmas")]
    FINDINGS["key_pairs"] = {f"{r.arrangement}-{r.cover}:{r.a}-{r.b}":
                             dict(diff=round(r.mean_diff, 1), ci=[round(r.ci_lo, 1), round(r.ci_hi, 1)],
                                  r=round(r.r, 2), p_holm=float(f"{r.p_holm:.3g}"))
                             for _, r in key.iterrows()}

    # arrangement effect (unpaired)
    arr = []
    for p in POLICIES:
        for c in COVERS:
            u = df[(df.policy == p) & (df.cover == c) & (df.arrangement == "uniform")].late_mean
            q = df[(df.policy == p) & (df.cover == c) & (df.arrangement == "patchy")].late_mean
            res = stats.mannwhitneyu(q, u, alternative="two-sided")
            arr.append(dict(policy=p, cover=c, mean_uniform=u.mean(), mean_patchy=q.mean(),
                            diff=q.mean() - u.mean(), cliffs_delta=cliffs_delta(q, u), U=res.statistic, p=res.pvalue))
    arr = pd.DataFrame(arr)
    arr["p_holm"] = holm_correct(arr.p)
    arr.to_csv(TAB / "sweep_arrangement.csv", index=False, float_format="%.4g")
    FINDINGS["arrangement"] = {f"{r.policy}-{r.cover}": dict(diff=round(r["diff"], 1), delta=round(r.cliffs_delta, 2),
                                                            p_holm=float(f"{r.p_holm:.3g}"))
                               for _, r in arr.iterrows()}

    # extinction by policy and cover (pooled over arrangement)
    ext = []
    for p in POLICIES:
        for c in COVERS:
            g = df[(df.policy == p) & (df.cover == c)]
            k = int(g.extinct.sum())
            lo, hi = wilson(k, len(g))
            ext.append(dict(policy=p, cover=c, n=len(g), extinct=k, share=k / len(g), ci_lo=lo, ci_hi=hi,
                            median_time_extinct=g[g.extinct].ext_time.median() if k else np.nan))
    pd.DataFrame(ext).to_csv(TAB / "sweep_extinction.csv", index=False, float_format="%.3f")

    # low cover: extinction curves of adaptive vs each other policy (log-rank, Holm over 5)
    from stats_core import logrank
    lr = []
    low = df[df.cover == "low"]
    ref = low[low.policy == "adaptive-dmas"]
    for p in POLICIES[1:]:
        g = low[low.policy == p]
        chi2, pv = logrank(np.where(ref.extinct, ref.ext_time, DURATION), ref.extinct.values,
                           np.where(g.extinct, g.ext_time, DURATION), g.extinct.values)
        lr.append(dict(a="adaptive-dmas", b=p, extinct_a=int(ref.extinct.sum()), extinct_b=int(g.extinct.sum()),
                       n=len(g), chi2=chi2, p=pv))
    lr = pd.DataFrame(lr)
    lr["p_holm"] = holm_correct(lr.p)
    lr.to_csv(TAB / "sweep_logrank_low.csv", index=False, float_format="%.4g")
    FINDINGS["logrank_low"] = {r.b: dict(ext=[r.extinct_a, r.extinct_b], chi2=round(r.chi2, 2),
                                         p=float(f"{r.p:.3g}"), p_holm=float(f"{r.p_holm:.3g}"))
                               for _, r in lr.iterrows()}

    # mixed populations: which inherited policy takes over? (surviving populations only)
    mix = df[(df.policy == "experimental-assigned") & ~df.extinct]
    share_cols = {"still": 'policy-share "still"', "hide": 'policy-share "hide"',
                  "flee": 'policy-share "flee"', "seek-cover": 'policy-share "seek-cover"'}
    mrows = []
    for (a, c), g in mix.groupby(["arrangement", "cover"]):
        mrows.append(dict(arrangement=a, cover=c, n=len(g),
                          **{k: g[v].mean() for k, v in share_cols.items()}))
    mrows = pd.DataFrame(mrows)
    mrows.to_csv(TAB / "sweep_mixed_final_shares.csv", index=False, float_format="%.3f")
    FINDINGS["mixed_final_shares"] = {f"{r.arrangement}-{r.cover}": dict(n=int(r.n), **{k: round(r[k], 2) for k in share_cols})
                                      for _, r in mrows.iterrows()}

    # CV of surviving populations: does policy matter for fluctuations?
    cvr = []
    for a in ARRANGEMENTS:
        for c in COVERS:
            cell = df[(df.arrangement == a) & (df.cover == c) & ~df.extinct]
            groups = [cell[cell.policy == p].late_cv.values for p in POLICIES]
            groups = [g for g in groups if len(g) >= 3]
            h, pv = stats.kruskal(*groups)
            cvr.append(dict(arrangement=a, cover=c, H=h, p=pv, n_runs=len(cell)))
    cvr = pd.DataFrame(cvr)
    cvr["p_holm"] = holm_correct(cvr.p)
    cvr.to_csv(TAB / "sweep_cv_kruskal.csv", index=False, float_format="%.4g")
    FINDINGS["cv_kruskal"] = {f"{r.arrangement}-{r.cover}": dict(H=round(r.H, 1), p_holm=float(f"{r.p_holm:.3g}"))
                              for _, r in cvr.iterrows()}
    return summ, pairs


def fig_timeseries(df, name="fig_timeseries"):
    t = np.arange(0, DURATION, 20)
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 3.5), sharex=True, sharey=True)
    for i, a in enumerate(ARRANGEMENTS):
        for j, c in enumerate(COVERS):
            ax = axes[i, j]
            for p in POLICIES:
                h = np.stack(df[(df.policy == p) & (df.cover == c) & (df.arrangement == a)].history.values)[:, t]
                m = h.mean(0)
                idx = np.random.default_rng(1).integers(0, h.shape[0], (2000, h.shape[0]))
                boots = h[idx].mean(1)
                lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
                ax.fill_between(t / 60, lo, hi, color=COLOR[p], alpha=0.13, lw=0)
                ax.plot(t / 60, m, color=COLOR[p], ls=DASH[p], lw=1.4)
            ax.set_title(f"{a}, {c} cover", fontsize=8.5)
            ax.axvspan(DURATION / 2 / 60, DURATION / 60, color="#f3f2ef", zorder=0, lw=0)
            if j == 0:
                ax.set_ylabel("prey population")
            if i == 1:
                ax.set_xlabel("time (min)")
    axes[0, 0].text(17.2, 235, "late window", fontsize=6.5, color=INK_SOFT)
    axes[0, 0].set_ylim(0, 250)
    axes[0, 0].set_xlim(0, DURATION / 60)
    policy_legend(fig, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    save(fig, name)


def fig_boxes(df):
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 3.7), sharey=True)
    for i, a in enumerate(ARRANGEMENTS):
        for j, c in enumerate(COVERS):
            ax = axes[i, j]
            data = [df[(df.policy == p) & (df.cover == c) & (df.arrangement == a)].late_mean.values for p in POLICIES]
            bp = ax.boxplot(data, widths=0.6, patch_artist=True, showfliers=False,
                            medianprops=dict(color=INK, lw=1.2), whiskerprops=dict(color=INK_SOFT, lw=0.8),
                            capprops=dict(color=INK_SOFT, lw=0.8))
            for k, (box, p) in enumerate(zip(bp["boxes"], POLICIES)):
                box.set(facecolor=COLOR[p] + "40", edgecolor=COLOR[p], lw=1)
                x = np.random.default_rng(k).uniform(-0.18, 0.18, len(data[k])) + k + 1
                ax.scatter(x, data[k], s=5, color=COLOR[p], lw=0, alpha=0.8, zorder=3)
                ax.scatter(k + 1, data[k].mean(), marker="D", s=14, color="white", edgecolor=INK, lw=0.8, zorder=4)
            ax.set_xticks(range(1, 7), [LABEL[p] for p in POLICIES], rotation=40, ha="right")
            ax.set_title(f"{a}, {c} cover", fontsize=8.5)
            ax.grid(axis="x", visible=False)
            if j == 0:
                ax.set_ylabel("late mean population")
            if i == 0:
                ax.tick_params(labelbottom=False)
    axes[0, 0].set_ylim(-5, 255)
    fig.tight_layout()
    save(fig, "fig_late_mean_boxes")


def fig_hide_flee(pairs):
    """Paired difference Flee - Hide and Adaptive - best fixed policy, per environment."""
    rows = []
    for a in ARRANGEMENTS:
        for c in COVERS:
            r = pairs[(pairs.arrangement == a) & (pairs.cover == c) & (pairs.a == "flee") & (pairs.b == "hide")].iloc[0]
            rows.append((f"{a}, {c}", r.mean_diff, r.ci_lo, r.ci_hi, r.p_holm))
    fig, ax = plt.subplots(figsize=(3.5, 2.3))
    y = np.arange(len(rows))[::-1]
    for yi, (lab, m, lo, hi, p) in zip(y, rows):
        col = COLOR["flee"] if lo > 0 else COLOR["hide"] if hi < 0 else INK_SOFT
        ax.plot([lo, hi], [yi, yi], color=col, lw=2, solid_capstyle="round")
        ax.scatter(m, yi, s=28, color=col, edgecolor="white", lw=1, zorder=3)
    ax.axvline(0, color=INK_SOFT, lw=0.8)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.set_xlabel("Flee − Hide, late mean population\n(paired by seed, mean and 95% CI)")
    ax.grid(axis="y", visible=False)
    xl = max(abs(min(r[2] for r in rows)), abs(max(r[3] for r in rows))) * 1.15
    ax.set_xlim(-xl, xl)
    ax.text(-xl * 0.97, y.max() + 0.75, "← hiding better", fontsize=6.5, color=COLOR["hide"], va="bottom")
    ax.text(xl * 0.97, y.max() + 0.75, "fleeing better →", fontsize=6.5, color=COLOR["flee"], ha="right", va="bottom")
    ax.set_ylim(-0.6, y.max() + 1.3)
    fig.tight_layout()
    save(fig, "fig_flee_minus_hide")


def fig_extinction(df):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.1), sharey=True)
    for j, c in enumerate(["low", "medium"]):  # no run went extinct at high cover
        ax = axes[j]
        for p in POLICIES:
            g = df[(df.policy == p) & (df.cover == c)]
            times = np.where(g.extinct, g.ext_time, DURATION)
            xs, ys = kaplan_meier(times, g.extinct.values)
            xs = np.append(xs, DURATION)
            ys = np.append(ys, ys[-1])
            ax.step(xs / 60, ys * 100, where="post", color=COLOR[p], ls=DASH[p], lw=1.5)
        ax.set_title(f"{c} cover", fontsize=8.5)
        ax.set_xlabel("time (min)")
        ax.set_xlim(0, DURATION / 60)
    axes[0].set_ylabel("populations not extinct (%)")
    axes[0].set_ylim(-3, 103)
    policy_legend(fig, y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    save(fig, "fig_extinction")


# ----------------------------------------------------------------------------- RQ3 social alarm
def social_alarm(sa, sweep):
    FINDINGS["alarm_runs"] = int(len(sa))
    # reproducibility: alarm-off runs must equal the patchy runs of the sweep
    off = sa[~sa.alarm].set_index(["policy", "cover", "seed"]).sort_index()
    ref = sweep[sweep.arrangement == "patchy"].set_index(["policy", "cover", "seed"]).sort_index()
    same = np.allclose(off.late_mean.values, ref.loc[off.index].late_mean.values)
    FINDINGS["alarm_off_equals_sweep_patchy"] = bool(same)

    rows = []
    for p in POLICIES:
        for c in COVERS + ["all"]:
            g = sa[sa.policy == p] if c == "all" else sa[(sa.policy == p) & (sa.cover == c)]
            on = g[g.alarm].sort_values(["cover", "seed"])
            of = g[~g.alarm].sort_values(["cover", "seed"])
            assert (on[["cover", "seed"]].values == of[["cover", "seed"]].values).all()
            row = dict(policy=p, cover=c, n=len(on))
            for v in ["late_mean", "births", "captures", "share_forage"]:
                d = on[v].values - of[v].values
                m, lo, hi = mean_ci(d)
                row.update({f"{v}_off": of[v].mean(), f"{v}_on": on[v].mean(), f"{v}_diff": m,
                            f"{v}_ci_lo": lo, f"{v}_ci_hi": hi})
            row["extinct_off"] = int(of.extinct.sum())
            row["extinct_on"] = int(on.extinct.sum())
            row["r"] = rank_biserial_paired(on.late_mean.values, of.late_mean.values)
            row["p"] = wilcoxon_p(on.late_mean.values, of.late_mean.values)
            rows.append(row)
    t = pd.DataFrame(rows)
    per_cover = t.cover != "all"
    t.loc[per_cover, "p_holm"] = holm_correct(t.loc[per_cover, "p"])
    t.loc[~per_cover, "p_holm"] = holm_correct(t.loc[~per_cover, "p"])
    t.to_csv(TAB / "alarm_paired.csv", index=False, float_format="%.4g")
    FINDINGS["alarm"] = {f"{r.policy}-{r.cover}": dict(
        off=round(r.late_mean_off, 1), on=round(r.late_mean_on, 1), diff=round(r.late_mean_diff, 1),
        ci=[round(r.late_mean_ci_lo, 1), round(r.late_mean_ci_hi, 1)], r=round(r.r, 2),
        p_holm=float(f"{r.p_holm:.3g}"), births=[round(r.births_off), round(r.births_on)],
        captures=[round(r.captures_off), round(r.captures_on)],
        forage=[round(r.share_forage_off, 3), round(r.share_forage_on, 3)]) for _, r in t.iterrows()}
    return t


def fig_alarm(t):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.3), gridspec_kw=dict(width_ratios=[1.25, 1]))
    ax = axes[0]
    tt = t[t.cover == "all"].set_index("policy").loc[POLICIES]
    y = np.arange(len(POLICIES))[::-1]
    for yi, p in zip(y, POLICIES):
        r = tt.loc[p]
        ax.plot([r.late_mean_off, r.late_mean_on], [yi, yi], color=COLOR[p], lw=1.5)
        ax.scatter(r.late_mean_off, yi, s=30, facecolor="white", edgecolor=COLOR[p], lw=1.4, zorder=3)
        ax.scatter(r.late_mean_on, yi, s=30, color=COLOR[p], zorder=3)
    ax.set_yticks(y, [LABEL[p] for p in POLICIES])
    ax.set_xlabel("late mean population (patchy, all cover levels)")
    ax.grid(axis="y", visible=False)
    ax.scatter([], [], s=30, facecolor="white", edgecolor=INK_SOFT, label="alarm off")
    ax.scatter([], [], s=30, color=INK_SOFT, label="alarm on")
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 0.1), handletextpad=0.2)
    ax.set_title("Population, alarm off vs on", fontsize=8.5)

    ax = axes[1]
    r = tt.loc["flee"]
    vals = [("births", r.births_diff, r.births_ci_lo, r.births_ci_hi),
            ("captures", r.captures_diff, r.captures_ci_lo, r.captures_ci_hi)]
    for k, (lab, m, lo, hi) in enumerate(vals):
        ax.bar(k, m, width=0.55, color=COLOR["flee"] + ("ff" if k == 0 else "80"), edgecolor=COLOR["flee"])
        ax.errorbar(k, m, yerr=[[m - lo], [hi - m]], color=INK, capsize=3, lw=1)
    ax.axhline(0, color=INK_SOFT, lw=0.8)
    ax.set_xticks([0, 1], ["births", "captures"])
    ax.set_ylabel("change per run (on − off)")
    ax.set_title("Flee policy: what the alarm changes", fontsize=8.5)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    save(fig, "fig_social_alarm")


# ----------------------------------------------------------------------------- sensitivity
def sensitivity():
    files = sorted((RES / "sensitivity").glob("*.csv"))
    if not files:
        return None
    frames = []
    for f in files:
        d = load(f)
        case, cover, arr = f.stem.split("_")[0], f.stem.split("_")[-2], f.stem.split("_")[-1]
        case = f.stem.rsplit("_", 2)[0]
        d["case"] = case
        frames.append(d)
    s = pd.concat(frames, ignore_index=True)
    s["env"] = s.arrangement + ", " + s.cover
    rows = []
    for (case, env), g in s.groupby(["case", "env"]):
        means = g.groupby("policy").late_mean.mean().reindex(POLICIES)
        rows.append(dict(case=case, env=env, n_per_policy=int(g.groupby("policy").size().min()),
                         best=means.idxmax(), **{p: means[p] for p in POLICIES}))
    t = pd.DataFrame(rows)
    # rank agreement with the default case (Kendall tau over the 6 policy means)
    for env in t.env.unique():
        base = t[(t.env == env) & (t.case == "default")][POLICIES].values[0]
        for i in t.index[t.env == env]:
            t.loc[i, "kendall_tau_vs_default"] = stats.kendalltau(base, t.loc[i, POLICIES].values.astype(float))[0]
    t.to_csv(TAB / "sensitivity.csv", index=False, float_format="%.3f")
    FINDINGS["sensitivity"] = {f"{r.case}|{r.env}": dict(best=r.best, tau=round(r.kendall_tau_vs_default, 2),
                                                        **{p: round(r[p], 1) for p in POLICIES})
                               for _, r in t.iterrows()}
    return t


def fig_sensitivity(t):
    envs = ["uniform, low", "patchy, medium"]
    cases = ["default",
             "hide-detection-multiplier_0.05", "hide-detection-multiplier_0.3",
             "motion-detection-multiplier_1.0", "motion-detection-multiplier_2.0",
             "calm-down-time_10", "calm-down-time_40", "handling-time_10", "handling-time_30",
             "alarm-radius_2.5", "alarm-radius_5", "alarm-radius_10"]
    cases = [c for c in cases if c in set(t.case)]
    nice = {c: c.replace("_", " = ").replace("detection-multiplier", "mult.") for c in cases}
    nice["default"] = "default"
    for c in cases:
        if c.startswith("alarm-radius"):
            nice[c] += " (alarm on)"
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), sharey=True)
    y = np.arange(len(cases))[::-1]
    for ax, env in zip(axes, envs):
        sub = t[t.env == env].set_index("case")
        for yi, c in zip(y, cases):
            if c not in sub.index:
                continue
            for p in POLICIES:
                ax.scatter(sub.loc[c, p], yi, s=22, color=COLOR[p], marker="o" if p != "experimental-assigned" else "s",
                           edgecolor="white", lw=0.5, zorder=3)
        ax.set_title(env + " cover", fontsize=8.5)
        ax.set_xlabel("late mean population (10 seeds)")
        ax.grid(axis="y", visible=False)
        ax.axhspan(y[0] - 0.5, y[0] + 0.5, color="#f3f2ef", zorder=0)
    axes[0].set_yticks(y, [nice[c] for c in cases])
    handles = [plt.Line2D([], [], marker="o" if p != "experimental-assigned" else "s", ls="", color=COLOR[p], ms=5)
               for p in POLICIES]
    fig.legend(handles, [LABEL[p] for p in POLICIES], loc="lower center", bbox_to_anchor=(0.6, 0.98), ncol=6)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "fig_sensitivity")


# ----------------------------------------------------------------------------- main
def main():
    for d in (TAB, FIG):
        d.mkdir(parents=True, exist_ok=True)
    style()
    sweep = load(RES / "environment-sweep.csv")
    summ, pairs = environment_sweep(sweep)
    fig_timeseries(sweep)
    fig_boxes(sweep)
    fig_hide_flee(pairs)
    fig_extinction(sweep)
    if (RES / "social-alarm.csv").exists():
        sa = load(RES / "social-alarm.csv")
        t = social_alarm(sa, sweep)
        fig_alarm(t)
    st = sensitivity()
    if st is not None:
        fig_sensitivity(st)
    (OUT / "findings.json").write_text(json.dumps(FINDINGS, indent=1, default=str))
    print(json.dumps(FINDINGS, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
