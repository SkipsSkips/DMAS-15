"""Analysis of the octoplus main factorial.

Produces the tables and figures for the report. Every number written to
analysis/tables is derived here from the raw BehaviorSpace CSV, so the
report can be regenerated from the data with one command.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

import stats_core as sc
import figstyle as fs
from load import (load_table, check_pairing, STRATEGY_ORDER,
                  COVER_ORDER, ARRANGEMENT_ORDER, CELL)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAB = os.path.join(ROOT, "analysis", "tables")
FIG = os.path.join(ROOT, "analysis", "figures")
os.makedirs(TAB, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

fs.apply_base_style()
DIVERGING_CMAP = LinearSegmentedColormap.from_list("adv", fs.DIVERGING)
SEQ_CMAP = LinearSegmentedColormap.from_list("seq", fs.SEQUENTIAL)

FINDINGS = {}


def save(fig, name):
    path = os.path.join(FIG, name)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("  figure:", name)


def write(df, name, **kw):
    path = os.path.join(TAB, name)
    df.to_csv(path, index=kw.pop("index", False), **kw)
    print("  table: ", name)


# ====================================================================
# 1. Integrity checks on the raw data
# ====================================================================
def integrity(df):
    print("\n[1] Data integrity")
    issues = []

    expected = 4 * 3 * 3 * 3 * 3 * 30
    if len(df) != expected:
        issues.append(f"row count {len(df)} != expected {expected}")

    spread, bad = check_pairing(df)
    print(f"  seed reproduces environment: max spread {spread:.2e} "
          f"across {bad} cells")
    if spread > 1e-9:
        issues.append("seeds do not reproduce identical environments")

    # Realised cover must track the declared target, or cover amount and
    # cover arrangement are not independent factors.
    targets = {"low": 0.15, "medium": 0.45, "high": 0.75}
    cov = (df.groupby(["cover", "arrangement"], observed=True)["cover_mean"]
             .agg(["mean", "std", "min", "max"]).reset_index())
    cov["target"] = cov["cover"].map(targets).astype(float)
    cov["abs_error"] = (cov["mean"] - cov["target"]).abs()
    write(cov, "01_environment_realisation.csv")
    worst = cov["abs_error"].max()
    print(f"  worst |realised - target| cover: {worst:.4f}")
    if worst > 0.02:
        issues.append(f"cover normalisation off by {worst:.3f}")

    # Bounds
    for col, lo, hi in [("survival", 0, 100), ("population_index", 0, 100),
                        ("evenness", 0, 1), ("exp_hide", 0, 1)]:
        if col in df and (df[col].min() < lo - 1e-9 or df[col].max() > hi + 1e-9):
            issues.append(f"{col} out of [{lo},{hi}]")

    # With reproduction off, the founder cohort is the whole population.
    if "population_index" in df:
        delta = (df["survival"] - df["population_index"]).abs().max()
        print(f"  founder survival == population index: max |diff| {delta:.2e}")
        if delta > 1e-9:
            issues.append("founder and population measures diverge")

    # Cell balance
    counts = df.groupby(CELL[:-1] + ["strategy"], observed=True).size()
    print(f"  runs per (cell, strategy): min {counts.min()}, max {counts.max()}")
    if counts.min() != 30 or counts.max() != 30:
        issues.append("unbalanced design")

    FINDINGS["integrity_issues"] = issues
    print("  ->", "PASS" if not issues else f"ISSUES: {issues}")
    return issues


# ====================================================================
# 2. Descriptive comparison of strategies
# ====================================================================
def descriptives(df):
    print("\n[2] Strategy performance")
    rows = []
    for (strat, cover, arr), g in df.groupby(
            ["strategy", "cover", "arrangement"], observed=True):
        point, lo, hi = sc.bootstrap_ci(g["survival"].values)
        rows.append(dict(
            strategy=strat, cover=cover, arrangement=arr, n=len(g),
            survival_mean=point, ci_lo=lo, ci_hi=hi,
            survival_median=float(np.median(g["survival"])),
            mean_survival_ticks=float(g["mean_survival_ticks"].mean()),
            extinction_pct=100.0 * float(g["went_extinct"].mean()),
            predator_efficiency=float(g["predator_efficiency"].mean()),
        ))
    table = pd.DataFrame(rows)
    write(table, "02_survival_by_condition.csv")

    overall = []
    for strat, g in df.groupby("strategy", observed=True):
        point, lo, hi = sc.bootstrap_ci(g["survival"].values)
        overall.append(dict(strategy=strat, n=len(g), survival_mean=point,
                            ci_lo=lo, ci_hi=hi,
                            extinction_pct=100 * float(g["went_extinct"].mean())))
    overall = pd.DataFrame(overall).sort_values("survival_mean", ascending=False)
    write(overall, "03_survival_overall.csv")
    print(overall.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    FINDINGS["overall_ranking"] = overall.to_dict("records")
    return table, overall


# ====================================================================
# 3. Paired comparisons between strategies
# ====================================================================
def paired_comparisons(df):
    print("\n[3] Paired strategy comparisons (matched on seed)")
    wide = df.pivot_table(index=CELL, columns="strategy",
                          values="survival", observed=True)
    rows = []
    for a in STRATEGY_ORDER:
        for b in STRATEGY_ORDER:
            if a >= b or a not in wide or b not in wide:
                continue
            res = sc.paired_test(wide[a].values, wide[b].values)
            d = sc.cliffs_delta(wide[a].values, wide[b].values)
            rows.append(dict(strategy_a=a, strategy_b=b, **res,
                             cliffs_delta=d, magnitude=sc.delta_magnitude(d)))
    out = pd.DataFrame(rows)
    out["p_holm"] = sc.holm_correct(out["p"].values)
    write(out, "04_paired_overall.csv")
    print(out[["strategy_a", "strategy_b", "median_diff", "cliffs_delta",
               "magnitude", "p_holm"]].to_string(
        index=False, float_format=lambda v: f"{v:.4g}"))

    # The same comparison inside each environment, which is where the
    # interesting reversals live.
    rows = []
    for (cover, arr), g in df.groupby(["cover", "arrangement"], observed=True):
        w = g.pivot_table(index=CELL, columns="strategy",
                          values="survival", observed=True)
        for a in STRATEGY_ORDER:
            for b in STRATEGY_ORDER:
                if a >= b or a not in w or b not in w:
                    continue
                res = sc.paired_test(w[a].values, w[b].values)
                d = sc.cliffs_delta(w[a].values, w[b].values)
                rows.append(dict(cover=cover, arrangement=arr,
                                 strategy_a=a, strategy_b=b, **res,
                                 cliffs_delta=d,
                                 magnitude=sc.delta_magnitude(d)))
    per_env = pd.DataFrame(rows)
    per_env["p_holm"] = sc.holm_correct(per_env["p"].values)
    write(per_env, "05_paired_by_environment.csv")
    return out, per_env


# ====================================================================
# 4. How much does each factor actually matter?
# ====================================================================
def variance_decomposition(df):
    print("\n[4] Variance explained (omega-squared) on founder survival")
    rows = []
    for factor in ["strategy", "cover", "arrangement",
                   "prey_speed", "pred_speed"]:
        groups = [g["survival"].values
                  for _, g in df.groupby(factor, observed=True)]
        rows.append(dict(factor=factor, levels=len(groups),
                         omega_squared=sc.omega_squared(groups)))
    # The speed ratio is the mechanistically meaningful combination of
    # the two speed factors, so it is reported alongside them.
    ratio = df.assign(ratio=(df["pred_speed"] / df["prey_speed"]).round(3))
    rows.append(dict(factor="pred/prey speed ratio",
                     levels=ratio["ratio"].nunique(),
                     omega_squared=sc.omega_squared(
                         [g["survival"].values
                          for _, g in ratio.groupby("ratio")])))
    out = pd.DataFrame(rows).sort_values("omega_squared", ascending=False)
    write(out, "06_variance_explained.csv")
    print(out.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    FINDINGS["variance_explained"] = out.to_dict("records")
    return out


# ====================================================================
# 5. The hide-versus-flee boundary
# ====================================================================
def boundary(df):
    print("\n[5] Hide vs flee boundary")
    w = df.pivot_table(index=CELL, columns="strategy",
                       values="survival", observed=True).reset_index()
    w["hide_advantage"] = w["hide"] - w["flee"]
    cells = (w.groupby(["cover", "prey_speed", "pred_speed"], observed=True)
              ["hide_advantage"].agg(["mean", "std", "count"]).reset_index())
    write(cells, "07_hide_vs_flee_boundary.csv")

    # Where does the sign flip?
    flips = cells[cells["mean"].abs() < 5]
    FINDINGS["boundary_near_zero_cells"] = len(flips)
    print(f"  cells where |hide - flee| < 5 points: {len(flips)} "
          f"of {len(cells)}")
    print(cells.groupby("cover", observed=True)["mean"].mean()
             .to_string(float_format=lambda v: f"{v:+.2f}"))
    return w, cells


# ====================================================================
# 6. Survival analysis on time to population extinction
# ====================================================================
def survival_analysis(df):
    print("\n[6] Time-to-extinction (Kaplan-Meier, right-censored)")
    rows = []
    curves = {}
    for strat, g in df.groupby("strategy", observed=True):
        xs, ys = sc.kaplan_meier(g["event_time"].values,
                                 g["went_extinct"].values)
        curves[strat] = (xs, ys)
        rows.append(dict(strategy=strat, n=len(g),
                         extinct_pct=100 * float(g["went_extinct"].mean()),
                         median_extinction=float(
                             np.median(g.loc[g["went_extinct"],
                                             "event_time"]))
                         if g["went_extinct"].any() else np.nan,
                         survival_at_limit=float(ys[-1])))
    km = pd.DataFrame(rows)
    write(km, "08_kaplan_meier_summary.csv")

    pairs = []
    for i, a in enumerate(STRATEGY_ORDER):
        for b in STRATEGY_ORDER[i + 1:]:
            ga = df[df["strategy"] == a]
            gb = df[df["strategy"] == b]
            chi2, p = sc.logrank(ga["event_time"].values,
                                 ga["went_extinct"].values,
                                 gb["event_time"].values,
                                 gb["went_extinct"].values)
            pairs.append(dict(strategy_a=a, strategy_b=b, chi2=chi2, p=p))
    lr = pd.DataFrame(pairs)
    lr["p_holm"] = sc.holm_correct(lr["p"].values)
    write(lr, "09_logrank_tests.csv")
    print(km.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    return km, curves, lr


# ====================================================================
# 7. Did the adaptive policy behave adaptively?
# ====================================================================
def adaptivity(df):
    print("\n[7] Adaptive policy behaviour")
    ad = df[df["strategy"] == "adaptive-dmas"]
    mix = (ad.groupby(["cover", "arrangement"], observed=True)
             [["exp_hide", "exp_flee", "exp_still", "exp_seek", "evenness"]]
             .mean().reset_index())
    write(mix, "10_adaptive_behaviour_mix.csv")
    print(mix.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    # Does the adaptive policy shift towards hiding as cover rises?
    corr = ad[["cover_mean", "exp_hide", "exp_flee", "exp_still"]].corr(
        numeric_only=True)["cover_mean"].drop("cover_mean")
    FINDINGS["adaptive_cover_correlation"] = corr.to_dict()
    print("  correlation of behaviour share with realised cover:")
    print(corr.to_string(float_format=lambda v: f"{v:+.3f}"))

    # Was the adaptive policy ever the best available choice?
    w = df.pivot_table(index=CELL, columns="strategy",
                       values="survival", observed=True)
    best = w.idxmax(axis=1)
    share = best.value_counts(normalize=True).mul(100).rename("pct_of_cells")
    share = share.reset_index()
    share.columns = ["strategy", "pct_of_cells_where_best"]
    write(share, "11_best_strategy_share.csv")
    print(share.to_string(index=False, float_format=lambda v: f"{v:.1f}"))
    FINDINGS["best_strategy_share"] = share.to_dict("records")
    return mix, share


# ====================================================================
# 8. Figures
# ====================================================================
def fig_survival_grid(table):
    """Survival by strategy across the nine environments.

    Form: grouped bars with bootstrap CIs. The job is comparing
    magnitudes across a small categorical set, which is what bars do
    best; the CI whiskers carry the uncertainty that a bare bar hides.
    """
    covers = [c for c in COVER_ORDER if c in set(table["cover"])]
    arrs = [a for a in ARRANGEMENT_ORDER if a in set(table["arrangement"])]
    fig, axes = plt.subplots(len(covers), len(arrs),
                             figsize=(10.5, 8.2), sharey=True, sharex=True)
    for i, cover in enumerate(covers):
        for j, arr in enumerate(arrs):
            ax = axes[i][j]
            sub = table[(table["cover"] == cover) &
                        (table["arrangement"] == arr)]
            sub = sub.set_index("strategy").reindex(STRATEGY_ORDER).dropna(
                subset=["survival_mean"])
            xs = np.arange(len(sub))
            colors = [fs.STRATEGY_COLOR[s] for s in sub.index]
            bars = ax.bar(xs, sub["survival_mean"], width=0.62,
                          color=colors, edgecolor=fs.SURFACE, linewidth=1.6)
            for b in bars:
                b.set_capstyle("round")
            ax.errorbar(xs, sub["survival_mean"],
                        yerr=[sub["survival_mean"] - sub["ci_lo"],
                              sub["ci_hi"] - sub["survival_mean"]],
                        fmt="none", ecolor=fs.INK_SOFT, elinewidth=1.2,
                        capsize=3, capthick=1.2)
            # Direct labels: the relief rule for the low-contrast slots.
            for x, v in zip(xs, sub["survival_mean"]):
                ax.text(x, v + 2.2, f"{v:.0f}", ha="center", va="bottom",
                        fontsize=8, color=fs.INK_SOFT)
            ax.set_xticks(xs)
            ax.set_xticklabels([fs.STRATEGY_LABEL[s] for s in sub.index],
                               fontsize=8)
            ax.set_ylim(0, 100)
            ax.grid(axis="x", visible=False)
            fs.strip_spines(ax)
            if i == 0:
                ax.set_title(f"{arr} cover", fontsize=9.5,
                             color=fs.INK_SOFT, pad=8)
            if j == 0:
                ax.set_ylabel("survival (%)", fontsize=8.5)
            if j == len(arrs) - 1:
                ax.text(1.04, 0.5, f"{cover} cover", transform=ax.transAxes,
                        rotation=270, ha="left", va="center",
                        fontsize=9.5, color=fs.INK_SOFT)
    fs.title_block(
        fig, "Which strategy survives, and where",
        "Founder survival after 500 ticks. Bars are means over 270 runs "
        "per cell; whiskers are 95% bootstrap CIs.")
    fs.source_note(
        fig, "octoplus main-factorial: 9,720 runs · reproduction disabled · "
             "30 seeds per condition")
    fig.subplots_adjust(top=0.88, bottom=0.06, hspace=0.25, wspace=0.08)
    save(fig, "fig01_survival_grid.png")


def fig_boundary(cells):
    """Hide-minus-flee advantage over the speed plane.

    Form: heatmap, because the data is a dense two-factor grid and the
    question is where a signed quantity changes sign. Diverging blue to
    red with a neutral midpoint, so zero reads as "no advantage".
    """
    covers = [c for c in COVER_ORDER if c in set(cells["cover"])]
    fig, axes = plt.subplots(1, len(covers), figsize=(11, 3.9),
                             sharey=True)
    vmax = float(np.nanmax(np.abs(cells["mean"])))
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    for ax, cover in zip(np.atleast_1d(axes), covers):
        sub = cells[cells["cover"] == cover]
        grid = sub.pivot(index="pred_speed", columns="prey_speed",
                         values="mean").sort_index(ascending=False)
        im = ax.imshow(grid.values, cmap=DIVERGING_CMAP.reversed(),
                       norm=norm, aspect="auto")
        ax.set_xticks(range(len(grid.columns)),
                      [f"{c:g}" for c in grid.columns])
        ax.set_yticks(range(len(grid.index)),
                      [f"{r:g}" for r in grid.index])
        for yi in range(grid.shape[0]):
            for xi in range(grid.shape[1]):
                v = grid.values[yi, xi]
                ax.text(xi, yi, f"{v:+.0f}", ha="center", va="center",
                        fontsize=8.5,
                        color=fs.SURFACE if abs(v) > vmax * 0.55 else fs.INK)
        ax.set_title(f"{cover} cover", fontsize=9.5, color=fs.INK_SOFT, pad=8)
        ax.set_xlabel("prey speed")
        ax.grid(visible=False)
        ax.tick_params(length=0)
        fs.strip_spines(ax, keep=())
    np.atleast_1d(axes)[0].set_ylabel("predator speed")
    cbar = fig.colorbar(im, ax=list(np.atleast_1d(axes)), fraction=0.03,
                        pad=0.02)
    cbar.set_label("hide advantage over flee\n(survival % points)",
                   fontsize=8.5, color=fs.INK_SOFT)
    cbar.outline.set_visible(False)
    worst = float(cells["mean"].min())
    best = float(cells["mean"].max())
    fs.title_block(
        fig, "Hiding never beats fleeing anywhere in the factorial",
        f"Every cell is negative: the advantage runs from {best:+.0f} to "
        f"{worst:+.0f} survival points against hiding. Paired on seed, so "
        "each cell compares the two strategies in identical worlds.")
    fs.source_note(fig, "octoplus main-factorial · 30 seeds per cell "
                        "· arrangements pooled")
    fig.subplots_adjust(top=0.78, bottom=0.14)
    save(fig, "fig02_hide_flee_boundary.png")


def fig_kaplan_meier(curves, km):
    """Time-to-extinction curves.

    Form: step lines, because a survival function is a step function and
    drawing it smoothly would misrepresent when the drops happen.
    """
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    endpoints = []
    for strat in STRATEGY_ORDER:
        if strat not in curves:
            continue
        xs, ys = curves[strat]
        xs = np.append(xs, 500)
        ys = np.append(ys, ys[-1])
        ax.step(xs, ys * 100, where="post",
                color=fs.STRATEGY_COLOR[strat], linewidth=2.0,
                label=fs.STRATEGY_LABEL[strat], solid_capstyle="round")
        endpoints.append([ys[-1] * 100, strat])

    # Nudge labels apart where curves finish close together, so the
    # direct labels stay readable without moving the data.
    endpoints.sort()
    min_gap = 3.6
    for i in range(1, len(endpoints)):
        if endpoints[i][0] - endpoints[i - 1][0] < min_gap:
            endpoints[i][0] = endpoints[i - 1][0] + min_gap
    for y, strat in endpoints:
        ax.text(508, y, fs.STRATEGY_LABEL[strat], va="center",
                fontsize=8.5, color=fs.STRATEGY_COLOR[strat])
    ax.set_xlim(0, 560)
    ax.set_ylim(0, 102)
    ax.set_xlabel("tick")
    ax.set_ylabel("populations still alive (%)")
    ax.grid(axis="x", visible=False)
    fs.strip_spines(ax)
    ax.legend(loc="lower left", ncol=4)
    fs.title_block(
        fig, "How long does a population last?",
        "Kaplan-Meier estimate of time to total extinction. Runs that "
        "ended with prey alive are right-censored, not counted as deaths.")
    fs.source_note(fig, "octoplus main-factorial · 2,430 runs per strategy")
    fig.subplots_adjust(top=0.82, bottom=0.13)
    save(fig, "fig03_time_to_extinction.png")


def fig_variance(var):
    """What actually drives the outcome.

    Form: horizontal bars — one measure, few categories, long labels.
    """
    var = var.sort_values("omega_squared")
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    ys = np.arange(len(var))
    ax.barh(ys, var["omega_squared"], height=0.58,
            color=fs.SLOT[0], edgecolor=fs.SURFACE, linewidth=1.4)
    for y, v in zip(ys, var["omega_squared"]):
        ax.text(v + 0.006, y, f"{v:.3f}", va="center", fontsize=8.5,
                color=fs.INK_SOFT)
    ax.set_yticks(ys, var["factor"])
    ax.set_xlabel("variance in founder survival explained (omega squared)")
    ax.set_xlim(0, max(0.1, float(var["omega_squared"].max()) * 1.25))
    ax.grid(axis="y", visible=False)
    fs.strip_spines(ax)
    fs.title_block(fig, "What decides survival",
                   "Single-factor omega squared. Values are small because "
                   "most variance sits in seed-to-seed noise and interactions.")
    fs.source_note(fig, "octoplus main-factorial · 9,720 runs")
    fig.subplots_adjust(top=0.76, bottom=0.18, left=0.28)
    save(fig, "fig04_variance_explained.png")


def fig_adaptive_mix(mix):
    """What the adaptive policy actually did.

    Form: stacked bars of a parts-of-a-whole quantity that sums to 1,
    with a 2px surface gap between segments.
    """
    mix = mix.copy()
    mix["label"] = (mix["cover"].astype(str) + "\n" +
                    mix["arrangement"].astype(str))
    parts = [("exp_still", "Still", fs.STRATEGY_COLOR["still"]),
             ("exp_hide", "Hide", fs.STRATEGY_COLOR["hide"]),
             ("exp_flee", "Flee", fs.STRATEGY_COLOR["flee"]),
             ("exp_seek", "Seek cover", fs.SLOT[0])]
    fig, ax = plt.subplots(figsize=(9.6, 4.2))
    xs = np.arange(len(mix))
    bottom = np.zeros(len(mix))
    for col, label, color in parts:
        vals = mix[col].values * 100
        ax.bar(xs, vals, bottom=bottom, width=0.66, label=label,
               color=color, edgecolor=fs.SURFACE, linewidth=2.0)
        for x, v, b in zip(xs, vals, bottom):
            if v > 6:
                ax.text(x, b + v / 2, f"{v:.0f}", ha="center", va="center",
                        fontsize=7.5, color=fs.SURFACE, fontweight="semibold")
        bottom += vals
    ax.set_xticks(xs, mix["label"], fontsize=8)
    ax.set_ylabel("share of prey-ticks (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="x", visible=False)
    fs.strip_spines(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4)
    fs.title_block(
        fig, "What the adaptive policy actually did",
        "Share of prey-ticks spent in each action. Exposure, not decision "
        "count: risk accrues per tick, not per decision.")
    fs.source_note(fig, "octoplus main-factorial · adaptive runs only "
                        "· 2,430 runs")
    fig.subplots_adjust(top=0.80, bottom=0.25)
    save(fig, "fig05_adaptive_behaviour.png")


# ====================================================================
# 9. The speed boundary
#
#    The factorial's speed window only reaches a predator/prey ratio
#    of 2.5. This experiment sweeps both speeds from 0.2 to 1.4, which
#    is wide enough to contain the crossover.
# ====================================================================
def speed_boundary(path):
    print("\n[9] Speed boundary (wide grid)")
    df = load_table(path)
    print(f"  {len(df)} runs")

    w = df.pivot_table(index=CELL, columns="strategy",
                       values="survival", observed=True).reset_index()
    w["hide_advantage"] = w["hide"] - w["flee"]
    cells = (w.groupby(["arrangement", "prey_speed", "pred_speed"],
                       observed=True)["hide_advantage"]
              .agg(["mean", "std", "count"]).reset_index())
    write(cells, "12_speed_boundary_wide.csv")
    wins = cells[cells["mean"] > 0]
    print(f"  cells where hiding wins: {len(wins)} of {len(cells)}")

    # The mechanistically meaningful quantity is the speed ratio, not
    # either speed alone: fleeing works exactly when prey can keep
    # distance, which depends on predator speed relative to prey speed.
    cells = cells.assign(ratio=(cells["pred_speed"] /
                                cells["prey_speed"]).round(3))
    by_ratio = (cells.groupby("ratio")["mean"]
                     .agg(["mean", "count"]).reset_index()
                     .rename(columns={"mean": "hide_advantage"}))
    write(by_ratio, "13_hide_advantage_by_speed_ratio.csv")
    positive = by_ratio[by_ratio["hide_advantage"] > 0]
    if len(positive):
        threshold = float(positive["ratio"].min())
        print(f"  hiding first wins at predator/prey speed ratio "
              f">= {threshold:g}")
        FINDINGS["hide_wins_speed_ratio_threshold"] = threshold

    pooled = (cells.groupby(["prey_speed", "pred_speed"])["mean"]
                   .mean().reset_index())
    grid = pooled.pivot(index="pred_speed", columns="prey_speed",
                        values="mean").sort_index(ascending=False)
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    vmax = float(np.nanmax(np.abs(grid.values)))
    im = ax.imshow(grid.values, cmap=DIVERGING_CMAP.reversed(),
                   norm=TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax),
                   aspect="auto")
    ax.set_xticks(range(len(grid.columns)), [f"{c:g}" for c in grid.columns])
    ax.set_yticks(range(len(grid.index)), [f"{r:g}" for r in grid.index])
    for yi in range(grid.shape[0]):
        for xi in range(grid.shape[1]):
            v = grid.values[yi, xi]
            ax.text(xi, yi, f"{v:+.0f}", ha="center", va="center", fontsize=8,
                    color=fs.SURFACE if abs(v) > vmax * 0.55 else fs.INK)
    ax.set_xlabel("prey speed"); ax.set_ylabel("predator speed")
    ax.grid(visible=False); ax.tick_params(length=0)
    fs.strip_spines(ax, keep=())
    # Mark the window the factorial actually sampled.
    fx = [i for i, c in enumerate(grid.columns) if 0.4 <= c <= 0.8]
    fy = [i for i, r in enumerate(grid.index) if 0.6 <= r <= 1.0]
    if fx and fy:
        ax.add_patch(plt.Rectangle(
            (min(fx) - 0.5, min(fy) - 0.5), len(fx), len(fy),
            fill=False, edgecolor=fs.INK, linewidth=1.8,
            linestyle=(0, (5, 3))))
        ax.text(min(fx) - 0.45, min(fy) - 0.62, "main factorial window",
                fontsize=7.5, color=fs.INK, va="bottom")
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    cbar.set_label("hide advantage over flee (survival % points)",
                   fontsize=8.5, color=fs.INK_SOFT)
    cbar.outline.set_visible(False)
    fs.title_block(
        fig, "The boundary exists — just outside the sampled window",
        "Hiding wins only where prey are near-immobile relative to the "
        "predator (top-left). The factorial never sampled that corner.")
    fs.source_note(fig, "octoplus speed-boundary · 4,410 runs · "
                        "medium cover · arrangements pooled")
    fig.subplots_adjust(top=0.78, bottom=0.12)
    save(fig, "fig06_speed_boundary.png")
    return cells


# ====================================================================
# Main
# ====================================================================
def main(path):
    print(f"Loading {path}")
    df = load_table(path)
    print(f"  {len(df)} runs, {df['seed'].nunique()} seeds")

    integrity(df)
    table, overall = descriptives(df)
    paired_comparisons(df)
    var = variance_decomposition(df)
    w, cells = boundary(df)
    km, curves, lr = survival_analysis(df)
    mix, share = adaptivity(df)

    print("\n[8] Figures")
    fig_survival_grid(table)
    fig_boundary(cells)
    fig_kaplan_meier(curves, km)
    fig_variance(var)
    fig_adaptive_mix(mix)

    sb = os.path.join(ROOT, "results", "speed-boundary.csv")
    from load import resolve
    sb = resolve(sb)
    if os.path.exists(sb):
        speed_boundary(sb)
    else:
        print("\n[9] speed-boundary results not present; skipping")

    with open(os.path.join(TAB, "findings.json"), "w") as fh:
        json.dump(FINDINGS, fh, indent=2, default=str)
    print("\nDone.")


if __name__ == "__main__":
    from load import resolve
    main(sys.argv[1] if len(sys.argv) > 1
         else resolve(os.path.join(ROOT, "results", "main-factorial.csv")))
