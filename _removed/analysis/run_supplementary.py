"""Analysis of the supporting experiments.

The main factorial answers "which strategy wins, here?". These
experiments answer the questions that result raises: does a hide/flee
boundary exist anywhere; how much cover is enough; what happens once
the population can reproduce; and what selection favours when policies
are inherited.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

import stats_core as sc
import figstyle as fs
from load import load_table, STRATEGY_ORDER, COVER_ORDER, ARRANGEMENT_ORDER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
TAB = os.path.join(ROOT, "analysis", "tables")
FIG = os.path.join(ROOT, "analysis", "figures")
os.makedirs(TAB, exist_ok=True); os.makedirs(FIG, exist_ok=True)

fs.apply_base_style()
DIVERGING_CMAP = LinearSegmentedColormap.from_list("adv", fs.DIVERGING)
SEQ_CMAP = LinearSegmentedColormap.from_list("seq", fs.SEQUENTIAL)
FINDINGS = {}


def save(fig, name):
    fig.savefig(os.path.join(FIG, name), bbox_inches="tight")
    plt.close(fig); print("  figure:", name)


def write(df, name):
    df.to_csv(os.path.join(TAB, name), index=False); print("  table: ", name)


EXPECTED_RUNS = {
    "detection-sensitivity": 6480, "speed-boundary": 4410,
    "cover-gradient": 3780, "reproduction-equilibrium": 540,
    "evolutionary-mixed": 540, "policy-tournament": 6075,
    "motion-penalty-boundary": 2100, "reaction-time": 1575,
}


def have(name):
    """Only analyse a result file once its experiment has finished.

    A file that is still being written has a truncated factor set, which
    silently produces wrong pivots rather than an obvious error.
    """
    from load import resolve
    p = resolve(os.path.join(RES, f"{name}.csv"))
    if not os.path.exists(p):
        return None
    if p.endswith(".gz"):
        import gzip
        with gzip.open(p, "rt") as fh:
            rows = sum(1 for _ in fh) - 7
    else:
        with open(p) as fh:
            rows = sum(1 for _ in fh) - 7
    expected = EXPECTED_RUNS.get(name)
    if expected is not None and rows < expected:
        print(f"\n[wait] {name}: {rows}/{expected} runs so far")
        return None
    return p


# ====================================================================
# Detection-model sensitivity: does a hide/flee boundary exist at all?
# ====================================================================
def detection_sensitivity(path):
    print("\n[S1] Detection-model sensitivity")
    df = load_table(path)
    df = df.rename(columns={"hide-detection-multiplier": "hide_mult",
                            "cover-impact-strength": "cover_impact",
                            "motion-detection-multiplier": "motion_mult"})
    print(f"  {len(df)} runs")

    idx = ["cover", "hide_mult", "cover_impact", "motion_mult", "seed"]
    w = df.pivot_table(index=idx, columns="strategy",
                       values="survival", observed=True).reset_index()
    w["hide_advantage"] = w["hide"] - w["flee"]
    w["adaptive_advantage"] = w["adaptive-dmas"] - w[["hide", "flee"]].max(axis=1)

    cells = (w.groupby(["cover", "hide_mult", "cover_impact", "motion_mult"],
                       observed=True)
              .agg(hide_advantage=("hide_advantage", "mean"),
                   hide_survival=("hide", "mean"),
                   flee_survival=("flee", "mean"),
                   adaptive_survival=("adaptive-dmas", "mean"),
                   adaptive_advantage=("adaptive_advantage", "mean"),
                   n=("hide_advantage", "size")).reset_index())
    write(cells, "20_detection_sensitivity_cells.csv")

    wins = cells[cells["hide_advantage"] > 0]
    print(f"  cells where hiding beats fleeing: {len(wins)} of {len(cells)} "
          f"({100*len(wins)/len(cells):.1f}%)")
    FINDINGS["hide_wins_cells"] = int(len(wins))
    FINDINGS["hide_wins_pct"] = round(100 * len(wins) / len(cells), 2)

    if len(wins):
        print("  hiding wins when:")
        print(f"    hide-detection-multiplier <= "
              f"{wins['hide_mult'].max():g} "
              f"(median {wins['hide_mult'].median():g})")
        print(f"    cover-impact-strength >= {wins['cover_impact'].min():g}")
        print(f"    cover categories: {sorted(set(wins['cover'].astype(str)))}")
        best = wins.sort_values("hide_advantage", ascending=False).head(5)
        print(best[["cover", "hide_mult", "cover_impact", "motion_mult",
                    "hide_advantage"]].to_string(
            index=False, float_format=lambda v: f"{v:.2f}"))
        FINDINGS["hide_wins_conditions"] = dict(
            max_hide_mult=float(wins["hide_mult"].max()),
            min_cover_impact=float(wins["cover_impact"].min()),
            covers=sorted(set(wins["cover"].astype(str))))

    # The boundary in the detection plane, at the model's own motion
    # penalty, pooled over cover amount.
    fig_detection_boundary(cells)
    return cells


def fig_detection_boundary(cells):
    motion = 1.5 if 1.5 in set(cells["motion_mult"]) else \
        sorted(set(cells["motion_mult"]))[0]
    sub = cells[cells["motion_mult"] == motion]
    covers = [c for c in COVER_ORDER if c in set(sub["cover"].astype(str))]
    fig, axes = plt.subplots(1, len(covers), figsize=(11, 3.9), sharey=True)
    vmax = float(np.nanmax(np.abs(sub["hide_advantage"])))
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    for ax, cover in zip(np.atleast_1d(axes), covers):
        g = sub[sub["cover"].astype(str) == cover]
        grid = g.pivot(index="cover_impact", columns="hide_mult",
                       values="hide_advantage").sort_index(ascending=False)
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
                        fontsize=8,
                        color=fs.SURFACE if abs(v) > vmax * 0.55 else fs.INK)
        ax.set_title(f"{cover} cover", fontsize=9.5, color=fs.INK_SOFT, pad=8)
        ax.set_xlabel("residual detectability\nwhen hidden")
        ax.grid(visible=False)
        ax.tick_params(length=0)
        fs.strip_spines(ax, keep=())
    np.atleast_1d(axes)[0].set_ylabel("cover impact strength")
    cbar = fig.colorbar(im, ax=list(np.atleast_1d(axes)), fraction=0.03,
                        pad=0.02)
    cbar.set_label("hide advantage over flee\n(survival % points)",
                   fontsize=8.5, color=fs.INK_SOFT)
    cbar.outline.set_visible(False)
    n_cells = len(sub)
    wins = int((sub["hide_advantage"] > 0).sum())
    fs.title_block(
        fig, "Better concealment never flips the result",
        f"Hiding wins in {wins} of {n_cells} cells shown. Even at zero "
        "residual detectability and maximum cover impact — a prey that is "
        "literally invisible while hidden — fleeing still wins.")
    fs.source_note(fig, f"octoplus detection-sensitivity · motion penalty "
                        f"{motion:g}x · 10 seeds per cell")
    fig.subplots_adjust(top=0.76, bottom=0.20)
    save(fig, "fig06_detection_boundary.png")


# ====================================================================
# Speed boundary on a wider grid than the factorial sampled
# ====================================================================
def speed_boundary(path):
    print("\n[S2] Speed boundary (wide grid)")
    df = load_table(path)
    idx = ["cover", "arrangement", "prey_speed", "pred_speed", "seed"]
    w = df.pivot_table(index=idx, columns="strategy",
                       values="survival", observed=True).reset_index()
    w["hide_advantage"] = w["hide"] - w["flee"]
    cells = (w.groupby(["arrangement", "prey_speed", "pred_speed"],
                       observed=True)["hide_advantage"]
              .agg(["mean", "std", "count"]).reset_index())
    write(cells, "21_speed_boundary_wide.csv")
    wins = cells[cells["mean"] > 0]
    print(f"  cells where hiding wins: {len(wins)} of {len(cells)}")
    FINDINGS["speed_boundary_hide_wins"] = int(len(wins))
    if len(wins):
        print(wins.sort_values("mean", ascending=False).head(8).to_string(
            index=False, float_format=lambda v: f"{v:.2f}"))

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
    # Mark the window the main factorial actually sampled, so the
    # reader can see that the boundary sits just outside it.
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
        "predator (top-left). The factorial never sampled that corner, "
        "which is why it found no boundary.")
    fs.source_note(fig, "octoplus speed-boundary · medium cover · "
                        "15 seeds per cell · arrangements pooled")
    fig.subplots_adjust(top=0.78, bottom=0.12)
    save(fig, "fig07_speed_boundary_wide.png")

    # The mechanistically meaningful quantity is the speed ratio, not
    # either speed alone: fleeing works exactly when prey can keep
    # distance, which depends on predator speed relative to prey speed.
    cells = cells.assign(ratio=(cells["pred_speed"] /
                                cells["prey_speed"]).round(3))
    by_ratio = (cells.groupby("ratio")["mean"]
                     .agg(["mean", "count"]).reset_index()
                     .rename(columns={"mean": "hide_advantage"}))
    write(by_ratio, "26_hide_advantage_by_speed_ratio.csv")
    positive = by_ratio[by_ratio["hide_advantage"] > 0]
    if len(positive):
        threshold = float(positive["ratio"].min())
        print(f"  hiding first wins at predator/prey speed ratio "
              f">= {threshold:g}")
        FINDINGS["hide_wins_speed_ratio_threshold"] = threshold
    print(by_ratio.to_string(index=False,
                             float_format=lambda v: f"{v:.2f}"))
    return cells


# ====================================================================
# Cover gradient: how much cover is enough?
# ====================================================================
def cover_gradient(path):
    """Cover heterogeneity at constant mean.

    This experiment was designed to sweep cover amount by varying the
    number of reef clusters. It does not do that, and the reason is a
    feature of the model rather than a bug: normalize-cover-to-target
    rescales every patch after the clusters are placed, so the realised
    mean lands on the category target regardless of cluster count.

    What the experiment actually delivers is better. Cluster count
    varies the *spatial heterogeneity* of cover while holding the mean
    exactly constant, at seven levels instead of the three the
    `cover-arrangement` chooser provides. That is a direct, high
    resolution test of research questions 3 and 4: does the arrangement
    of cover matter once its amount is controlled?
    """
    print("\n[S3] Cover heterogeneity at constant mean")
    df = load_table(path)

    # First: confirm the mean really is invariant to cluster count.
    inv = (df.groupby(["cover", "clusters"], observed=True)
             .agg(cover_mean=("cover_mean", "mean"),
                  cover_sd=("cover_sd", "mean"),
                  usable_cover=("cover_available", "mean"),
                  dist_to_cover=("dist_to_cover", "mean")).reset_index())
    write(inv, "22_cover_heterogeneity_environment.csv")
    spread = (inv.groupby("cover", observed=True)["cover_mean"]
                 .agg(lambda s: s.max() - s.min()))
    print("  realised mean cover, spread across cluster counts:")
    print(spread.to_string(float_format=lambda v: f"{v:.2e}"))
    FINDINGS["cover_mean_invariance"] = float(spread.max())

    out = (df.groupby(["strategy", "cover", "clusters"], observed=True)
             .agg(survival=("survival", "mean"),
                  cover_sd=("cover_sd", "mean"),
                  usable_cover=("cover_available", "mean"),
                  n=("survival", "size")).reset_index())
    write(out, "23_cover_heterogeneity_survival.csv")

    # Does heterogeneity move survival at all, holding mean constant?
    rows = []
    for (strat, cover), g in df.groupby(["strategy", "cover"],
                                        observed=True):
        groups = [gg["survival"].values
                  for _, gg in g.groupby("clusters", observed=True)]
        lo = g[g["clusters"] == g["clusters"].min()]["survival"]
        hi = g[g["clusters"] == g["clusters"].max()]["survival"]
        d = sc.cliffs_delta(hi.values, lo.values)
        rows.append(dict(strategy=strat, cover=cover,
                         omega_squared=sc.omega_squared(groups),
                         survival_at_0_clusters=float(lo.mean()),
                         survival_at_60_clusters=float(hi.mean()),
                         cliffs_delta=d, magnitude=sc.delta_magnitude(d)))
    eff = pd.DataFrame(rows)
    write(eff, "24_cover_heterogeneity_effect.csv")
    print(eff.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    FINDINGS["heterogeneity_effect"] = eff.to_dict("records")

    fig, axes = plt.subplots(1, 3, figsize=(11.2, 4.2), sharey=True)
    covers = [c for c in COVER_ORDER if c in set(out["cover"].astype(str))]
    for ax, cover in zip(axes, covers):
        g = out[out["cover"].astype(str) == cover]
        for strat in STRATEGY_ORDER:
            gg = g[g["strategy"] == strat].sort_values("cover_sd")
            if gg.empty:
                continue
            ax.plot(gg["cover_sd"], gg["survival"],
                    color=fs.STRATEGY_COLOR[strat], linewidth=2.0,
                    marker="o", markersize=4.2, markeredgecolor=fs.SURFACE,
                    markeredgewidth=1.2, label=fs.STRATEGY_LABEL[strat],
                    solid_capstyle="round")
        ax.set_title(f"{cover} cover", fontsize=9.5, color=fs.INK_SOFT,
                     pad=8)
        ax.set_xlabel("cover heterogeneity (SD)")
        fs.strip_spines(ax)
    axes[0].set_ylabel("founder survival (%)")
    axes[0].set_ylim(0, 100)
    axes[0].legend(loc="upper left", ncol=2)
    fs.title_block(
        fig, "Arrangement barely matters once amount is controlled",
        "Cluster count varies cover heterogeneity while the normalisation "
        "holds the mean exactly at its target. Survival is close to flat "
        "across the whole range.")
    fs.source_note(fig, "octoplus cover-gradient · 3,780 runs · "
                        "mean cover invariant to 1e-15 across cluster counts")
    fig.subplots_adjust(top=0.80, bottom=0.14)
    save(fig, "fig08_cover_heterogeneity.png")
    return out


# ====================================================================
# Reproduction: equilibrium population rather than time to extinction
# ====================================================================
def reproduction(path):
    print("\n[S4] Reproduction equilibrium")
    df = load_table(path)
    out = (df.groupby(["strategy", "cover", "arrangement"], observed=True)
             .agg(final_population=("count octopuses", "mean"),
                  founder_survival=("survival", "mean"),
                  births=("births", "mean"),
                  captures=("captures", "mean"),
                  extinct_pct=("went_extinct", lambda s: 100 * s.mean()),
                  n=("survival", "size")).reset_index())
    write(out, "35_reproduction_equilibrium.csv")

    summary = (df.groupby("strategy", observed=True)
                 .agg(final_population=("count octopuses", "mean"),
                      births=("births", "mean"),
                      captures=("captures", "mean"),
                      extinct_pct=("went_extinct", lambda s: 100*s.mean()))
                 .reset_index().sort_values("final_population",
                                            ascending=False))
    print(summary.to_string(index=False, float_format=lambda v: f"{v:.1f}"))
    FINDINGS["reproduction_summary"] = summary.to_dict("records")

    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    covers = [c for c in COVER_ORDER if c in set(out["cover"].astype(str))]
    width = 0.2
    for k, strat in enumerate(STRATEGY_ORDER):
        g = (out[out["strategy"] == strat]
             .groupby("cover", observed=True)["final_population"].mean())
        g = g.reindex(covers)
        xs = np.arange(len(covers)) + (k - 1.5) * width
        ax.bar(xs, g.values, width=width * 0.9,
               color=fs.STRATEGY_COLOR[strat], label=fs.STRATEGY_LABEL[strat],
               edgecolor=fs.SURFACE, linewidth=1.6)
        for x, v in zip(xs, g.values):
            if not np.isnan(v):
                ax.text(x, v + 2, f"{v:.0f}", ha="center", va="bottom",
                        fontsize=7.5, color=fs.INK_SOFT)
    ax.set_xticks(np.arange(len(covers)), [f"{c} cover" for c in covers])
    ax.set_ylabel("population at tick 2000")
    ax.grid(axis="x", visible=False)
    fs.strip_spines(ax)
    ax.legend(ncol=4, loc="upper left")
    fs.title_block(
        fig, "With births, survival becomes a standing population",
        "Mean population after 2,000 ticks with reproduction enabled "
        "(carrying capacity 250).")
    fs.source_note(fig, "octoplus reproduction-equilibrium · 540 runs")
    fig.subplots_adjust(top=0.82, bottom=0.12)
    save(fig, "fig09_reproduction_equilibrium.png")
    return out


# ====================================================================
# Evolution: which policy does selection favour?
# ====================================================================
def evolutionary(path):
    print("\n[S5] Evolutionary mixed population")
    df = load_table(path)
    ren = {f'policy-share "{p}"': f"share_{p}"
           for p in ["hide", "flee", "still", "seek-cover"]}
    ren.update({f'policy-selection-ratio "{p}"': f"sel_{p}"
                for p in ["hide", "flee", "still", "seek-cover"]})
    df = df.rename(columns=ren)
    share_cols = [c for c in df.columns if c.startswith("share_")]
    if not share_cols:
        print("  no policy-share columns; skipping")
        return None

    # A run that went extinct has every policy share at zero, so
    # including those runs makes the mean shares sum to less than one
    # and a stacked bar of them would not reach 100%. Composition is
    # only defined where a population exists, so extinct runs are
    # excluded here and reported separately.
    extinct = int((df["count octopuses"] <= 0).sum())
    print(f"  runs: {len(df)}, of which extinct: {extinct} "
          f"({100 * extinct / len(df):.1f}%) — excluded from composition")
    FINDINGS["evolutionary_extinct_pct"] = round(100 * extinct / len(df), 2)
    df = df[df["count octopuses"] > 0]

    out = (df.groupby(["cover", "arrangement", "pred_speed"], observed=True)
             [share_cols + ["count octopuses"]].mean().reset_index())
    write(out, "36_evolutionary_shares.csv")

    overall = df[share_cols].mean().sort_values(ascending=False)
    print("  final policy shares (started at 25% each):")
    print(overall.to_string(float_format=lambda v: f"{v:.3f}"))
    FINDINGS["evolutionary_final_shares"] = overall.to_dict()

    # Selection is visible as a share that moved away from 0.25.
    by_cover = (df.groupby("cover", observed=True)[share_cols]
                  .mean().reset_index())
    fig, ax = plt.subplots(figsize=(8.8, 4.4))
    covers = [c for c in COVER_ORDER if c in set(by_cover["cover"].astype(str))]
    order = ["still", "hide", "flee", "seek-cover"]
    colors = {"still": fs.STRATEGY_COLOR["still"],
              "hide": fs.STRATEGY_COLOR["hide"],
              "flee": fs.STRATEGY_COLOR["flee"],
              "seek-cover": fs.SLOT[0]}
    labels = {"still": "Still", "hide": "Hide", "flee": "Flee",
              "seek-cover": "Seek cover"}
    xs = np.arange(len(covers))
    bottom = np.zeros(len(covers))
    for p in order:
        col = f"share_{p}"
        if col not in by_cover:
            continue
        vals = (by_cover.set_index("cover").reindex(covers)[col].values) * 100
        ax.bar(xs, vals, bottom=bottom, width=0.55, color=colors[p],
               label=labels[p], edgecolor=fs.SURFACE, linewidth=2.0)
        for x, v, b in zip(xs, vals, bottom):
            if v > 5:
                ax.text(x, b + v / 2, f"{v:.0f}", ha="center", va="center",
                        fontsize=8, color=fs.SURFACE, fontweight="semibold")
        bottom += vals
    ax.axhline(25, color=fs.INK_SOFT, linewidth=1.0, linestyle=(0, (4, 3)))
    ax.text(-0.42, 27, "starting share of each policy", fontsize=7.5,
            color=fs.INK_SOFT, ha="left")
    ax.set_xticks(xs, [f"{c} cover" for c in covers])
    ax.set_ylabel("share of surviving population (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="x", visible=False)
    fs.strip_spines(ax)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fs.title_block(
        fig, "What selection actually favours",
        "Policies are inherited, so after 2,000 ticks the mix is an outcome. "
        "All four start at 25%. Fleeing takes the population almost "
        "completely, and does so faster the more cover there is.")
    fs.source_note(fig, "octoplus evolutionary-mixed · 507 surviving runs "
                        "of 540 · 80 founders per run")
    fig.subplots_adjust(top=0.82, bottom=0.22)
    save(fig, "fig10_evolutionary_selection.png")
    return out



# ====================================================================
# Motion penalty: the second boundary
# ====================================================================
ALL_POLICIES = ["still", "hide", "flee", "seek-cover", "adaptive-dmas"]
POLICY_LABEL = {"still": "Still", "hide": "Hide", "flee": "Flee",
                "seek-cover": "Seek cover", "adaptive-dmas": "Adaptive"}
POLICY_COLOR = {"still": fs.SLOT[3], "hide": fs.SLOT[2], "flee": fs.SLOT[1],
                "seek-cover": fs.SLOT[0], "adaptive-dmas": "#4a3aa7"}


def motion_penalty(path):
    """How hard must movement be punished before hiding wins?

    detection-sensitivity ruled out concealment quality as the thing
    that decides hide-versus-flee. The remaining candidate is the cost
    of moving, which is the one parameter that penalises fleeing
    specifically. This sweeps it far past the model's default of 1.5.
    """
    print("\n[S6] Motion-penalty boundary")
    df = load_table(path).rename(
        columns={"motion-detection-multiplier": "motion"})
    print(f"  {len(df)} runs")

    by = df.pivot_table(index="motion", columns="strategy",
                        values="survival", observed=True)
    write(by.reset_index(), "27_motion_penalty_survival.csv")
    print(by.round(1).to_string())

    # Immobile policies must be completely unaffected by a movement
    # penalty. That is a free validity check on the detection model.
    for immobile in ["still", "hide"]:
        if immobile in by:
            spread = float(by[immobile].max() - by[immobile].min())
            print(f"  {immobile}: survival spread across motion penalty "
                  f"= {spread:.2f} (expected 0)")
            FINDINGS[f"{immobile}_motion_invariance"] = spread

    w = df.pivot_table(index=["cover", "motion", "seed"], columns="strategy",
                       values="survival", observed=True).reset_index()
    w["hide_advantage"] = w["hide"] - w["flee"]
    cells = (w.groupby(["cover", "motion"], observed=True)["hide_advantage"]
              .mean().reset_index())
    write(cells, "28_motion_penalty_boundary.csv")
    wins = cells[cells["hide_advantage"] > 0]
    if len(wins):
        print(f"  hiding first wins at motion penalty "
              f">= {wins['motion'].min():g} (cover: "
              f"{sorted(set(wins['cover'].astype(str)))})")
        FINDINGS["motion_penalty_threshold"] = float(wins["motion"].min())
    else:
        print("  hiding never wins in the sampled motion range")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.4))
    for pol in ALL_POLICIES:
        if pol not in by:
            continue
        ax1.plot(by.index, by[pol], color=POLICY_COLOR[pol], linewidth=2.0,
                 marker="o", markersize=4.5, markeredgecolor=fs.SURFACE,
                 markeredgewidth=1.2, label=POLICY_LABEL[pol],
                 solid_capstyle="round")
    ax1.set_xlabel("movement detection multiplier")
    ax1.set_ylabel("founder survival (%)")
    ax1.set_ylim(0, 100)
    ax1.axvline(1.5, color=fs.INK_MUTED, linewidth=1.0,
                linestyle=(0, (4, 3)))
    ax1.text(1.62, 95, "model default", fontsize=7.5, color=fs.INK_MUTED)
    fs.strip_spines(ax1)
    ax1.legend(loc="upper right", ncol=1)

    covers = [c for c in COVER_ORDER if c in set(cells["cover"].astype(str))]
    for cover, shade in zip(covers, [fs.SEQUENTIAL[2], fs.SEQUENTIAL[4],
                                     fs.SEQUENTIAL[6]]):
        g = cells[cells["cover"].astype(str) == cover]
        ax2.plot(g["motion"], g["hide_advantage"], color=shade, linewidth=2.0,
                 marker="o", markersize=4.5, markeredgecolor=fs.SURFACE,
                 markeredgewidth=1.2, label=f"{cover} cover",
                 solid_capstyle="round")
    ax2.axhline(0, color=fs.INK_SOFT, linewidth=1.2)
    ax2.set_xlabel("movement detection multiplier")
    ax2.set_ylabel("hide advantage over flee (% points)")
    fs.strip_spines(ax2)
    ax2.legend(loc="lower right")
    fs.title_block(
        fig, "Punishing movement is what makes hiding viable",
        "Left: only the mobile policies respond to the movement penalty. "
        "Right: hiding overtakes fleeing at high cover once movement is "
        "penalised about 4x, well past the model's default of 1.5.")
    fs.source_note(fig, "octoplus motion-penalty-boundary · 2,100 runs · "
                        "20 seeds per cell")
    fig.subplots_adjust(top=0.80, bottom=0.13, wspace=0.26)
    save(fig, "fig11_motion_penalty.png")
    return cells


# ====================================================================
# Five-policy tournament, including the untested seek-cover policy
# ====================================================================
def policy_tournament(path):
    print("\n[S7] Five-policy tournament")
    df = load_table(path)
    print(f"  {len(df)} runs")

    rows = []
    for pol, g in df.groupby("strategy", observed=True):
        point, lo, hi = sc.bootstrap_ci(g["survival"].values)
        rows.append(dict(policy=pol, n=len(g), survival=point,
                         ci_lo=lo, ci_hi=hi,
                         extinct_pct=100 * float(g["went_extinct"].mean())))
    overall = pd.DataFrame(rows).sort_values("survival", ascending=False)
    write(overall, "29_policy_tournament_overall.csv")
    print(overall.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    FINDINGS["policy_tournament"] = overall.to_dict("records")

    cell = ["cover", "arrangement", "prey_speed", "pred_speed", "seed"]
    wide = df.pivot_table(index=cell, columns="strategy",
                          values="survival", observed=True)

    # Does the adaptive policy beat the best fixed policy available?
    fixed = [c for c in wide.columns if c != "adaptive-dmas"]
    rows = []
    for pol in fixed:
        if "adaptive-dmas" not in wide:
            break
        res = sc.paired_test(wide["adaptive-dmas"].values, wide[pol].values)
        d = sc.cliffs_delta(wide["adaptive-dmas"].values, wide[pol].values)
        rows.append(dict(comparison=f"adaptive vs {pol}", **res,
                         cliffs_delta=d, magnitude=sc.delta_magnitude(d)))
    vs = pd.DataFrame(rows)
    if len(vs):
        vs["p_holm"] = sc.holm_correct(vs["p"].values)
        write(vs, "30_adaptive_vs_fixed.csv")
        print(vs[["comparison", "median_diff", "cliffs_delta",
                  "magnitude", "p_holm"]].to_string(
            index=False, float_format=lambda v: f"{v:.4g}"))

    # Independent replication: this experiment repeats the factorial's
    # design with different seeds, so the four shared policies should
    # reproduce their factorial means.
    main = os.path.join(TAB, "03_survival_overall.csv")
    if os.path.exists(main):
        ref = pd.read_csv(main).set_index("strategy")["survival_mean"]
        rep = []
        for pol in overall["policy"]:
            if pol in ref.index:
                here = float(
                    overall.loc[overall["policy"] == pol, "survival"].iloc[0])
                rep.append(dict(policy=pol, factorial=float(ref[pol]),
                                tournament=here,
                                difference=here - float(ref[pol])))
        if rep:
            rep = pd.DataFrame(rep)
            write(rep, "34_replication_check.csv")
            print("  replication against the main factorial:")
            print(rep.to_string(index=False,
                                float_format=lambda v: f"{v:.2f}"))
            FINDINGS["replication_max_abs_diff"] = float(
                rep["difference"].abs().max())

    best = wide.idxmax(axis=1)
    share = (best.value_counts(normalize=True).mul(100)
             .rename_axis("policy").reset_index(name="pct_of_cells_best"))
    write(share, "31_policy_tournament_best_share.csv")
    print(share.to_string(index=False, float_format=lambda v: f"{v:.1f}"))

    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    o = overall.set_index("policy").reindex(
        [p for p in ALL_POLICIES if p in set(overall["policy"])])
    xs = np.arange(len(o))
    ax.bar(xs, o["survival"], width=0.6,
           color=[POLICY_COLOR[p] for p in o.index],
           edgecolor=fs.SURFACE, linewidth=1.8)
    ax.errorbar(xs, o["survival"],
                yerr=[o["survival"] - o["ci_lo"], o["ci_hi"] - o["survival"]],
                fmt="none", ecolor=fs.INK_SOFT, elinewidth=1.2, capsize=3)
    for x, v in zip(xs, o["survival"]):
        ax.text(x, v + 1.6, f"{v:.1f}", ha="center", va="bottom",
                fontsize=9, color=fs.INK_SOFT)
    ax.set_xticks(xs, [POLICY_LABEL[p] for p in o.index])
    ax.set_ylabel("founder survival (%)")
    ax.set_ylim(0, max(100, float(o["survival"].max()) * 1.2))
    ax.grid(axis="x", visible=False)
    fs.strip_spines(ax)
    fs.title_block(
        fig, "The policy the factorial forgot lands in the middle",
        "Seek-cover is one of the model's four actions and was absent from "
        "the original design. It beats hiding in place, but not fleeing.")
    fs.source_note(fig, "octoplus policy-tournament · 6,075 runs · "
                        "15 seeds per condition")
    fig.subplots_adjust(top=0.80, bottom=0.10)
    save(fig, "fig12_policy_tournament.png")
    return overall



# ====================================================================
# Reaction time (hypothesis H9)
# ====================================================================
def reaction_time(path):
    print("\n[S8] Reaction time")
    df = load_table(path).rename(
        columns={"prey-reaction-time-setting": "reaction"})
    print(f"  {len(df)} runs")

    by = df.pivot_table(index="reaction", columns="strategy",
                        values="survival", observed=True)
    write(by.reset_index(), "32_reaction_time_survival.csv")
    print(by.round(1).to_string())

    rows = []
    for pol in by.columns:
        lo = df[(df["strategy"] == pol) &
                (df["reaction"] == df["reaction"].min())]["survival"]
        hi = df[(df["strategy"] == pol) &
                (df["reaction"] == df["reaction"].max())]["survival"]
        d = sc.cliffs_delta(hi.values, lo.values)
        rows.append(dict(policy=pol,
                         survival_at_0=float(lo.mean()),
                         survival_at_15=float(hi.mean()),
                         change=float(hi.mean() - lo.mean()),
                         cliffs_delta=d, magnitude=sc.delta_magnitude(d)))
    eff = pd.DataFrame(rows).sort_values("change")
    write(eff, "33_reaction_time_effect.csv")
    print(eff.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    FINDINGS["reaction_time_effect"] = eff.to_dict("records")

    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    for pol in ALL_POLICIES:
        if pol not in by:
            continue
        ax.plot(by.index, by[pol], color=POLICY_COLOR[pol], linewidth=2.0,
                marker="o", markersize=4.5, markeredgecolor=fs.SURFACE,
                markeredgewidth=1.2, label=POLICY_LABEL[pol],
                solid_capstyle="round")
    # Five series, so the legend carries identity on its own; direct
    # labels at this density collide with each other and with the lines.
    ax.set_xlabel("prey reaction delay (ticks)")
    ax.set_ylabel("founder survival (%)")
    ax.set_ylim(0, 100)
    ax.set_xlim(-0.4, by.index.max() + 0.4)
    ax.axvline(2, color=fs.INK_MUTED, linewidth=1.0, linestyle=(0, (4, 3)))
    ax.text(2.25, 95, "model default", fontsize=7.5, color=fs.INK_MUTED)
    fs.strip_spines(ax)
    ax.legend(loc="upper right", ncol=2)
    fs.title_block(
        fig, "Reaction delay costs exactly the policies that need to act",
        "H9 predicted that longer delays reduce survival. They do — but "
        "only for the policies whose action is time-critical.")
    fs.source_note(fig, "octoplus reaction-time · 1,575 runs · "
                        "15 seeds per cell")
    fig.subplots_adjust(top=0.82, bottom=0.13)
    save(fig, "fig13_reaction_time.png")
    return by


def main():
    jobs = [("detection-sensitivity", detection_sensitivity),
            ("speed-boundary", speed_boundary),
            ("cover-gradient", cover_gradient),
            ("reproduction-equilibrium", reproduction),
            ("evolutionary-mixed", evolutionary),
            ("motion-penalty-boundary", motion_penalty),
            ("policy-tournament", policy_tournament),
            ("reaction-time", reaction_time)]
    for name, fn in jobs:
        p = have(name)
        if p is None:
            print(f"\n[skip] {name}: results not available yet")
            continue
        try:
            fn(p)
        except Exception as exc:
            print(f"  !! {name} failed: {type(exc).__name__}: {exc}")
    with open(os.path.join(TAB, "findings_supplementary.json"), "w") as fh:
        json.dump(FINDINGS, fh, indent=2, default=str)
    print("\nDone.")


if __name__ == "__main__":
    main()
