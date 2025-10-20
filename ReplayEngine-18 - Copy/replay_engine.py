import os
import json
import pandas as pd
from datetime import datetime
from jinja2 import Template
from flask import Flask  # Simple web server for report

app = Flask(__name__)

def load_logs(input_dir):
    """Load and merge all JSONL logs"""
    all_logs = []
    for file in os.listdir(input_dir):
        if file.endswith('.jsonl'):
            with open(os.path.join(input_dir, file), 'r') as f:
                for line in f:
                    try:
                        all_logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
    
    # ← ADD THIS BLOCK HERE (before return)
    # Auto-export from Fluentd if no local files
    import subprocess
    if not os.listdir(input_dir):
        result = subprocess.run(['docker', 'exec', 'fluentd', 'fluent-cat', '/fluentd/log/events.log'], capture_output=True, text=True)
        with open(os.path.join(input_dir, 'auto_export.jsonl'), 'w') as f:
            f.write(result.stdout)
        print("Auto-exported logs from Fluentd")
        # Re-load the auto-exported file
        with open(os.path.join(input_dir, 'auto_export.jsonl'), 'r') as f:
            for line in f:
                try:
                    all_logs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass
    
    return pd.DataFrame(all_logs)

def detect_bugs(df):
    """Detect bugs: ERROR logs, timeouts (message contains 'timeout')"""
    bugs = df[df['level'] == 'ERROR'] | df[df['message'].str.contains('timeout', case=False, na=False)]
    return bugs

def group_by_correlation(df):
    """Group by request_id (correlation)"""
    return df.groupby('request_id')

def generate_html_report(df, bugs, groups):
    """Generate simple HTML report"""
    html_template = """
    <!DOCTYPE html>
    <html><body>
    <h1>Replay Engine Report</h1>
    <h2>Total Events: {{ total }}</h2>
    <h2>Bugs Detected: {{ bugs_count }}</h2>
    <ul>{% for bug in bugs %}<li>{{ bug.timestamp }}: {{ bug.message }} (ID: {{ bug.request_id }})</li>{% endfor %}</ul>
    <h2>Correlated Groups:</h2>
    <ul>{% for gid, group in groups.items() %}<li>Group {{ gid }}: {{ group.shape[0] }} events</li>{% endfor %}</ul>
    </body></html>
    """
    t = Template(html_template)
    output = t.render(
        total=len(df),
        bugs_count=len(bugs),
        bugs=bugs.to_dict('records')[:10],  # Top 10 bugs
        groups={gid: len(g) for gid, g in groups}
    )
    with open('/app/output/report.html', 'w') as f:
        f.write(output)

@app.route('/')
def serve_report():
    return open('/app/output/report.html').read()

if __name__ == '__main__':
    # Run replay
    print("Starting replay...")
    df = load_logs('/app/logs')
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')  # Deterministic replay order
        bugs = detect_bugs(df)
        groups = group_by_correlation(df)
        generate_html_report(df, bugs, groups)
        print(f"Replayed {len(df)} events. {len(bugs)} bugs detected.")
        print("Serving report at http://localhost:8080")
    else:
        print("No logs found. Add sample logs to /logs/")
    app.run(host='0.0.0.0', port=8080)