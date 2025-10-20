
from flask import Flask, request, jsonify
import subprocess
import threading
import os
import signal
import sys
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, filename='logs/api_server.log',
                    format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
proc = None
proc_lock = threading.Lock()

def get_script_path():
    """Resolve the path to ReplayEnhanced.py dynamically."""
    return os.path.join(os.path.dirname(__file__), 'ReplayEnhanced.py')

def terminate_process():
    """Safely terminate the subprocess."""
    with proc_lock:
        global proc
        if proc and proc.poll() is None:
            logger.info(f"Terminating process {proc.pid}")
            try:
                os.killpg(proc.pid, signal.SIGTERM)  # Terminate process group
                proc.wait(timeout=5)  # Wait up to 5 seconds
            except subprocess.TimeoutExpired:
                logger.warning(f"Process {proc.pid} did not terminate, sending SIGKILL")
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            except Exception as e:
                logger.error(f"Failed to terminate process {proc.pid}: {e}")
            finally:
                proc = None

@app.route('/start', methods=['POST'])
def start_replay():
    global proc
    with proc_lock:
        if proc and proc.poll() is None:
            logger.info("Replay process already running")
            return jsonify({'status': 'already_running', 'pid': proc.pid}), 200

        args = request.get_json(silent=True) or {}
        pattern = args.get('pattern', 'logs/events.log*')
        if not isinstance(pattern, str) or not pattern.strip():
            logger.error("Invalid pattern provided")
            return jsonify({'status': 'error', 'message': 'Pattern must be a non-empty string'}), 400

        cmd = [sys.executable, get_script_path(), '-p', pattern]
        try:
            # Use setsid to create a new process group
            proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
            logger.info(f"Started replay process with PID {proc.pid}")
            return jsonify({'status': 'started', 'pid': proc.pid}), 200
        except (FileNotFoundError, OSError) as e:
            logger.error(f"Failed to start replay process: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop_replay():
    global proc
    with proc_lock:
        if not proc or proc.poll() is not None:
            logger.info("No replay process running")
            return jsonify({'status': 'not_running'}), 200
        terminate_process()
        return jsonify({'status': 'stopped'}), 200

@app.route('/status', methods=['GET'])
def status():
    with proc_lock:
        if not proc:
            return jsonify({'running': False, 'status': 'not_started'}), 200
        if proc.poll() is None:
            return jsonify({'running': True, 'pid': proc.pid}), 200
        exit_code = proc.poll()
        logger.info(f"Replay process terminated with exit code {exit_code}")
        return jsonify({'running': False, 'status': 'terminated', 'exit_code': exit_code}), 200

def shutdown_hook():
    """Clean up subprocess on server shutdown."""
    logger.info("Server shutting down, cleaning up subprocess")
    terminate_process()

if __name__ == '__main__':
    # Ensure log directory exists
    os.makedirs('logs', exist_ok=True)
    # Register shutdown hook
    import atexit
    atexit.register(shutdown_hook)
    # Run Flask in non-debug mode for production
    app.run(host='0.0.0.0', port=6000, debug=False)