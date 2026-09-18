"""Loading and tidying of BehaviorSpace table output."""
import pandas as pd
import numpy as np

STRATEGY_ORDER = ["still", "hide", "flee", "adaptive-dmas"]
COVER_ORDER = ["low", "medium", "high"]
ARRANGEMENT_ORDER = ["uniform", "patchy", "mixed"]

# The cell that identifies one matched set of runs: every strategy is
# run against this exact combination, so strategies can be compared
# pairwise within it.
CELL = ["cover", "arrangement", "prey_speed", "pred_speed", "seed"]

RENAME = {
    "octopus-strategy-mode": "strategy",
    "cover-amount-category": "cover",
    "cover-arrangement": "arrangement",
    "prey-speed-setting": "prey_speed",
    "predator-speed-setting": "pred_speed",
    "experiment-seed": "seed",
    "founder-survival-rate": "survival",
    "survival-rate": "population_index",
    "capture-rate": "captures_pct",
    "mean-founder-survival-time": "mean_survival_ticks",
    "extinction-time": "extinction_tick",
    "run-censored?": "censored",
    "median-capture-tick": "median_capture_tick",
    "predator-capture-efficiency": "predator_efficiency",
    "realized-cover-mean": "cover_mean",
    "cover-availability": "cover_available",
    "cover-variation": "cover_sd",
    "mean-distance-to-usable-cover": "dist_to_cover",
    "average-cover-usage": "cover_used",
    "relative-cover-use": "cover_use_ratio",
    "hide-exposure-proportion": "exp_hide",
    "flee-exposure-proportion": "exp_flee",
    "still-exposure-proportion": "exp_still",
    "seek-cover-exposure-proportion": "exp_seek",
    "strategy-evenness": "evenness",
    "detection-events": "detections",
    "pursuit-events": "pursuits",
    "total-captures": "captures",
    "total-births": "births",
    "final-tick": "final_tick",
    "reef-cluster-count": "clusters",
    "predator-prey-speed-ratio": "speed_ratio",
}


def resolve(path):
    """Accepts either `name.csv` or `name.csv.gz`, whichever exists."""
    import os
    if os.path.exists(path):
        return path
    if not path.endswith(".gz") and os.path.exists(path + ".gz"):
        return path + ".gz"
    if path.endswith(".gz") and os.path.exists(path[:-3]):
        return path[:-3]
    return path


def load_table(path):
    """Reads a BehaviorSpace 'table' CSV (six metadata lines, then data).

    Gzipped files are read transparently, which is how the repository
    ships the full evidence base without carrying 18 MB of raw CSV.
    """
    df = pd.read_csv(resolve(path), skiprows=6)
    # pandas already removes CSV quoting; stripping quote characters again
    # would mangle reporter names that legitimately contain them, such as
    # 'policy-share "hide"'.
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns=RENAME)

    for col in ("censored",):
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().eq("true")

    if "extinction_tick" in df.columns:
        # -1 is the model's "never went extinct" sentinel. For survival
        # analysis a censored observation is the final tick, flagged as
        # not-an-event, so the sentinel must not leak into the times.
        df["went_extinct"] = df["extinction_tick"] >= 0
        df["event_time"] = np.where(
            df["went_extinct"], df["extinction_tick"], df["final_tick"])

    for col, order in (("strategy", STRATEGY_ORDER),
                       ("cover", COVER_ORDER),
                       ("arrangement", ARRANGEMENT_ORDER)):
        if col in df.columns:
            present = [v for v in order if v in set(df[col])]
            extra = [v for v in df[col].unique() if v not in present]
            df[col] = pd.Categorical(df[col], categories=present + extra,
                                     ordered=True)
    return df


def check_pairing(df):
    """Verifies that a seed really does reproduce the same environment.

    The paired analysis depends on it, so it is asserted rather than
    assumed: within one (cover, arrangement, seed) the realised cover
    mean must be identical across strategies and speeds.
    """
    key = ["cover", "arrangement", "seed"]
    spread = (df.groupby(key, observed=True)["cover_mean"]
                .agg(lambda s: s.max() - s.min()))
    return float(spread.max()), int((spread > 1e-9).sum())
