# offline_sim/poisoning_eval.py
from __future__ import annotations
import os, argparse, json, math
from typing import Dict, List
import numpy as np
import pandas as pd
from tqdm import tqdm

from common import (
    DATA_DIR, read_events, _counts_for, groupby_client_counts,
    aggregate_fedavg, Laplace, build_stats_section, save_model_v2,
    score_event, choose_threshold
)

DEFAULT_EVENTS = os.path.join(DATA_DIR, "synthetic_events.csv")

def poison_client_counts(df: pd.DataFrame, mode: str = "label_flip") -> Dict[str, Dict[str,int]]:
    """
    Construct poisoned counts for a single client partition.
    - label_flip: swap success/fail tallies
    - location_bias: inflate a rare location to look normal
    """
    counts = _counts_for(df, "location")  # start from location for demo

    if mode == "label_flip":
        for k in counts:
            s, f = counts[k]["success"], counts[k]["fail"]
            counts[k]["success"], counts[k]["fail"] = f, s

    elif mode == "location_bias":
        if counts:
            # pick the least frequent location key (smallest total = success+fail)
            least_key = min(counts.keys(), key=lambda k: counts[k]["success"] + counts[k]["fail"])
            counts[least_key]["success"] += 200  # add fake successes

    return counts


def robust_aggregate(client_counts: List[Dict[str, Dict[str,int]]], trim_ratio: float = 0.1) -> Dict[str, Dict[str,int]]:
    """
    Robustify by taking trimmed mean on success-rate then mapping back to counts scale.
    For simplicity we aggregate on rates and multiply by average total counts.
    """
    cats = sorted({c for cc in client_counts for c in cc.keys()})
    # compute per-client totals to rescale
    totals = [sum(sf["success"] + sf["fail"] for sf in cc.values()) for cc in client_counts]
    avg_total = max(1, int(np.mean(totals)))

    out: Dict[str, Dict[str,int]] = {}
    for cat in cats:
        rates = []
        for cc in client_counts:
            sf = cc.get(cat, {"success":0, "fail":0})
            tot = sf["success"] + sf["fail"]
            p = (sf["success"] + 1.0) / (tot + 2.0)  # Laplace per-client
            rates.append(p)
        rates_sorted = sorted(rates)
        k = int(math.floor(len(rates_sorted)*trim_ratio))
        kept = rates_sorted[k: len(rates_sorted)-k] if len(rates_sorted)-2*k>0 else rates_sorted
        p_hat = float(np.mean(kept)) if kept else 0.5
        s = int(round(p_hat * avg_total))
        f = max(0, avg_total - s)
        out[cat] = {"success": s, "fail": f}
    return out

def evaluate_scores(df: pd.DataFrame, model: Dict) -> Dict[str, float]:
    y_true = (df["label"] == 0).astype(int).values  # anomaly=1 on fail
    scores = []
    for _, r in df.iterrows():
        scores.append(score_event(model, r["location"], r["device"], r["time_bucket"]))
    scores = np.array(scores, dtype=float)
    thr = choose_threshold(y_true, scores, target_fpr=0.1)
    y_pred = (scores >= thr).astype(int)
    precision = float(np.sum((y_pred==1)&(y_true==1)) / max(1, np.sum(y_pred==1)))
    recall    = float(np.sum((y_pred==1)&(y_true==1)) / max(1, np.sum(y_true==1)))
    return {"threshold": float(thr), "precision@thr": precision, "recall@thr": recall}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default=DEFAULT_EVENTS)
    ap.add_argument("--poison_frac", type=float, default=0.2)
    ap.add_argument("--mode", choices=["label_flip","location_bias"], default="label_flip")
    ap.add_argument("--trim_ratio", type=float, default=0.1)
    args = ap.parse_args()

    df = read_events(args.events)
    # split 70/30 for quick eval
    df_train = df.sample(frac=0.7, random_state=123)
    df_test  = df.drop(df_train.index).reset_index(drop=True)

    # Build clean per-client counts
    client_groups = list(df_train.groupby("client_id"))
    n_poison = int(len(client_groups) * args.poison_frac)

    clean_counts_loc = []
    for i, (_, g) in enumerate(client_groups):
        if i < n_poison:
            clean_counts_loc.append(poison_client_counts(g, mode=args.mode))
        else:
            clean_counts_loc.append(_counts_for(g, "location"))

    # Aggregate: naive vs robust
    agg_naive = aggregate_fedavg(clean_counts_loc)
    agg_robust = robust_aggregate(clean_counts_loc, trim_ratio=args.trim_ratio)

    # Compose stats using robust location only (for brevity)
    stats_clean = build_stats_section(df_train)
    stats_naive = dict(stats_clean); stats_naive = json.loads(json.dumps(stats_clean))
    stats_robust = dict(stats_clean); stats_robust = json.loads(json.dumps(stats_clean))
    stats_naive["location_stats"] = agg_naive
    stats_robust["location_stats"] = agg_robust

    lp = Laplace(1,1)
    weights = {"location": 0.5, "device": 0.3, "time": 0.2}  # fixed for this ablation
    agg_cfg = { "algorithm": "FedAvg",
                "robust_aggregation": { "enabled": True, "type": "trimmed_mean", "trim_ratio": float(args.trim_ratio) },
                "clip": { "enabled": True, "max_l2_norm": 1.0 },
                "dp_noise": { "enabled": False, "sigma": 0.0 } }

    model_naive  = save_model_v2(os.path.join(DATA_DIR, "tmp_naive.json"),  stats_naive,  lp, weights, 0.65, agg_cfg, {"holdout_enabled": False})
    model_robust = save_model_v2(os.path.join(DATA_DIR, "tmp_robust.json"), stats_robust, lp, weights, 0.65, agg_cfg, {"holdout_enabled": False})

    m_naive  = evaluate_scores(df_test,  model_naive)
    m_robust = evaluate_scores(df_test, model_robust)

    report = {
        "poison_mode": args.mode,
        "poison_frac": args.poison_frac,
        "naive": m_naive,
        "robust_trimmed_mean": m_robust
    }
    out_path = os.path.join(DATA_DIR, "poisoning_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    print(f"Wrote report to {out_path}")

if __name__ == "__main__":
    main()
