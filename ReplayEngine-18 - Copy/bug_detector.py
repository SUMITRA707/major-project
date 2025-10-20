# app/bug_detector.py
from collections import defaultdict, Counter
from datetime import datetime, timezone

class BugDetector:
    """
    Analyse logs to detect:
     - error/exception events
     - timeout gaps between events (threshold seconds)
     - collect correlation flows (per request id)
    """
    def __init__(self, timeout_threshold=5):
        self.timeout_threshold = timeout_threshold
        self.last_ts = None
        self.error_counts = Counter()
        self.event_counts = Counter()
        self.detected_bugs = []          # list[str]
        self.correlation_flows = defaultdict(list)

    def analyze(self, ts, record):
        """
        ts : datetime (UTC)
        record : dict (parsed JSON log)
        returns: list of bug strings detected for this record
        """
        bugs = []
        self.event_counts[record.get("source","unknown")] += 1

        level = str(record.get("level","")).upper()
        if level in ("ERROR","EXCEPTION","ERR"):
            svc = record.get("source","unknown")
            self.error_counts[svc] += 1
            msg = record.get("message","")
            s = f"[ERROR] {svc} at {ts.isoformat()} -> {msg}"
            bugs.append(s)
            self.detected_bugs.append(s)

        # timeout gap
        if self.last_ts:
            gap = (ts - self.last_ts).total_seconds()
            if gap > self.timeout_threshold:
                s = f"[TIMEOUT] gap {gap:.1f}s at {ts.isoformat()} (th={self.timeout_threshold}s)"
                bugs.append(s)
                self.detected_bugs.append(s)

        # correlation id capture
        corr = record.get("correlationId") or record.get("correlation_id") or record.get("traceId")
        if corr:
            self.correlation_flows[corr].append({"ts": ts.isoformat(), "source": record.get("source"), "message": record.get("message")})

        self.last_ts = ts
        return bugs

    def error_summary(self):
        return {
            "total_events": sum(self.event_counts.values()),
            "total_errors": sum(self.error_counts.values()),
            "errors_by_service": dict(self.error_counts),
            "events_by_service": dict(self.event_counts),
        }

    def correlation_report(self):
        return dict(self.correlation_flows)

    def get_detected_bugs(self):
        return list(self.detected_bugs)
