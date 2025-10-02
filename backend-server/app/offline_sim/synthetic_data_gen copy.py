# offline_sim/synthetic_data_gen.py
from __future__ import annotations
import os, argparse, random, time, uuid
import numpy as np
import pandas as pd
from tqdm import tqdm
from common import DATA_DIR, time_to_bucket

LOCATIONS = ["chennai", "mumbai"]
DEVICES   = ["legion", "laptop1", "phone1"]
DEPARTMENTS = ["cs"]  # extend if needed

def make_clients(n_clients: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    return [str(uuid.uuid4()) for _ in range(n_clients)]

def gen_events(n_events: int, clients: list[str], seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    # Global base preferences (tweak as desired)
    p_loc = np.array([0.6, 0.4])  # chennai, mumbai
    p_dev = np.array([0.45, 0.35, 0.20])  # legion, laptop1, phone1
    p_hour = np.array([0.20, 0.35, 0.30, 0.15])  # buckets 0-6, 6-12, 12-18, 18-24

    rows = []
    for _ in tqdm(range(n_events), desc="Generating"):
        cid = rng.choice(clients)
        # sample hour bucket then hour
        b_idx = rng.choice(4, p=p_hour)
        if b_idx == 0: hour = int(rng.integers(0, 6))
        elif b_idx == 1: hour = int(rng.integers(6, 12))
        elif b_idx == 2: hour = int(rng.integers(12, 18))
        else: hour = int(rng.integers(18, 24))
        loc = LOCATIONS[rng.choice(len(LOCATIONS), p=p_loc)]
        dev = DEVICES[rng.choice(len(DEVICES), p=p_dev)]
        dept = "cs"

        # Make success prob higher for frequent combos, lower for rare ones
        base = 0.85
        bonus = 0.0
        if loc == "chennai": bonus += 0.05
        if dev == "legion":  bonus += 0.03
        if 6 <= hour < 12:   bonus += 0.02
        p_success = max(0.05, min(0.98, base + bonus - 0.15*rng.random()))
        label = 1 if rng.random() < p_success else 0

        rows.append({
            "event_id": str(uuid.uuid4()),
            "client_id": cid,
            "ts": int(time.time()),
            "hour": hour,
            "time_bucket": time_to_bucket(hour),
            "location": loc,
            "device": dev,
            "department": dept,
            "label": label
        })
    return pd.DataFrame(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(DATA_DIR, "synthetic_events.csv"))
    ap.add_argument("--events", type=int, default=10000)
    ap.add_argument("--clients", type=int, default=25)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    clients = make_clients(args.clients, args.seed)
    df = gen_events(args.events, clients, args.seed)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} events to {args.out}")

if __name__ == "__main__":
    main()
