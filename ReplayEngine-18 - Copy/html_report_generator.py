import json
import os
import html

def simple_html_report(events, bugs, summary, corr, outfile):
    # Handle directory creation safely
    if os.path.dirname(outfile):
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
    
    # Generate services and points
    services = sorted({e['y'] for e in events}) if events else []
    points = []
    for e in events:
        points.append({
            "x": e['x'],
            "y": services.index(e['y']) if services else 0,
            "level": e.get('level', 'INFO'),
            "event": e.get('event', ''),
            "message": e.get('message', '')
        })
    
    # Escape JSON for safe HTML rendering
    summary_json = html.escape(json.dumps(summary, indent=2, ensure_ascii=False))
    bugs_json = html.escape(json.dumps(bugs, indent=2, ensure_ascii=False))
    corr_json = html.escape(json.dumps(corr, indent=2, ensure_ascii=False))
    
    # Generate HTML with Chart.js and date adapter
    html_content = f"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Replay Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3"></script>
    <style>
        #timeline {{ width: 100%; max-width: 1000px; height: 300px; }}
    </style>
</head>
<body>
    <h2>Replay Report Dashboard</h2>
    {'<p>No events to display.</p>' if not events else '<canvas id="timeline"></canvas>'}
    <script>
        const points = {json.dumps(points, ensure_ascii=False)};
        const serviceLabels = {json.dumps(services, ensure_ascii=False)};
        const data = {{
            datasets: [{{
                label: 'Events',
                data: points.map(p => ({{
                    x: p.x,
                    y: p.y,
                    level: p.level,
                    event: p.event,
                    message: p.message
                }})),
                pointRadius: 6,
                pointBackgroundColor: points.map(p => 
                    (p.level && p.level.toUpperCase && p.level.toUpperCase().startsWith('ERR')) ? 'red' : 
                    (p.level && p.level.toUpperCase && p.level.toUpperCase() === 'INFO') ? 'green' : 'orange'
                )
            }}]
        }};
        const config = {{
            type: 'scatter',
            data: data,
            options: {{
                scales: {{
                    x: {{
                        type: 'time',
                        time: {{ unit: 'second' }},
                        title: {{ display: true, text: 'Time' }}
                    }},
                    y: {{
                        ticks: {{ callback: function(v) {{ return serviceLabels[v] || ''; }} }},
                        title: {{ display: true, text: 'Service' }}
                    }}
                }}
            }}
        }};
        {'new Chart(document.getElementById("timeline"), config);' if events else '// No chart data'}
    </script>
    <h3>Summary</h3>
    <pre>{summary_json}</pre>
    <h3>Detected Bugs</h3>
    <pre>{bugs_json}</pre>
    <h3>Correlation Flows</h3>
    <pre>{corr_json}</pre>
</body>
</html>
"""
    try:
        with open(outfile, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("[INFO] wrote", outfile)
    except IOError as e:
        print(f"[ERROR] Failed to write {outfile}: {e}", file=sys.stderr)