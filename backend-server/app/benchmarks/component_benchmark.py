# benchmarks/component_benchmark.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from components.crypto_component import CryptoComponent
from components.fl_component import FLComponent

def benchmark_crypto():
    """Benchmark encryption performance - NO SERVER NEEDED"""
    crypto = CryptoComponent()
    try:
        crypto.load_master_keys()
    except FileNotFoundError:
        crypto.setup(force=True)
        crypto.save_master_keys()
    
    # Create test file
    test_file = "temp_test_5mb.bin"
    with open(test_file, "wb") as f:
        f.write(os.urandom(5 * 1024 * 1024))  # 5MB
    
    # Measure encryption
    start = time.time()
    meta = crypto.encrypt_file_hybrid(test_file, "role:prof")
    enc_time = time.time() - start
    
    throughput = 5.0 / enc_time
    
    # Cleanup
    os.remove(test_file)
    os.remove(meta["enc_file_path"])
    
    return {
        "encryption_time_sec": enc_time,
        "encryption_throughput_MB_sec": throughput
    }

def benchmark_fl():
    """Benchmark FL scoring performance"""
    fl_comp = FLComponent()
    
    contexts = [
        {"location": "chennai", "device_id": "laptop1"},
        {"location": "mumbai", "device_id": "phone1"},
        {"location": "unknown", "device_id": "suspicious"}
    ]
    
    # Measure FL scoring speed
    num_requests = 1000
    start = time.time()
    for i in range(num_requests):
        score = fl_comp.score_access(contexts[i % len(contexts)])
    total_time = time.time() - start
    
    return {
        "fl_scoring_requests": num_requests,
        "fl_scoring_time_sec": total_time,
        "fl_scoring_rps": num_requests / total_time
    }

if __name__ == "__main__":
    print("🚀 Running Component Benchmarks...")
    
    crypto_results = benchmark_crypto()
    fl_results = benchmark_fl()
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "crypto_benchmark": crypto_results,
        "fl_benchmark": fl_results
    }
    
    # Save results
    with open("app/benchmarks/results/component_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Encryption: {crypto_results['encryption_throughput_MB_sec']:.2f} MB/sec")
    print(f"✅ FL Scoring: {fl_results['fl_scoring_rps']:.0f} requests/sec")
    print("📊 Results saved to benchmarks/results/component_results.json")
