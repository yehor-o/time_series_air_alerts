"""Exploration: which spatial unit should we forecast at? (decision D16)

Every option is scored on the same question: "will a new alert start in district (raion) r
during the next h hours?", for h = 1 and 3. Truth = official data at raion level.

Options
  O1 oblast   - model trained on oblast "any alert" history; each raion gets its oblast's probability
  O3 raion    - model trained on raion history; before the raion era an oblast-wide alert is
                copied to every raion of the oblast ("disaggregation")
  O4 hier.    - O1 probability x P(raion alert | oblast alert), the share estimated on the last 28
                training days
  baseline    - "same hour of day over the last 14 days" rate of the raion (no model)

Periods (all before the yellow/red reform, so the real test period from 2026-09-07 stays untouched)
  train       2025-06-01 .. 2026-08-09
  evaluation  2026-08-10 .. 2026-09-06

Leakage rules (CLAUDE.md): every feature at issue time t uses only alerts that started before t;
an alert active at t is "active", its end time is not used; ends are used only once they happened.

Usage: python scripts/explore_spatial_options.py <official_data_uk.csv> [--out reports/spatial_options.md]
"""
import argparse
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

START, TRAIN_END, EVAL_END = (pd.Timestamp(x, tz="UTC") for x in ("2025-06-01", "2026-08-10", "2026-09-07"))
WARMUP = pd.Timedelta("14D")  # history needed before the first feature row
HOURS = pd.date_range(START - WARMUP, EVAL_END + pd.Timedelta("3h"), freq="h")
SEED = 42


def load_units(path):
    """Official alerts -> {unit: (starts, ends)} for raions and for oblasts, after disaggregation."""
    o = pd.read_csv(path, parse_dates=["started_at", "finished_at"])
    o = o[(o.level != "hromada") & (o.oblast != "Луганська область")]  # hromada rows: mostly artillery
    o = o[(o.finished_at > HOURS[0]) & (o.started_at < HOURS[-1])]
    raions = o[o.level == "raion"].groupby("oblast").raion.unique().to_dict()
    rows = []
    for r in o.itertuples():
        if r.level == "raion":
            rows.append((r.oblast, r.raion, r.started_at, r.finished_at))
        else:  # oblast-wide alert -> every raion of that oblast (Kyiv City is its own single unit)
            for rn in raions.get(r.oblast, [r.oblast]):
                rows.append((r.oblast, rn, r.started_at, r.finished_at))
    d = pd.DataFrame(rows, columns=["oblast", "raion", "start", "end"])
    raion_units = {k: merge(g) for k, g in d.groupby(["oblast", "raion"])}
    oblast_units = {k: merge(g) for k, g in d.groupby("oblast")}
    return raion_units, oblast_units


def merge(g):
    """Union of possibly overlapping intervals -> sorted (starts, ends) arrays of separate alerts."""
    g = g.sort_values("start")
    starts, ends = [], []
    for s, e in zip(g.start, g.end):
        if starts and s <= ends[-1]:
            ends[-1] = max(ends[-1], e)
        else:
            starts.append(s)
            ends.append(e)
    return np.array(starts, dtype="datetime64[ns]"), np.array(ends, dtype="datetime64[ns]")


