"""Write the report's result tables as LaTeX, straight from analysis/v3/tables/*.csv.

Usage: python3 analysis/v3_tables.py   (after analysis/v3_analysis.py)
Writes report/generated/*.tex, so the numbers in the report always match the data.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TAB = ROOT / "analysis" / "v3" / "tables"
OUT = ROOT / "report" / "generated"
OUT.mkdir(parents=True, exist_ok=True)

POLICIES = ["adaptive-dmas", "flee", "hide", "still", "seek-cover", "experimental-assigned"]
SHORT = {"adaptive-dmas": "adaptive", "experimental-assigned": "mixed"}
NAME = {p: SHORT.get(p, p) for p in POLICIES}
ENVS = [("uniform", "low"), ("uniform", "medium"), ("uniform", "high"),
        ("patchy", "low"), ("patchy", "medium"), ("patchy", "high")]


def p_fmt(p):
    if p < 0.001:
        return r"$<$0.001"
    return f"{p:.3f}"


def sweep_table():
    s = pd.read_csv(TAB / "sweep_summary.csv")
    lines = [r"\begin{tabular}{l" + "r" * 6 + "}", r"\toprule",
             r" & \multicolumn{3}{c}{Uniform} & \multicolumn{3}{c}{Patchy} \\",
             r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
             r"Policy & Low & Medium & High & Low & Medium & High \\", r"\midrule"]
    best = {e: s[(s.arrangement == e[0]) & (s.cover == e[1])]["mean"].max() for e in ENVS}
    for p in POLICIES:
        cells = []
        for e in ENVS:
            r = s[(s.policy == p) & (s.arrangement == e[0]) & (s.cover == e[1])].iloc[0]
            txt = f"{r['mean']:.1f} ({r['sd']:.1f})"
            if r["mean"] == best[e]:
                txt = r"\textbf{" + txt + "}"
            ext = int(r.extinct)
            cells.append(txt + (f"$^{{{ext}}}$" if ext else ""))
        lines.append(NAME[p] + " & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "tab_sweep.tex").write_text("\n".join(lines) + "\n")


def pooled_table():
    s = pd.read_csv(TAB / "sweep_pooled.csv").set_index("policy").loc[POLICIES]
    lines = [r"\begin{tabular}{lrrrr}", r"\toprule",
             r"Policy & Late mean pop. [95\% CI] & Extinct runs & Extinct, low cover & CV (surviving) \\",
             r"\midrule"]
    e = pd.read_csv(TAB / "sweep_extinction.csv")
    for p in POLICIES:
        r = s.loc[p]
        low = e[(e.policy == p) & (e.cover == "low")].iloc[0]
        lines.append(f"{NAME[p]} & {r['mean']:.1f} [{r.ci_lo:.1f}, {r.ci_hi:.1f}] & {int(r.extinct)}/{int(r.n)} & "
                     f"{int(low.extinct)}/{int(low.n)} & {r.cv_survivors:.3f}" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "tab_pooled.tex").write_text("\n".join(lines) + "\n")


def alarm_table():
    t = pd.read_csv(TAB / "alarm_paired.csv")
    t = t[t.cover == "all"].set_index("policy").loc[POLICIES]
    lines = [r"\begin{tabular}{lrrrrrrr}", r"\toprule",
             r"Policy & Off & On & On $-$ off [95\% CI] & $r$ & $p_\mathrm{Holm}$ & Births & Captures \\",
             r"\midrule"]
    for p in POLICIES:
        r = t.loc[p]
        if r.late_mean_diff == 0 and r.late_mean_ci_lo == 0 and r.late_mean_ci_hi == 0:
            diff, rr, pp = r"0 (identical runs)", "-", "-"
        else:
            diff = f"{r.late_mean_diff:+.1f} [{r.late_mean_ci_lo:+.1f}, {r.late_mean_ci_hi:+.1f}]"
            rr, pp = f"{r.r:+.2f}", p_fmt(r.p_holm)
        lines.append(f"{NAME[p]} & {r.late_mean_off:.1f} & {r.late_mean_on:.1f} & {diff} & {rr} & {pp} & "
                     f"{r.births_off:.0f}$\\to${r.births_on:.0f} & {r.captures_off:.0f}$\\to${r.captures_on:.0f}" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "tab_alarm.tex").write_text("\n".join(lines) + "\n")


def friedman_table():
    f = pd.read_csv(TAB / "sweep_friedman.csv")
    pw = pd.read_csv(TAB / "sweep_pairwise.csv")
    lines = [r"\begin{tabular}{llrrrrr}", r"\toprule",
             r"Arrangement & Cover & $\chi^2_{\mathrm{F}}(5)$ & $p_\mathrm{Holm}$ & Kendall's $W$ & Flee $-$ hide [95\% CI] & $r$ \\",
             r"\midrule"]
    for a, c in ENVS:
        r = f[(f.arrangement == a) & (f.cover == c)].iloc[0]
        q = pw[(pw.arrangement == a) & (pw.cover == c) & (pw.a == "flee") & (pw.b == "hide")].iloc[0]
        lines.append(f"{a} & {c} & {r.chi2:.1f} & {p_fmt(r.p_holm)} & {r.kendall_w:.2f} & "
                     f"{q.mean_diff:+.1f} [{q.ci_lo:+.1f}, {q.ci_hi:+.1f}] & {q.r:+.2f}" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "tab_friedman.tex").write_text("\n".join(lines) + "\n")


def mixed_table():
    m = pd.read_csv(TAB / "sweep_mixed_final_shares.csv")
    lines = [r"\begin{tabular}{llrrrrr}", r"\toprule",
             r"Arrangement & Cover & Surviving runs & still & hide & flee & seek-cover \\",
             r"\midrule"]
    for a, c in ENVS:
        r = m[(m.arrangement == a) & (m.cover == c)].iloc[0]
        vals = {k: r[k] for k in ["still", "hide", "flee", "seek-cover"]}
        top = max(vals.values())
        cells = [(r"\textbf{%.2f}" % v) if v == top else f"{v:.2f}" for v in vals.values()]
        lines.append(f"{a} & {c} & {int(r.n)}/20 & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "tab_mixed.tex").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sweep_table()
    pooled_table()
    alarm_table()
    friedman_table()
    mixed_table()
    for f in sorted(OUT.glob("*.tex")):
        print(f"== {f.name}\n{f.read_text()}")
