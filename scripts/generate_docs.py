import os
import sys
import argparse
from datetime import datetime

from dotenv import load_dotenv

def log(msg):
    now_str = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{now_str}] {msg}")
    except UnicodeEncodeError:
        safe_msg = msg.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace')
        print(f"[{now_str}] {safe_msg}")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Load WF_USERNAME/WF_PASSWORD (and any other local overrides) from a .env
# file at the project root if present. Safe no-op otherwise. This covers
# running this script directly from the CLI, outside of Django.
load_dotenv(os.path.join(BASE_DIR, ".env"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from start_doc_server import start_server
from stop_doc_server import stop_server

from doc_engine.playwright_engine import get_playwright_backend

def run_capture(language='en', theme='dark', device=None, host='127.0.0.1', port='8001',
                 username=None, password=None):
    """
    Reusable function to generate documentation screenshots.
    Executes Python Playwright capture engine natively.
    """
    backend_strategy = get_playwright_backend()

    gen_dir = os.path.join(BASE_DIR, 'docs', 'generated')
    os.makedirs(gen_dir, exist_ok=True)
    cancel_flag = os.path.join(gen_dir, 'cancel.flag')
    if os.path.exists(cancel_flag):
        os.remove(cancel_flag)

    try:
        log("\n--- Starting Documentation Generation ---")
        log(f"Backend Strategy: PythonPlaywrightBackend | Language: {language} | Theme: {theme} | Device: {device or 'desktop'}")

        os.environ['DOC_HOST'] = host
        os.environ['DOC_PORT'] = port

        if not start_server():
            log("Failed to start server. Aborting.")
            return False

        success = backend_strategy.capture(
            language=language,
            theme=theme,
            device=device,
            host=host,
            port=port,
            username=username,
            password=password
        )
        log(f"PythonPlaywrightBackend completed with success={success}.")
        return success

    finally:
        stop_server()
        log("Finished.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Documentation Screenshots")
    parser.add_argument('--lang', default='en', help="Language")
    parser.add_argument('--theme', default='dark', choices=['dark', 'light'], help="Theme")
    parser.add_argument('--device', default=None, help="Device to emulate (e.g., 'iPhone 13')")
    parser.add_argument('--host', default='127.0.0.1', help="Server Host")
    parser.add_argument('--port', default='8001', help="Server Port")
    parser.add_argument('--username', default=None,
                         help="Login username for the capture session. Falls back to the "
                              "WF_USERNAME environment variable if not given.")
    parser.add_argument('--password', default=None,
                         help="Login password for the capture session. Falls back to the "
                              "WF_PASSWORD environment variable if not given.")

    args = parser.parse_args()

    run_capture(
        language=args.lang,
        theme=args.theme,
        device=args.device,
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password
    )