def unit_arrays(starts, ends):
    """Hourly arrays for one unit, indexed like HOURS (issue time t = HOURS[k])."""
    t = HOURS.values.astype("datetime64[ns]")
    edges = np.append(t, t[-1] + np.timedelta64(1, "h"))
    n_start = np.histogram(starts.astype("int64"), bins=edges.astype("int64"))[0]  # starts in [t_k, t_k+1h)
    i = np.searchsorted(starts, t, side="left")  # number of alerts that started strictly before t
    last_start = np.where(i > 0, starts[np.maximum(i - 1, 0)], np.datetime64("NaT", "ns"))
    active = (i > 0) & (ends[np.maximum(i - 1, 0)] > t)  # the most recent alert hasn't ended yet
    j = np.searchsorted(np.sort(ends), t, side="right")  # ends that already happened (<= t)
    last_end = np.where(j > 0, np.sort(ends)[np.maximum(j - 1, 0)], np.datetime64("NaT", "ns"))
    hrs = lambda x: np.minimum((t - x) / np.timedelta64(1, "h"), 24 * 14)
    return {
        "n_start": n_start,
        "active": active.astype(float),
        "h_since_start": np.nan_to_num(hrs(last_start), nan=24 * 14),
        "h_since_end": np.where(active, 0.0, np.nan_to_num(hrs(last_end), nan=24 * 14)),
    }


def past_sum(x, w):
    """Sum of x over the w bins strictly before k (no look-ahead)."""
    c = np.concatenate([[0], np.cumsum(x)])
    k = np.arange(len(x))
    return c[k] - c[np.maximum(k - w, 0)]


def future_any(x, h):
    """Target: any start in bins k .. k+h-1, i.e. during (t, t+h]."""
    c = np.concatenate([[0], np.cumsum(x > 0)])
    k = np.arange(len(x))
    return (c[np.minimum(k + h, len(x))] - c[k]) > 0


def hod_rate(x, days=14):
    """Share of the last `days` days with a start in the same hour of day (strictly past)."""
    s = np.zeros(len(x))
    for d in range(1, days + 1):
        s += np.concatenate([np.zeros(24 * d), (x[: len(x) - 24 * d] > 0)])
    return s / days


def frame(units, oblast_arrays, nat_starts):
    """Feature table for a set of units (raions or oblasts)."""
    local = HOURS.tz_convert("Europe/Kyiv")
    keep = (HOURS >= START) & (HOURS < EVAL_END)
    parts = []
    for key, (s, e) in units.items():
        a = unit_arrays(s, e)
        ob = key[0] if isinstance(key, tuple) else key
        oa = oblast_arrays[ob]
        f = pd.DataFrame({
            "time": HOURS, "unit": "|".join(key) if isinstance(key, tuple) else key, "oblast": ob,
            "active": a["active"], "h_since_start": a["h_since_start"], "h_since_end": a["h_since_end"],
            "starts_1h": past_sum(a["n_start"], 1), "starts_3h": past_sum(a["n_start"], 3),
            "starts_24h": past_sum(a["n_start"], 24), "hod_rate14": hod_rate(a["n_start"]),
            "ob_active_share": oa["active_share"], "ob_starts_3h": past_sum(oa["n_start"], 3),
            "nat_starts_1h": past_sum(nat_starts, 1), "nat_starts_3h": past_sum(nat_starts, 3),
            "hour": local.hour, "dow": local.dayofweek,
            "y1": future_any(a["n_start"], 1), "y3": future_any(a["n_start"], 3),
        })
        parts.append(f[keep])
    return pd.concat(parts, ignore_index=True)


FEATURES = ["active", "h_since_start", "h_since_end", "starts_1h", "starts_3h", "starts_24h", "hod_rate14",
            "ob_active_share", "ob_starts_3h", "nat_starts_1h", "nat_starts_3h", "hour", "dow"]


def fit_predict(df, target):
    tr, ev = df[df.time < TRAIN_END], df[df.time >= TRAIN_END]
    m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31, min_child_samples=200,
                           subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=SEED, verbose=-1)
    m.fit(tr[FEATURES], tr[target])
    return m.predict_proba(ev[FEATURES])[:, 1]


def md(df):
    """DataFrame -> markdown table (without the optional `tabulate` dependency)."""
    head = "| | " + " | ".join(df.columns) + " |"
    rows = ["| " + str(i) + " | " + " | ".join(f"{v:.4f}" for v in r) + " |" for i, r in zip(df.index, df.values)]
    return "\n".join([head, "|" + "---|" * (len(df.columns) + 1)] + rows)


