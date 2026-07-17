import os
import sys
import time
import urllib.request
import subprocess
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def start_server():
    port = os.environ.get('DOC_PORT', '8001')
    host = os.environ.get('DOC_HOST', '127.0.0.1')
    
    log(f"Starting documentation server on {host}:{port}...")
    
    # Path to manage.py
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manage_py = os.path.join(base_dir, 'manage.py')
    
    # Python executable from current environment (venv)
    python_exe = sys.executable
    
    # Start process
    proc = subprocess.Popen(
        [python_exe, manage_py, 'runserver', f'{host}:{port}'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    
    # Write PID
    pid_dir = os.path.join(base_dir, 'docs', 'generated')
    os.makedirs(pid_dir, exist_ok=True)
    with open(os.path.join(pid_dir, 'server.pid'), 'w') as f:
        f.write(str(proc.pid))
        
    # Wait for server
    log("Waiting for server...")
    url = f"http://{host}:{port}/accounts/login/"
    timeout = 30
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            req = urllib.request.urlopen(url)
            if req.getcode() == 200:
                log("Server is ready.")
                return True
        except Exception:
            pass
        time.sleep(0.5)
        
    log("Error: Server failed to start or respond in time.")
    return False

if __name__ == "__main__":
    start_server()
