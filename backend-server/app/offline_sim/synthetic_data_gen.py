from __future__ import annotations
import os, argparse, random, time, uuid
import numpy as np
import pandas as pd
from tqdm import tqdm

# This function would typically be in a shared file like 'common.py'
# For simplicity, it's included here.
def time_to_bucket(hour: int) -> str:
    if 5 <= hour <= 11:
        return "morning"
    if 12 <= hour <= 16:
        return "afternoon"
    if 17 <= hour <= 21:
        return "evening"
    return "night"

# --- Main Data Generation Logic ---

LOCATIONS = ["chennai", "mumbai", "bangalore", "delhi"]
DEVICES = ["legion", "laptop1", "phone1", "desktop", "tablet"]
DEPARTMENTS = ["cs", "math", "eng"]

def make_clients(n_clients: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    return [str(uuid.uuid4()) for _ in range(n_clients)]

def gen_events(n_events: int, clients: list[str], seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    
    # Base probabilities for normal events
    p_loc = np.array([0.4, 0.25, 0.2, 0.15])
    p_dev = np.array([0.3, 0.25, 0.2, 0.15, 0.1])
    p_dept = np.array([0.6, 0.25, 0.15])
    
    rows = []
    anomaly_count = 0
    # Set a target for how many events should be anomalies
    target_anomalies = int(n_events * 0.15) # Target 15% of events to be anomalies
    
    # Use tqdm for a nice progress bar
    for _ in tqdm(range(n_events), desc="Generating Realistic Events"):
        cid = rng.choice(clients)
        
        # Probabilistically decide if this event should be an anomaly
        is_anomaly = anomaly_count < target_anomalies and rng.random() < 0.15
        
        if is_anomaly:
            # --- Generate a clear ANOMALOUS event pattern ---
            hour = int(rng.choice([2, 3, 4, 23, 1])) # Unusual hours
            loc = rng.choice(["unknown_country", "suspicious_location", "blacklisted_region"])
            dev = rng.choice(["unknown_device", "suspicious_browser", "tor_exit_node"])
            dept = rng.choice(["unknown", "external"])
            
            # Simulate a classic attack pattern: multiple failed attempts
            consecutive_failures = rng.integers(3, 8)
            for _ in range(consecutive_failures):
                rows.append({
                    "event_id": str(uuid.uuid4()),
                    "client_id": cid,
                    "ts": int(time.time()) + rng.integers(-86400, 86400),
                    "hour": hour,
                    "time_bucket": time_to_bucket(hour),
                    "location": loc,
                    "device": dev,
                    "department": dept,
                    "label": 0, # Failure
                    "is_anomaly": 1,
                    "anomaly_type": "suspicious_access"
                })
            anomaly_count += 1
        else:
            # --- Generate a NORMAL event pattern ---
            hour = int(rng.choice(range(9, 18))) # Normal business hours
            loc = LOCATIONS[rng.choice(len(LOCATIONS), p=p_loc)]
            dev = DEVICES[rng.choice(len(DEVICES), p=p_dev)]
            dept = DEPARTMENTS[rng.choice(len(DEPARTMENTS), p=p_dept)]
            
            # Normal events have a high, but not perfect, success probability
            p_success = 0.92 if (loc in ["chennai", "mumbai"] and 9 <= hour <= 17) else 0.85
            label = 1 if rng.random() < p_success else 0 # 1 for success, 0 for failure
            
            rows.append({
                "event_id": str(uuid.uuid4()),
                "client_id": cid,
                "ts": int(time.time()),
                "hour": hour,
                "time_bucket": time_to_bucket(hour),
                "location": loc,
                "device": dev,
                "department": dept,
                "label": label,
                "is_anomaly": 0,
                "anomaly_type": "normal"
            })
    
    return pd.DataFrame(rows)

def main():
    # Setup command-line argument parsing
    ap = argparse.ArgumentParser()
    # Assume DATA_DIR is a folder where you store data, e.g., 'data/'
    DATA_DIR = "data" 
    ap.add_argument("--out", default=os.path.join(DATA_DIR, "synthetic_events.csv"))
    ap.add_argument("--events", type=int, default=10000)
    ap.add_argument("--clients", type=int, default=25)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    # Generate clients and then the event data
    clients = make_clients(args.clients, args.seed)
    df = gen_events(args.events, clients, args.seed)
    
    # Create the output directory if it doesn't exist and save the file
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"\nSuccessfully wrote {len(df)} events to {args.out}")

if __name__ == "__main__":
    main()