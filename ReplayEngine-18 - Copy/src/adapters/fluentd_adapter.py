"""Adapter to read logs from Universal Logging Microservice"""
import subprocess
import json
from datetime import datetime

class FluentdLogAdapter:
    """Reads logs from Fluentd container"""
    
    def __init__(self):
        self.logs = []
    
    def fetch_logs(self, limit=1000):
        """Fetch logs from Fluentd Docker container"""
        try:
            result = subprocess.run(
                ["docker", "logs", "universal-logging-fluentd", "--tail", str(limit)],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse JSON logs
            for line in result.stdout.strip().split('\n'):
                try:
                    if line.strip():
                        log = json.loads(line)
                        self.logs.append(log)
                except json.JSONDecodeError:
                    continue
            
            print(f"✅ Fetched {len(self.logs)} logs from Universal Logging")
            return self.logs
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error fetching logs: {e}")
            return []
    
    def get_logs_by_session(self, session_id):
        """Get all logs for a specific session"""
        return [log for log in self.logs if log.get('session_id') == session_id]
    
    def get_logs_by_source(self, source):
        """Get logs from specific source"""
        return [log for log in self.logs if log.get('source') == source]