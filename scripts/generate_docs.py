import os
import sys
import subprocess
import argparse
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# Add current directory to path to import other scripts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from start_doc_server import start_server
from stop_doc_server import stop_server

def run_capture(language='en', theme='dark', device=None, host='127.0.0.1', port='8001'):
    """
    Reusable function to generate documentation screenshots.
    This can be called by future Django UI code.
    """
    # Set environment variables for the JS script
    env = os.environ.copy()
    env['DOC_HOST'] = host
    env['DOC_PORT'] = port
    env['DOC_LANG'] = language
    env['DOC_THEME'] = theme
    if device:
        env['DOC_DEVICE'] = device
    else:
        env.pop('DOC_DEVICE', None)
        
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    capture_script = os.path.join(base_dir, 'doc_engine', 'capture_pages.js')
    
    # Ensure generated directory exists for cancellation flags
    gen_dir = os.path.join(base_dir, 'docs', 'generated')
    os.makedirs(gen_dir, exist_ok=True)
    cancel_flag = os.path.join(gen_dir, 'cancel.flag')
    if os.path.exists(cancel_flag):
        os.remove(cancel_flag)
        
    try:
        log("\n--- Starting Documentation Generation ---")
        log(f"Language: {language}, Theme: {theme}, Device: {device or 'desktop'}")
        
        # 1. Start Server
        # Since start_server relies on env vars internally, update them here too
        os.environ['DOC_HOST'] = host
        os.environ['DOC_PORT'] = port
        
        if not start_server():
            log("Failed to start server. Aborting.")
            return False
            
        # 2. Run Playwright Script
        log("Running Playwright...")
        proc = subprocess.run(['node', capture_script], env=env)
        
        log(f"Playwright completed with exit code {proc.returncode}.")
        return proc.returncode == 0
        
    finally:
        # 3. Always Stop Server
        stop_server()
        log("Finished.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Documentation Screenshots")
    parser.add_argument('--lang', default='en', choices=['en', 'ar','fr','de'], help="Language")
    parser.add_argument('--theme', default='dark', choices=['dark', 'light'], help="Theme")
    parser.add_argument('--device', default=None, help="Device to emulate (e.g., 'iPhone 13')")
    parser.add_argument('--host', default='127.0.0.1', help="Server Host")
    parser.add_argument('--port', default='8001', help="Server Port")
    
    args = parser.parse_args()
    
    run_capture(
        language=args.lang,
        theme=args.theme,
        device=args.device,
        host=args.host,
        port=args.port
    )
