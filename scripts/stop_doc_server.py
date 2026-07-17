import os
import signal
import subprocess
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def kill_process_tree(pid):
    if os.name == 'nt':
        subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass

def stop_server():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pid_file = os.path.join(base_dir, 'docs', 'generated', 'server.pid')
    
    if not os.path.exists(pid_file):
        log("Nothing to stop.")
        return
        
    try:
        with open(pid_file, 'r') as f:
            pid_str = f.read().strip()
            if not pid_str:
                log("Nothing to stop.")
                return
            pid = int(pid_str)
            
        log(f"Stopping server with PID {pid}...")
        kill_process_tree(pid)
        log("Server stopped.")
    except Exception as e:
        log(f"Error stopping server: {e}")
    finally:
        if os.path.exists(pid_file):
            try:
                os.remove(pid_file)
            except OSError:
                pass

if __name__ == "__main__":
    stop_server()
