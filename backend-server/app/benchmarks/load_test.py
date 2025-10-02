# benchmarks/load_test.py
import requests
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor

class LoadTester:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()
    
    def single_request_test(self, request_id):
        """Single FL scoring request"""
        start = time.time()
        try:
            # Test FL scoring endpoint (simulated)
            response = requests.post(
                f"{self.base_url}/download",
                json={
                    "username": "alice",
                    "file_id": "test-id", 
                    "user_context": {"location": "chennai", "device": "laptop1"}
                },
                timeout=10
            )
            duration = time.time() - start
            
            with self.lock:
                self.results.append({
                    "request_id": request_id,
                    "duration": duration,
                    "status_code": response.status_code,
                    "success": response.status_code in [200, 403, 404]  # Expected codes
                })
        except Exception as e:
            duration = time.time() - start
            with self.lock:
                self.results.append({
                    "request_id": request_id,
                    "duration": duration,
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                })
    
    def run_load_test(self, concurrent_users=[1, 5, 10, 20], requests_per_user=10):
        """Run load test with different concurrency levels"""
        print("🚀 Running Load Test...")
        
        load_results = {}
        
        for users in concurrent_users:
            print(f"  🔄 Testing {users} concurrent users...")
            self.results = []
            
            start_time = time.time()
            
            # Run concurrent requests
            with ThreadPoolExecutor(max_workers=users) as executor:
                futures = []
                for user in range(users):
                    for req in range(requests_per_user):
                        request_id = f"user_{user}_req_{req}"
                        futures.append(executor.submit(self.single_request_test, request_id))
                
                # Wait for all requests to complete
                for future in futures:
                    future.result()
            
            total_time = time.time() - start_time
            
            # Analyze results
            successful_requests = sum(1 for r in self.results if r["success"])
            total_requests = len(self.results)
            avg_response_time = sum(r["duration"] for r in self.results) / len(self.results)
            requests_per_second = total_requests / total_time
            
            load_results[f"{users}_users"] = {
                "concurrent_users": users,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": successful_requests / total_requests,
                "avg_response_time_sec": avg_response_time,
                "requests_per_second": requests_per_second,
                "total_time_sec": total_time
            }
            
            print(f"    ✅ {users} users: {requests_per_second:.1f} req/sec, {avg_response_time*1000:.1f}ms avg")
        
        return load_results

if __name__ == "__main__":
    print("⚡ Load Testing Tool")
    print("⚠️  Make sure server is running!")
    
    tester = LoadTester()
    results = tester.run_load_test()
    
    # Save results
    with open("benchmarks/results/load_test_results.json", "w") as f:
        json.dump({"load_test": results}, f, indent=2)
    
    print("📊 Load test completed!")
