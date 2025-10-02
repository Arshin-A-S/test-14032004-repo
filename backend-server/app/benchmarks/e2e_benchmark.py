# benchmarks/e2e_benchmark.py
import requests
import time
import os
import json
from datetime import datetime

class EndToEndBenchmark:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "e2e_benchmarks": {}
        }
    
    def benchmark_complete_workflow(self, file_sizes_mb=[1, 5, 10], trials=3):
        """Test complete upload → download workflow"""
        print("🔄 Benchmarking Complete Workflow...")
        
        results = {}
        
        for size_mb in file_sizes_mb:
            print(f"  📊 Testing {size_mb}MB end-to-end workflow...")
            workflow_times = []
            
            for trial in range(trials):
                # Create test file
                test_file = f"e2e_test_{size_mb}mb_{trial}.bin"
                with open(test_file, "wb") as f:
                    f.write(os.urandom(size_mb * 1024 * 1024))
                
                # Measure complete workflow
                start_total = time.time()
                
                # 1. Upload
                start_upload = time.time()
                with open(test_file, "rb") as f:
                    upload_response = requests.post(
                        f"{self.base_url}/upload",
                        files={"file": f},
                        data={"owner": "alice", "policy": "role:prof"}
                    )
                upload_time = time.time() - start_upload
                
                if upload_response.status_code == 200:
                    file_id = upload_response.json()["file_id"]
                    
                    # 2. Download
                    start_download = time.time()
                    download_response = requests.post(
                        f"{self.base_url}/download",
                        json={
                            "username": "alice",
                            "file_id": file_id,
                            "user_context": {"location": "chennai", "device": "laptop1"}
                        },
                        stream=True
                    )
                    
                    if download_response.status_code == 200:
                        # Save downloaded file
                        with open(f"downloaded_{trial}.bin", "wb") as f:
                            for chunk in download_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        download_time = time.time() - start_download
                        
                        total_time = time.time() - start_total
                        workflow_times.append({
                            "upload_time": upload_time,
                            "download_time": download_time,
                            "total_time": total_time,
                            "upload_throughput": size_mb / upload_time,
                            "download_throughput": size_mb / download_time,
                            "overall_throughput": size_mb / total_time
                        })
                        
                        # Cleanup
                        os.remove(f"downloaded_{trial}.bin")
                
                # Cleanup
                os.remove(test_file)
            
            if workflow_times:
                results[f"{size_mb}MB"] = {
                    "avg_upload_time": sum(w["upload_time"] for w in workflow_times) / len(workflow_times),
                    "avg_download_time": sum(w["download_time"] for w in workflow_times) / len(workflow_times),
                    "avg_total_time": sum(w["total_time"] for w in workflow_times) / len(workflow_times),
                    "avg_upload_throughput": sum(w["upload_throughput"] for w in workflow_times) / len(workflow_times),
                    "avg_download_throughput": sum(w["download_throughput"] for w in workflow_times) / len(workflow_times),
                    "avg_overall_throughput": sum(w["overall_throughput"] for w in workflow_times) / len(workflow_times),
                    "successful_trials": len(workflow_times)
                }
                print(f"    ✅ {size_mb}MB: {results[f'{size_mb}MB']['avg_overall_throughput']:.2f} MB/sec overall")
        
        return results

if __name__ == "__main__":
    print("🧪 End-to-End Performance Benchmark")
    print("⚠️  Make sure server is running on http://127.0.0.1:5000")
    
    benchmark = EndToEndBenchmark()
    results = benchmark.benchmark_complete_workflow()
    
    # Save results
    with open("app/benchmarks/results/e2e_results.json", "w") as f:
        json.dump({"e2e_benchmarks": results}, f, indent=2)
    
    print("📁 Results saved to benchmarks/results/e2e_results.json")
