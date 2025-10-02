# benchmarks/run_all_tests.py
import subprocess
import time
import json
import os
from datetime import datetime

class ComprehensiveTestSuite:
    def __init__(self):
        self.results = {
            "test_run_timestamp": datetime.now().isoformat(),
            "test_results": {}
        }
    
    def run_all_benchmarks(self):
        """Run all performance tests"""
        print("🚀 Starting Comprehensive Performance Test Suite")
        print("=" * 60)
        
        # 1. Component benchmarks (no server needed)
        print("\n1️⃣ Running Component Benchmarks...")
        try:
            result = subprocess.run(
                ["python", "app/benchmarks/performance_benchmark.py"],
                capture_output=True, text=True, timeout=300
            )
            self.results["test_results"]["component_benchmark"] = {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }
            print("✅ Component benchmarks completed")
        except Exception as e:
            print(f"❌ Component benchmarks failed: {e}")
        
        # 2. End-to-end benchmarks (requires server)
        print("\n2️⃣ Running End-to-End Benchmarks...")
        if self._check_server_running():
            try:
                result = subprocess.run(
                    ["python", "app/benchmarks/e2e_benchmark.py"],
                    capture_output=True, text=True, timeout=300
                )
                self.results["test_results"]["e2e_benchmark"] = {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "errors": result.stderr
                }
                print("✅ End-to-end benchmarks completed")
            except Exception as e:
                print(f"❌ E2E benchmarks failed: {e}")
        else:
            print("⚠️ Server not running, skipping E2E tests")
        
        # 3. Load testing
        print("\n3️⃣ Running Load Tests...")
        if self._check_server_running():
            try:
                result = subprocess.run(
                    ["python", "app/benchmarks/load_test.py"],
                    capture_output=True, text=True, timeout=600
                )
                self.results["test_results"]["load_test"] = {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "errors": result.stderr
                }
                print("✅ Load tests completed")
            except Exception as e:
                print(f"❌ Load tests failed: {e}")
        
        # Save comprehensive results
        self._save_results()
        self._print_summary()
    
    def _check_server_running(self):
        """Check if server is running"""
        try:
            import requests
            response = requests.get("http://127.0.0.1:5000/list", timeout=5)
            return response.status_code in [200, 405]  # 405 is method not allowed, but server is up
        except:
            return False
    
    def _save_results(self):
        """Save all test results"""
        os.makedirs("app/benchmarks/results", exist_ok=True)
        results_file = f"app/benchmarks/results/comprehensive_test_{int(time.time())}.json"
        
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📁 Comprehensive results saved to: {results_file}")
    
    def _print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🎯 COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)
        
        for test_name, test_result in self.results["test_results"].items():
            status = "✅ PASSED" if test_result["success"] else "❌ FAILED"
            print(f"{test_name}: {status}")
        
        print("=" * 60)

if __name__ == "__main__":
    suite = ComprehensiveTestSuite()
    suite.run_all_benchmarks()
