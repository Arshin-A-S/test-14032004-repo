# benchmarks/performance_benchmark.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add your existing imports after this
import time
import json
import statistics
from datetime import datetime
from components.crypto_component import CryptoComponent
from components.fl_component import FLComponent
from components.s3_component import S3Component

class PerformanceBenchmark:
    def __init__(self):
        self.crypto = CryptoComponent()
        # NEW line
        from components.fl_component import FLComponent # Make sure this import is at the top
        self.fl_comp = FLComponent()
        self.s3c = S3Component("file-storage-00414", region_name="eu-central-1")
        
        # Ensure crypto is set up
        try:
            self.crypto.load_master_keys()
        except FileNotFoundError:
            print("🔑 Setting up crypto keys...")
            self.crypto.setup(force=True)
            self.crypto.save_master_keys()
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": {}
        }
    
    def benchmark_encryption(self, file_sizes_mb=[1, 5, 10], trials=3):
        """Benchmark AES + Waters11 hybrid encryption performance"""
        print("🔐 Benchmarking Encryption Performance...")
        
        results = {}
        
        for size_mb in file_sizes_mb:
            print(f"  📊 Testing {size_mb}MB files...")
            size_results = []
            
            for trial in range(trials):
                # Create test file
                test_file = f"temp_test_{size_mb}mb_{trial}.bin"
                file_size_bytes = size_mb * 1024 * 1024
                
                with open(test_file, "wb") as f:
                    f.write(os.urandom(file_size_bytes))
                
                # Time encryption
                start = time.time()
                meta = self.crypto.encrypt_file_hybrid(test_file, "role:prof")
                enc_time = time.time() - start
                
                # Time decryption
                user_sk = self.crypto.generate_user_secret(["role:prof"])
                start = time.time()
                dec_path = self.crypto.decrypt_file_hybrid(meta, user_sk)
                dec_time = time.time() - start
                
                # Calculate throughput
                enc_throughput = size_mb / enc_time if enc_time > 0 else 0
                dec_throughput = size_mb / dec_time if dec_time > 0 else 0
                
                size_results.append({
                    "encryption_time_sec": enc_time,
                    "decryption_time_sec": dec_time,
                    "encryption_throughput_MB_sec": enc_throughput,
                    "decryption_throughput_MB_sec": dec_throughput
                })
                
                # Cleanup
                os.remove(test_file)
                os.remove(meta["enc_file_path"])
                os.remove(dec_path)
            
            # Aggregate results for this file size
            results[f"{size_mb}MB"] = {
                "avg_encryption_time_sec": statistics.mean([r["encryption_time_sec"] for r in size_results]),
                "avg_decryption_time_sec": statistics.mean([r["decryption_time_sec"] for r in size_results]),
                "avg_encryption_throughput_MB_sec": statistics.mean([r["encryption_throughput_MB_sec"] for r in size_results]),
                "avg_decryption_throughput_MB_sec": statistics.mean([r["decryption_throughput_MB_sec"] for r in size_results]),
                "min_encryption_throughput": min([r["encryption_throughput_MB_sec"] for r in size_results]),
                "max_encryption_throughput": max([r["encryption_throughput_MB_sec"] for r in size_results]),
                "trials": trials
            }
            
            print(f"    ✅ {size_mb}MB: {results[f'{size_mb}MB']['avg_encryption_throughput_MB_sec']:.2f} MB/sec avg encryption")
        
        return results
    
    def benchmark_fl_scoring(self, num_requests=1000):
        """Benchmark FL anomaly scoring performance"""
        print("🤖 Benchmarking FL Scoring Performance...")
        
        contexts = [
            {"location": "chennai", "device_id": "laptop1"},
            {"location": "mumbai", "device_id": "legion"},
            {"location": "chennai", "device_id": "phone1"},
            {"location": "unknown", "device_id": "suspicious"},
            {"location": "foreign", "device_id": "hacker"}
        ]
        
        times = []
        scores = []
        
        for i in range(num_requests):
            context = contexts[i % len(contexts)]
            
            start = time.time()
            score = self.fl_comp.score_access(context)
            end = time.time()
            
            times.append(end - start)
            scores.append(score)
        
        return {
            "total_requests": num_requests,
            "avg_time_ms": statistics.mean(times) * 1000,
            "min_time_ms": min(times) * 1000,
            "max_time_ms": max(times) * 1000,
            "requests_per_sec": num_requests / sum(times),
            "avg_score": statistics.mean(scores),
            "score_range": [min(scores), max(scores)]
        }
    
    def benchmark_s3_operations(self, file_sizes_mb=[1, 5], trials=2):
        """Benchmark S3 upload/download performance (optional)"""
        print("☁️ Benchmarking S3 Operations...")
        
        results = {"upload": {}, "download": {}}
        
        for size_mb in file_sizes_mb:
            print(f"  📊 Testing S3 with {size_mb}MB files...")
            upload_times = []
            download_times = []
            
            for trial in range(trials):
                # Create test file
                test_file = f"s3_test_{size_mb}mb_{trial}.bin"
                with open(test_file, "wb") as f:
                    f.write(os.urandom(size_mb * 1024 * 1024))
                
                s3_key = f"app/benchmark/test_{size_mb}mb_{trial}_{int(time.time())}.bin"
                
                try:
                    # Time upload
                    start = time.time()
                    upload_success = self.s3c.upload_file(test_file, s3_key)
                    upload_time = time.time() - start
                    
                    if upload_success:
                        upload_times.append(upload_time)
                        
                        # Time download
                        download_file = f"downloaded_{size_mb}mb_{trial}.bin"
                        start = time.time()
                        download_success = self.s3c.download_file(s3_key, download_file)
                        download_time = time.time() - start
                        
                        if download_success:
                            download_times.append(download_time)
                            os.remove(download_file)
                        
                        # Cleanup S3
                        self.s3c.delete_file(s3_key)
                    
                except Exception as e:
                    print(f"    ⚠️ S3 operation failed: {e}")
                
                # Cleanup local file
                os.remove(test_file)
            
            if upload_times:
                results["upload"][f"{size_mb}MB"] = {
                    "avg_time_sec": statistics.mean(upload_times),
                    "avg_throughput_MB_sec": size_mb / statistics.mean(upload_times),
                    "successful_trials": len(upload_times)
                }
                print(f"    ✅ {size_mb}MB Upload: {results['upload'][f'{size_mb}MB']['avg_throughput_MB_sec']:.2f} MB/sec")
            
            if download_times:
                results["download"][f"{size_mb}MB"] = {
                    "avg_time_sec": statistics.mean(download_times),
                    "avg_throughput_MB_sec": size_mb / statistics.mean(download_times),
                    "successful_trials": len(download_times)
                }
                print(f"    ✅ {size_mb}MB Download: {results['download'][f'{size_mb}MB']['avg_throughput_MB_sec']:.2f} MB/sec")
        
        return results
    
    def benchmark_false_positive_rate(self):
        """Calculate false positive rate with synthetic test data"""
        print("📊 Benchmarking False Positive Rate...")
        
        # Create test dataset with known labels
        test_data = []
        
        # Normal cases (should not trigger anomaly)
        normal_contexts = [
            {"location": "chennai", "device_id": "laptop1"},
            {"location": "mumbai", "device_id": "legion"},
            {"location": "chennai", "device_id": "phone1"},
        ]
        
        # Add many normal cases
        for _ in range(200):
            context = normal_contexts[_ % len(normal_contexts)]
            test_data.append((context, 0))  # label=0 means normal
        
        # Anomalous cases (should trigger anomaly)
        anomaly_contexts = [
            {"location": "unknown_city", "device_id": "suspicious"},
            {"location": "foreign", "device_id": "hacker"},
            {"location": "new_location", "device_id": "unknown_device"},
        ]
        
        # Add anomaly cases
        for _ in range(50):
            context = anomaly_contexts[_ % len(anomaly_contexts)]
            test_data.append((context, 1))  # label=1 means anomaly
        
        # Score all test cases
        predictions = []
        true_labels = []
        # NEW CORRECT LINE
        threshold = self.fl_comp.model["decision"]["threshold"]
        
        for context, true_label in test_data:
            score = self.fl_comp.score_access(context)
            predicted_anomaly = 1 if score >= threshold else 0
            
            predictions.append(predicted_anomaly)
            true_labels.append(true_label)
        
        # Calculate metrics
        true_positives = sum((true_labels[i] == 1) and (predictions[i] == 1) for i in range(len(true_labels)))
        false_positives = sum((true_labels[i] == 0) and (predictions[i] == 1) for i in range(len(true_labels)))
        true_negatives = sum((true_labels[i] == 0) and (predictions[i] == 0) for i in range(len(true_labels)))
        false_negatives = sum((true_labels[i] == 1) and (predictions[i] == 0) for i in range(len(true_labels)))
        
        # Calculate rates
        fpr = false_positives / max(1, false_positives + true_negatives)
        tpr = true_positives / max(1, true_positives + false_negatives)
        accuracy = (true_positives + true_negatives) / len(true_labels)
        
        print(f"    📊 False Positive Rate: {fpr:.1%}")
        print(f"    📊 True Positive Rate: {tpr:.1%}")
        print(f"    📊 Accuracy: {accuracy:.1%}")
        
        return {
            "false_positive_rate": fpr,
            "true_positive_rate": tpr,
            "accuracy": accuracy,
            "threshold_used": threshold,
            "total_samples": len(true_labels),
            "confusion_matrix": {
                "true_positives": true_positives,
                "false_positives": false_positives,
                "true_negatives": true_negatives,
                "false_negatives": false_negatives
            }
        }
    
    def run_full_benchmark(self):
        """Run complete performance benchmark suite"""
        print("🚀 Starting Comprehensive Performance Benchmark...\n")
        
        # Run all benchmarks
        self.results["benchmarks"]["encryption"] = self.benchmark_encryption()
        print()
        
        self.results["benchmarks"]["fl_scoring"] = self.benchmark_fl_scoring()
        print()
        
        self.results["benchmarks"]["s3_operations"] = self.benchmark_s3_operations()
        print()
        
        self.results["benchmarks"]["false_positive_rate"] = self.benchmark_false_positive_rate()
        print()
        
        # Save results
        os.makedirs("app/benchmarks/results", exist_ok=True)
        results_file = f"app/benchmarks/results/performance_results_{int(time.time())}.json"
        
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Print summary
        self.print_summary()
        
        print(f"\n📁 Detailed results saved to: {results_file}")
        return self.results
    
    def print_summary(self):
        """Print performance summary"""
        print("=" * 60)
        print("🎯 PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 60)
        
        # Encryption summary
        enc_5mb = self.results["benchmarks"]["encryption"].get("5MB", {})
        if enc_5mb:
            print(f"🔐 Encryption (5MB): {enc_5mb.get('avg_encryption_throughput_MB_sec', 0):.2f} MB/sec")
            print(f"🔓 Decryption (5MB): {enc_5mb.get('avg_decryption_throughput_MB_sec', 0):.2f} MB/sec")
        
        # FL scoring summary
        fl_results = self.results["benchmarks"]["fl_scoring"]
        print(f"🤖 FL Scoring: {fl_results.get('requests_per_sec', 0):.0f} requests/sec")
        print(f"⏱️  FL Avg Time: {fl_results.get('avg_time_ms', 0):.2f} ms")
        
        # S3 summary
        s3_results = self.results["benchmarks"]["s3_operations"]
        s3_5mb_up = s3_results.get("upload", {}).get("5MB", {})
        s3_5mb_down = s3_results.get("download", {}).get("5MB", {})
        
        if s3_5mb_up:
            print(f"☁️ S3 Upload (5MB): {s3_5mb_up.get('avg_throughput_MB_sec', 0):.2f} MB/sec")
        if s3_5mb_down:
            print(f"📥 S3 Download (5MB): {s3_5mb_down.get('avg_throughput_MB_sec', 0):.2f} MB/sec")
        
        # FPR summary
        fpr_results = self.results["benchmarks"]["false_positive_rate"]
        print(f"📊 False Positive Rate: {fpr_results.get('false_positive_rate', 0):.1%}")
        print(f"🎯 Accuracy: {fpr_results.get('accuracy', 0):.1%}")
        
        print("=" * 60)

if __name__ == "__main__":
    print("🧪 Performance Benchmark Tool")
    print("=" * 40)
    
    benchmark = PerformanceBenchmark()
    results = benchmark.run_full_benchmark()
    
    print("\n✅ Benchmark completed successfully!")
    print("\n💡 Use these results in your IEEE paper for:")
    print("   • Encryption/Decryption throughput metrics")
    print("   • FL anomaly detection performance")
    print("   • False positive rate validation") 
    print("   • System scalability analysis")
