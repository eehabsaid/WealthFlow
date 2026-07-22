import os
import sys
import argparse
from datetime import datetime


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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from start_doc_server import start_server
from stop_doc_server import stop_server

from doc_engine.playwright_engine import get_playwright_backend

def run_capture(language='en', theme='dark', device=None, host='127.0.0.1', port='8001', backend=None):
    """
    Reusable function to generate documentation screenshots.
    Delegates capture execution to the active PlaywrightBackend strategy.
    """
    backend_strategy = get_playwright_backend(backend)
    backend_name = backend_strategy.__class__.__name__

    gen_dir = os.path.join(BASE_DIR, 'docs', 'generated')
    os.makedirs(gen_dir, exist_ok=True)
    cancel_flag = os.path.join(gen_dir, 'cancel.flag')
    if os.path.exists(cancel_flag):
        os.remove(cancel_flag)

    try:
        log("\n--- Starting Documentation Generation ---")
        log(f"Backend Strategy: {backend_name} | Language: {language} | Theme: {theme} | Device: {device or 'desktop'}")

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
            port=port
        )
        log(f"{backend_name} completed with success={success}.")
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
    parser.add_argument('--backend', default=None, choices=['python', 'javascript'], help="Playwright Backend Engine")

    args = parser.parse_args()

    run_capture(
        language=args.lang,
        theme=args.theme,
        device=args.device,
        host=args.host,
        port=args.port,
        backend=args.backend
    )
