# benchmarks/resource_monitor.py
import psutil
import time
import json
import threading
from datetime import datetime

class ResourceMonitor:
    def __init__(self):
        self.monitoring = False
        self.data = []
        self.monitor_thread = None
    
    def start_monitoring(self, interval=1.0):
        """Start monitoring system resources"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.start()
        print("📊 Resource monitoring started...")
    
    def stop_monitoring(self):
        """Stop monitoring and return results"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("📊 Resource monitoring stopped.")
        return self.get_summary()
    
    def _monitor_loop(self, interval):
        """Main monitoring loop"""
        while self.monitoring:
            # Get current resource usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            net_io = psutil.net_io_counters()
            
            self.data.append({
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / 1024 / 1024,
                "disk_read_mb": disk_io.read_bytes / 1024 / 1024 if disk_io else 0,
                "disk_write_mb": disk_io.write_bytes / 1024 / 1024 if disk_io else 0,
                "network_sent_mb": net_io.bytes_sent / 1024 / 1024 if net_io else 0,
                "network_recv_mb": net_io.bytes_recv / 1024 / 1024 if net_io else 0
            })
            
            time.sleep(interval)
    
    def get_summary(self):
        """Get monitoring summary"""
        if not self.data:
            return {}
        
        cpu_values = [d["cpu_percent"] for d in self.data]
        memory_values = [d["memory_percent"] for d in self.data]
        
        return {
            "monitoring_duration_sec": len(self.data),
            "cpu_usage": {
                "avg_percent": sum(cpu_values) / len(cpu_values),
                "max_percent": max(cpu_values),
                "min_percent": min(cpu_values)
            },
            "memory_usage": {
                "avg_percent": sum(memory_values) / len(memory_values),
                "max_percent": max(memory_values),
                "peak_used_mb": max(d["memory_used_mb"] for d in self.data)
            },
            "sample_count": len(self.data),
            "raw_data": self.data
        }

# Usage example:
if __name__ == "__main__":
    monitor = ResourceMonitor()
    
    print("Starting resource monitoring...")
    monitor.start_monitoring(interval=0.5)
    
    # Simulate some work
    time.sleep(10)
    
    summary = monitor.stop_monitoring()
    
    print(f"CPU Usage: {summary['cpu_usage']['avg_percent']:.1f}% avg")
    print(f"Memory Usage: {summary['memory_usage']['avg_percent']:.1f}% avg")
