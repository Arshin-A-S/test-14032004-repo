from __future__ import annotations

import os, json, math, random, datetime
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

BUCKETS = ["bucket_0_6", "bucket_6_12", "bucket_12_18", "bucket_18_24"]

def now_iso_z() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def time_to_bucket(hour: int) -> str:
    if 0 <= hour < 6:   return "bucket_0_6"
    if 6 <= hour < 12:  return "bucket_6_12"
    if 12 <= hour < 18: return "bucket_12_18"
    return "bucket_18_24"

def read_events(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["label"] = df["label"].astype(int)
    df["hour"] = df["hour"].astype(int)
    if "time_bucket" not in df.columns:
        df["time_bucket"] = df["hour"].apply(time_to_bucket)
    return df

@dataclass
class Laplace:
    success_prior: float = 1.0
    fail_prior: float = 1.0

def _counts_for(df: pd.DataFrame, key: str) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    g = df.groupby([key, "label"]).size().unstack(fill_value=0)
    for cat, row in g.iterrows():
        s = int(row.get(1, 0))
        f = int(row.get(0, 0))
        out[str(cat)] = {"success": s, "fail": f}
    return out

def apply_laplace(counts: Dict[str, Dict[str, int]], lp: Laplace) -> Dict[str, float]:
    rates: Dict[str, float] = {}
    for cat, sf in counts.items():
        s = sf.get("success", 0)
        f = sf.get("fail", 0)
        rates[cat] = (s + lp.success_prior) / (s + f + lp.success_prior + lp.fail_prior)
    return rates

def aggregate_fedavg(client_counts: List[Dict[str, Dict[str, int]]]) -> Dict[str, Dict[str, int]]:
    total: Dict[str, Dict[str, int]] = {}
    for cc in client_counts:
        for cat, sf in cc.items():
            if cat not in total:
                total[cat] = {"success": 0, "fail": 0}
            total[cat]["success"] += int(sf.get("success", 0))
            total[cat]["fail"] += int(sf.get("fail", 0))
    return total

def trimmed_mean(values: List[float], trim_ratio: float = 0.1) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    k = int(math.floor(len(v) * trim_ratio))
    v = v[k: len(v) - k] if len(v) - 2*k > 0 else v
    return float(np.mean(v)) if v else 0.0

def groupby_client_counts(df: pd.DataFrame, key: str) -> List[Dict[str, Dict[str, int]]]:
    return [_counts_for(g, key=key) for _, g in df.groupby("client_id")]

def build_stats_section(df: pd.DataFrame) -> Dict:
    g = df.groupby("label").size().to_dict()
    global_stats = {"success": int(g.get(1, 0)), "fail": int(g.get(0, 0))}
    location_stats = _counts_for(df, "location")
    device_stats   = _counts_for(df, "device")
    time_stats     = _counts_for(df, "time_bucket")
    if "department" in df.columns:
        dept_stats = _counts_for(df, "department")
    else:
        dept_stats = {"cs": {"success": global_stats["success"], "fail": global_stats["fail"]}}
    return {
        "seeded": True,
        "global": global_stats,
        "location_stats": location_stats,
        "device_stats": device_stats,
        "department_stats": dept_stats,
        "time_stats": time_stats
    }

# CHANGED: This function now also calculates and returns department success rates
def success_rates_from_stats(stats: Dict, lp: Laplace) -> Tuple[Dict[str,float], Dict[str,float], Dict[str,float], Dict[str,float], float]:
    loc_rates = apply_laplace(stats["location_stats"], lp)
    dev_rates = apply_laplace(stats["device_stats"], lp)
    time_rates = apply_laplace(stats["time_stats"], lp)
    dept_rates = apply_laplace(stats["department_stats"], lp) # ADDED
    gs = stats["global"]
    global_rate = (gs["success"] + lp.success_prior) / (gs["success"] + gs["fail"] + lp.success_prior + lp.fail_prior)
    return loc_rates, dev_rates, time_rates, dept_rates, global_rate # CHANGED

# CHANGED: This is the main fix for the TypeError. The function now accepts 'department'.
def score_event(model: Dict, location: str, device: str, time_bucket: str, department: str) -> float:
    weights = model["decision"]["weights"]
    learned = model["learned"]
    global_rate = learned.get("global_success_rate", 0.5)

    loc_p = learned["location_success_rate"].get(location, global_rate)
    dev_p = learned["device_success_rate"].get(device, global_rate)
    tim_p = learned["time_success_rate"].get(time_bucket, global_rate)
    dept_p = learned["department_success_rate"].get(department, global_rate) # ADDED

    loc_risk = 1.0 - float(loc_p)
    dev_risk = 1.0 - float(dev_p)
    time_risk = 1.0 - float(tim_p)
    dept_risk = 1.0 - float(dept_p) # ADDED

    risk = (weights["location"] * loc_risk +
            weights["device"]   * dev_risk +
            weights["time"]     * time_risk +
            weights["department"] * dept_risk) # ADDED
    
    return max(0.0, min(1.0, float(risk)))

def choose_threshold(y_true: np.ndarray, scores: np.ndarray, target_fpr: float = 0.1) -> float:
    thresholds = np.unique(scores)
    if thresholds.size == 0:
        return 0.65
    best_t = thresholds[0]
    best_diff = 1e9
    for t in thresholds:
        y_pred = (scores >= t).astype(int)
        fp = np.sum((y_true == 0) & (y_pred == 1))
        tn = np.sum((y_true == 0) & (y_pred == 0))
        fpr = fp / max(1, (fp + tn))
        diff = abs(fpr - target_fpr)
        if diff < best_diff:
            best_diff = diff
            best_t = t
    return float(best_t)

def write_json(obj: Dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)

# CHANGED: This function now handles the department feature when building the final model file.
def save_model_v2(path: str, stats: Dict, lp: Laplace, weights: Dict[str,float],
                  threshold: float, aggregation_cfg: Dict, validation_meta: Dict) -> Dict:
    loc_rates, dev_rates, time_rates, dept_rates, global_rate = success_rates_from_stats(stats, lp) # CHANGED
    model = {
        "version": 2, "schema": "context-anomaly-model", "last_updated": now_iso_z(),
        "decision": {
            "method": "logit_weighted", "threshold": float(threshold),
            "weights": {
                "location": float(weights["location"]),
                "device":   float(weights["device"]),
                "time":     float(weights["time"]),
                "department": float(weights["department"]) # ADDED
            },
            "eps": 1e-6
        },
        "smoothing": {
            "type": "laplace", "success_prior": float(lp.success_prior), "fail_prior": float(lp.fail_prior)
        },
        "feature_spec": {
            "location": { "type": "categorical" },
            "device":   { "type": "categorical" },
            "time_bucket": { "type": "categorical", "buckets": BUCKETS },
            "department": { "type": "categorical" } # ADDED
        },
        "stats": stats, "aggregation": aggregation_cfg, "validation": validation_meta,
        "learned": {
            "global_success_rate": float(global_rate),
            "location_success_rate": {k: float(v) for k, v in loc_rates.items()},
            "device_success_rate":   {k: float(v) for k, v in dev_rates.items()},
            "time_success_rate":     {k: float(v) for k, v in time_rates.items()},
            "department_success_rate": {k: float(v) for k, v in dept_rates.items()} # ADDED
        }
    }
    write_json(model, path)
    return model