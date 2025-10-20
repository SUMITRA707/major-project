"""Test integrated replay with Universal Logging"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'adapters'))

from fluentd_adapter import FluentdLogAdapter
import time

def test_replay_from_universal_logging():
    print("\n" + "="*70)
    print("INTEGRATED REPLAY ENGINE TEST")
    print("="*70 + "\n")
    
    # Fetch logs from Universal Logging
    print("📥 Fetching logs from universal logging microservice...")
    adapter = FluentdLogAdapter()
    logs = adapter.fetch_logs(limit=100)
    
    if not logs:
        print("❌ No logs found. Run some tests first:")
        print("   cd ..")
        print("   cd universal-logging-hook-microservice")
        print("   python tests\\test_working.py")
        return
    
    print(f"✅ Fetched {len(logs)} logs\n")
    
    # Sort logs deterministically
    print("🔄 Sorting logs deterministically...")
    sorted_logs = sorted(
        logs, 
        key=lambda x: (
            x.get('session_id', ''),
            x.get('sequence', 0),
            x.get('timestamp', '')
        )
    )
    
    # Replay logs
    print("\n" + "="*70)
    print("REPLAYING LOGS IN DETERMINISTIC ORDER")
    print("="*70 + "\n")
    
    for i, log in enumerate(sorted_logs[:15], 1):
        level = log.get('level', 'UNKNOWN')
        message = log.get('message', 'No message')
        session = log.get('session_id', 'N/A')
        sequence = log.get('sequence', 'N/A')
        source = log.get('source', 'N/A')
        
        print(f"{i:2d}. [{level:5s}] {message}")
        print(f"     Source: {source}")
        if session != 'N/A':
            print(f"     Session: {session[:16]}... | Seq: {sequence}")
        
        # Show metrics if available
        metrics = log.get('metrics', {})
        if metrics and 'cpu_percent' in metrics:
            print(f"     CPU: {metrics.get('cpu_percent', 0):.1f}% | Memory: {metrics.get('memory_usage_mb', 0):.1f}MB")
        
        print()
        time.sleep(0.3)
    
    print("="*70)
    print("✅ REPLAY COMPLETED!")
    print("="*70)
    print(f"\n📊 Total logs available: {len(logs)}")
    print(f"🔄 Replayed: {min(15, len(logs))} logs")
    print("\n💡 Key Features Demonstrated:")
    print("   • Deterministic ordering (session + sequence)")
    print("   • Cross-service log correlation")
    print("   • Metric tracking during replay")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_replay_from_universal_logging()