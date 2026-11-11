#!/usr/bin/env python3
"""
calib_score.py — does the rubric actually predict OB's real short-form performance?

Scores every fetched Short with the DETERMINISTIC rubric (regex features + archetype
library, NO LLM — the exact path that runs standalone), then correlates each feature
and the total score against the era-adjusted outlier ratio (and log views) with
Spearman rank correlation. Also tests whether Shorts whose opener matches a
bot-researched hook archetype outperform those that don't, and does a train/holdout
weight refit. Honest: reports holdout, flags significance, states caveats.

Writes calib/calibration_report.{md,json}.
"""
import json, os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from score import REGEX, W, detect_archetype, first_sentence   # noqa
from clean_srt import parse_srt, dedup_words                    # noqa

ROOT = os.path.join(HERE, "..", "calib")
SUBS = os.path.join(ROOT, "subs")
FEATS = list(W.keys())


def transcript(srt_path):
    words = dedup_words(parse_srt(srt_path))
    return " ".join(w for w, _ in words)


def score(text):
    sub = {k: fn(text) for k, fn in REGEX.items()}
    arch = detect_archetype(first_sentence(text))
    strength = arch["strength"] if arch else 0
    sub["hook"] = max(sub["hook"], strength)              # deterministic hook
    weighted = sum(sub[k] * W[k] for k in W) / 100.0
    total = weighted * (0.4 + 0.6 * sub["hook"] / 100.0)  # hook multiplier
    return sub, total, (1 if arch else 0)


# ---- stats (no scipy dependency) -------------------------------------------
def rankdata(a):
    a = np.asarray(a, float)
    sorter = np.argsort(a, kind="mergesort")
    inv = np.empty(len(a), int); inv[sorter] = np.arange(len(a))
    s = a[sorter]
    obs = np.r_[True, s[1:] != s[:-1]]
    dense = obs.cumsum()[inv]
    counts = np.r_[np.nonzero(obs)[0], len(a)]
    return 0.5 * (counts[dense] + counts[dense - 1] + 1)


def spearman(x, y):
    rx, ry = rankdata(x), rankdata(y)
    if rx.std() == 0 or ry.std() == 0:
        return 0.0, 1.0
    r = float(np.corrcoef(rx, ry)[0, 1])
    n = len(x)
    if abs(r) >= 1.0 or n < 4:
        return r, 0.0
    t = r * math.sqrt((n - 2) / (1 - r * r))
    p = math.erfc(abs(t) / math.sqrt(2))          # normal approx, fine for large n
    return r, p


def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


def main():
    manifest = {r["id"]: r for r in json.load(open(os.path.join(ROOT, "shorts_manifest.json")))}
    X, rows, arch_flags = [], [], []
    for vid, r in manifest.items():
        p = os.path.join(SUBS, f"{vid}.en.srt")
        if not os.path.exists(p):
            continue
        txt = transcript(p)
        if len(txt.split()) < 12:                 # skip empty/near-empty transcripts
            continue
        sub, total, has_arch = score(txt)
        rows.append({"id": vid, "outlier": r["outlier"], "views": r["views"],
                     "total": total, **{f"f_{k}": sub[k] for k in FEATS}})
        X.append([sub[k] for k in FEATS] + [total])
        arch_flags.append(has_arch)

    n = len(rows)
    if n < 30:
        print(f"[calib] only {n} scored — waiting on more transcripts.", file=sys.stderr)
        return
    X = np.array(X, float)
    outlier = np.array([r["outlier"] for r in rows], float)
    logv = np.log10(np.array([r["views"] for r in rows], float))
    arch_flags = np.array(arch_flags)

    predictors = FEATS + ["TOTAL"]
    corr = []
    for i, name in enumerate(predictors):
        ro, po = spearman(X[:, i], outlier)
        rv, pv = spearman(X[:, i], logv)
        corr.append((name, ro, po, rv, pv))
    corr_sorted = sorted(corr, key=lambda c: -abs(c[1]))

    # archetype effect: do opener-matched Shorts outperform?
    with_a = outlier[arch_flags == 1]
    without_a = outlier[arch_flags == 0]
    arch_line = (f"{len(with_a)} shorts matched a hook archetype (median outlier "
                 f"{np.median(with_a):.2f}) vs {len(without_a)} that didn't "
                 f"(median {np.median(without_a):.2f})") if len(with_a) and len(without_a) else "n/a"

    # train/holdout refit on log(outlier), standardized features
    np.random.seed(0)
    idx = np.random.permutation(n); cut = int(n * 0.7)
    tr, ho = idx[:cut], idx[cut:]
    F = X[:, :len(FEATS)]
    mu, sd = F[tr].mean(0), F[tr].std(0) + 1e-9
    Fz = (F - mu) / sd
    y = np.log(np.clip(outlier, 1e-3, None))
    A = np.c_[Fz[tr], np.ones(len(tr))]
    coef, *_ = np.linalg.lstsq(A, y[tr], rcond=None)
    w_fit = coef[:len(FEATS)]
    pred_ho = np.c_[Fz[ho], np.ones(len(ho))] @ coef
    rho_refit, _ = spearman(pred_ho, outlier[ho])
    rho_rubric, _ = spearman(X[ho, len(FEATS)], outlier[ho])   # rubric TOTAL on same holdout
    fit_order = sorted(zip(FEATS, w_fit), key=lambda t: -t[1])

    # ---- report ----
    L = [f"# Calibration report — does the rubric predict OB's real Shorts performance?",
         f"_n = {n} published Shorts with transcript + views · deterministic features only (no LLM) · "
         f"outcome = era-adjusted outlier ratio (views ÷ median of Shorts posted within ±45 days)_\n",
         "## Per-feature Spearman correlation vs performance (sorted by strength)",
         "| feature | ρ vs outlier | ρ vs log(views) |",
         "|---|---|---|"]
    for name, ro, po, rv, pv in corr_sorted:
        L.append(f"| {'**TOTAL**' if name=='TOTAL' else name} | {ro:+.3f}{stars(po)} | {rv:+.3f}{stars(pv)} |")
    L += ["", "_\\* p<0.05, ** p<0.01, \\*\\*\\* p<0.001 (normal approx). "
          f"For n={n}, |ρ|>~{1.96/math.sqrt(n):.2f} is significant at p<0.05._", ""]
    L += [f"## Do the bot-researched hook archetypes correlate with views?", f"{arch_line}\n"]
    L += ["## Refit (train/holdout, log-outlier regression on standardized features)",
          f"- Holdout Spearman — **current hand-set rubric**: ρ = {rho_rubric:+.3f}",
          f"- Holdout Spearman — **data-refit weights**: ρ = {rho_refit:+.3f}",
          "- Data-driven feature ranking (fitted coefficient, standardized):"]
    for name, w in fit_order:
        L.append(f"   - {name}: {w:+.3f}")
    json.dump({"n": n, "corr": corr, "rho_rubric_holdout": rho_rubric,
               "rho_refit_holdout": rho_refit, "arch_with_median": float(np.median(with_a)) if len(with_a) else None,
               "arch_without_median": float(np.median(without_a)) if len(without_a) else None,
               "fit_weights": dict(zip(FEATS, w_fit.tolist()))},
              open(os.path.join(ROOT, "calibration_report.json"), "w"), indent=2)
    open(os.path.join(ROOT, "calibration_report.md"), "w").write("\n".join(L))
    print("\n".join(L))
    print(f"\n[calib] n={n}; wrote calib/calibration_report.md", file=sys.stderr)


if __name__ == "__main__":
    main()
