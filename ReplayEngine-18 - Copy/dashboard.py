# app/dashboard.py
import dash, dash_core_components as dcc, dash_html_components as html
from dash.dependencies import Output, Input
import json, os
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H2("Replay Engine Dashboard"),
    dcc.Interval(id='interval', interval=5000),
    html.Div(id='content')
])
@app.callback(Output('content','children'), [Input('interval','n_intervals')])
def update(_):
    path = 'reports/replay_summary.json'
    if not os.path.exists(path):
        return html.Div("No summary yet. Run the replay.")
    s = json.load(open(path))
    return html.Pre(json.dumps(s, indent=2))
if __name__=='__main__':
    app.run_server(host='0.0.0.0', port=8050, debug=True)