def scores(y, p, base):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    b = brier_score_loss(y, p)
    return {"Brier": b, "Brier skill vs baseline": 1 - b / brier_score_loss(y, np.clip(base, 1e-4, 1 - 1e-4)),
            "log-loss": log_loss(y, p), "ROC-AUC": roc_auc_score(y, p), "base rate": y.mean()}


def main(path, out):
    raion_units, oblast_units = load_units(path)
    oblast_arrays = {}
    for ob, (s, e) in oblast_units.items():
        a = unit_arrays(s, e)
        ks = [k for k in raion_units if k[0] == ob]
        a["active_share"] = np.mean([unit_arrays(*raion_units[k])["active"] for k in ks], axis=0)
        oblast_arrays[ob] = a
    nat = np.sum([a["n_start"] for a in oblast_arrays.values()], axis=0)

    R = frame(raion_units, oblast_arrays, nat)   # one row per raion-hour
    O = frame(oblast_units, oblast_arrays, nat)  # one row per oblast-hour
    ev = R[R.time >= TRAIN_END].reset_index(drop=True)
    lines = ["# Spatial options: exploration results", "",
             f"Raions: {R.unit.nunique()}, oblasts: {O.unit.nunique()}. Train {START.date()}..{(TRAIN_END - pd.Timedelta('1D')).date()}, "
             f"evaluation {TRAIN_END.date()}..{(EVAL_END - pd.Timedelta('1D')).date()} (official data, pre-reform).",
             "All options are scored against **raion-level truth** (new alert starts in the raion).", ""]
    for h in (1, 3):
        y = f"y{h}"
        p_raion = fit_predict(R, y)
        p_ob = pd.Series(fit_predict(O, y), index=O[O.time >= TRAIN_END].set_index(["time", "unit"]).index)
        p_o1 = p_ob.reindex(pd.MultiIndex.from_arrays([ev.time, ev.oblast])).values
        # O4: P(raion starts | oblast starts) per raion, from the last 28 training days
        last = R[(R.time >= TRAIN_END - pd.Timedelta("28D")) & (R.time < TRAIN_END)]
        ob_y = O.set_index(["time", "unit"])[y]
        last = last.assign(ob_y=ob_y.reindex(pd.MultiIndex.from_arrays([last.time, last.oblast])).values)
        cond = last[last.ob_y == 1].groupby("unit")[y].mean()
        p_o4 = p_o1 * ev.unit.map(cond).fillna(cond.mean()).values
        base = ev.hod_rate14.values
        res = {"baseline (raion, same hour last 14 days)": scores(ev[y], base, base),
               "O1 oblast model -> raion": scores(ev[y], p_o1, base),
               "O3 raion model (disaggregated)": scores(ev[y], p_raion, base),
               "O4 hierarchical oblast x share": scores(ev[y], p_o4, base)}
        lines += [f"## Horizon {h}h", "", md(pd.DataFrame(res).T), ""]
        # the same models judged on oblast-level truth (is the raion model also good for the oblast?)
        evo = O[O.time >= TRAIN_END]
        p_agg = 1 - pd.Series(1 - p_raion).groupby([ev.time, ev.oblast]).prod()
        p_agg = p_agg.reindex(pd.MultiIndex.from_arrays([evo.time, evo.unit])).values
        reso = {"baseline (oblast)": scores(evo[y], evo.hod_rate14, evo.hod_rate14),
                "O1 oblast model": scores(evo[y], p_ob.values, evo.hod_rate14),
                "O3 raion model aggregated 1-prod(1-p)": scores(evo[y], p_agg, evo.hod_rate14)}
        lines += [f"### Horizon {h}h, judged on oblast-level truth", "", md(pd.DataFrame(reso).T), ""]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("official_csv")
    ap.add_argument("--out", default="reports/spatial_options.md")
    a = ap.parse_args()
    main(a.official_csv, a.out)
