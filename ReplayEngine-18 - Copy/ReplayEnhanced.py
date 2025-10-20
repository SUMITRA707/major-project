# app/ReplayEnhanced.py
#!/usr/bin/env python.py
import json
import glob
import os
import sys
import time
import heapq
import argparse
import csv
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date
try:
    from html_report_generator import simple_html_report
except ImportError:
    simple_html_report = None
from bug_detector import BugDetector
import fcntl  # For file locking on Unix-like systems

def parse_ts(ts):
    if not ts:
        return None
    try:
        # Handle both ISO format and other timestamp formats
        return parse_date(ts).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None

def load_checkpoint(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_checkpoint(path, data):
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            # Acquire an exclusive lock to prevent concurrent writes
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        os.replace(tmp, path)
    except IOError as e:
        print(f"[ERROR] Failed to save checkpoint: {e}", file=sys.stderr)

def file_iter(path, offset, errlog):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            f.seek(offset)
            while True:
                pos = f.tell()
                line = f.readline()
                if not line:
                    break
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    errlog.write(json.dumps({"file": path, "offset": pos, "err": "bad json"}) + "\n")
                    errlog.flush()
                    continue
                ts = parse_ts(rec.get("time") or rec.get("timestamp") or rec.get("@timestamp"))
                if not ts:
                    errlog.write(json.dumps({"file": path, "offset": pos, "err": "bad ts", "raw": rec}) + "\n")
                    errlog.flush()
                    continue
                # Use byte length for accurate offset
                yield ts, rec, pos + len(line.encode('utf-8'))
    except IOError as e:
        errlog.write(json.dumps({"file": path, "err": f"IO error: {str(e)}"}) + "\n")
        errlog.flush()

def merged_stream(pattern, checkpoint, errlog):
    files = sorted(glob.glob(pattern))
    if not files:
        print("[WARNING] No files matched the pattern", file=sys.stderr)
        return
    iters = [file_iter(f, checkpoint.get(f, 0), errlog) for f in files]
    heap = []
    seq = 0
    for i, it in enumerate(iters):
        try:
            ts, rec, pos = next(it)
            seq += 1
            heapq.heappush(heap, (ts, seq, i, rec, pos, files[i]))
        except StopIteration:
            pass
    while heap:
        ts, seq, i, rec, pos, f = heapq.heappop(heap)
        checkpoint[f] = pos
        yield ts, seq, rec, f
        try:
            ts2, rec2, pos2 = next(iters[i])
            seq += 1
            heapq.heappush(heap, (ts2, seq, i, rec2, pos2, f))
        except StopIteration:
            pass

def save_debug_reports(entries, json_path, csv_path):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['log_index', 'file', 'original', 'issues'])
        for e in entries:
            w.writerow([e.get('log_index'), e.get('file'), json.dumps(e.get('original', {}), ensure_ascii=False), "; ".join(e.get('issues', []))])

def generate_html_report(events, bugs, summary, corr, outfile):
    if not simple_html_report:
        print("[ERROR] html_report_generator module not available", file=sys.stderr)
        return
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    simple_html_report(events, bugs, summary, corr, outfile)

def replay(args):
    if args.checkpoint_every <= 0:
        raise ValueError("checkpoint_every must be a positive integer")

    cp = {} if args.no_checkpoint else load_checkpoint(args.checkpoint)
    os.makedirs(os.path.dirname(args.errlog), exist_ok=True) if args.errlog else None
    with open(args.errlog, 'a', encoding='utf-8') if args.errlog else sys.stderr as errlog:
        out = None
        try:
            if args.output:
                os.makedirs(os.path.dirname(args.output), exist_ok=True)
                out = open(args.output, 'a', encoding='utf-8')
            start = parse_ts(args.start) if args.start else None
            end = parse_ts(args.end) if args.end else None
            min_gap = 1.0 / args.max_rate if args.max_rate > 0 else 0
            last_emit = 0
            last_ts = None

            detector = BugDetector(timeout_threshold=args.timeout)
            debug_entries = []
            events_for_report = []
            idx = 0

            for ts, seq, rec, f in merged_stream(args.pattern, cp, errlog):
                if start and ts < start:
                    continue
                if end and ts > end:
                    continue
                if args.level and rec.get('level', '').lower() != args.level.lower() if args.level else False:
                    continue
                if args.source and rec.get('source', '').lower() != args.source.lower() if args.source else False:
                    continue

                idx += 1
                now = time.time()
                if args.real_time and last_ts:
                    gap = (ts - last_ts).total_seconds()
                    if gap > 0:
                        time.sleep(min(gap, args.max_sleep))
                elif min_gap and last_emit:
                    wait = min_gap - (now - last_emit)
                    if wait > 0:
                        time.sleep(wait)

                # analysis
                bugs = detector.analyze(ts, rec)
                if bugs:
                    debug_entries.append({"log_index": idx, "file": f, "original": rec, "issues": bugs})
                    for b in bugs:
                        print("[BUG]", b)

                # output line (optional)
                line = {"ts": ts.isoformat(), "seq": seq, "file": f, "rec": rec}
                if out:
                    out.write(json.dumps(line, ensure_ascii=False) + "\n")
                    out.flush()
                else:
                    print(f"[REPLAY] {ts.isoformat()} | {rec.get('level')} | {rec.get('source')} | {rec.get('message')}")

                events_for_report.append({
                    "x": ts.isoformat(),
                    "y": rec.get("source", "unknown"),
                    "level": rec.get("level", "INFO"),
                    "event": rec.get("event_type") or rec.get("event", ""),
                    "message": rec.get("message", "")
                })

                last_emit = time.time()
                last_ts = ts

                if args.checkpoint and idx % args.checkpoint_every == 0:
                    save_checkpoint(args.checkpoint, cp)
        except KeyboardInterrupt:
            print("[INFO] interrupted")
        finally:
            if args.checkpoint:
                save_checkpoint(args.checkpoint, cp)
            if out:
                out.close()

        # save debug reports + html
        save_debug_reports(debug_entries, args.debug_json, args.debug_csv)
        summary = detector.error_summary()
        corr = detector.correlation_report()
        generate_html_report(events_for_report, detector.get_detected_bugs(), summary, corr, args.html_report)
        os.makedirs(os.path.dirname(args.summary_json), exist_ok=True)
        with open(args.summary_json, 'w', encoding='utf-8') as f:
            json.dump({"summary": summary, "bugs": detector.get_detected_bugs(), "correlation": corr}, f, indent=2)
        print("[INFO] reports saved")

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('-p', '--pattern', default='logs/events.log*')
    p.add_argument('-c', '--checkpoint', default='logs/replay.checkpoint.json')
    p.add_argument('--no-checkpoint', action='store_true')
    p.add_argument('--errlog', default='logs/replay.errors.log')
    p.add_argument('-o', '--output', default=None)
    p.add_argument('--real-time', action='store_true')
    p.add_argument('--max-rate', type=float, default=0.0)
    p.add_argument('--max-sleep', type=float, default=5.0)
    p.add_argument('--level', default=None)
    p.add_argument('--source', default=None)
    p.add_argument('--start', default=None)
    p.add_argument('--end', default=None)
    p.add_argument('--timeout', type=float, default=5.0)
    p.add_argument('--checkpoint-every', type=int, default=100)
    p.add_argument('--debug-json', default='reports/debug_report.json')
    p.add_argument('--debug-csv', default='reports/debug_report.csv')
    p.add_argument('--html-report', default='reports/bug_report.html')
    p.add_argument('--summary-json', default='reports/replay_summary.json')
    args = p.parse_args()
    replay(args)