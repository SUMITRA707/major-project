# app/fluentd_integration.py
from flask import Flask, request, jsonify
import json, os, datetime
app = Flask(__name__)
OUT = 'logs/events.log'
os.makedirs(os.path.dirname(OUT), exist_ok=True)

@app.route('/ingest', methods=['POST'])
def ingest():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({'status':'error','reason':'invalid json'}), 400
    payload['_received_at'] = datetime.datetime.utcnow().isoformat() + 'Z'
    with open(OUT,'a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\\n")
    return jsonify({'status':'ok'}), 201

if __name__=='__main__':
    app.run(host='0.0.0.0', port=24224)
