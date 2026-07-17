# WealthFlow Documentation Engine

This module is a completely integrated Playwright documentation generator designed specifically for WealthFlow. It automatically navigates through all pages, clicks all tabs, opens all modals, and takes clean screenshots based on the configuration provided.

## Folder Structure
- `doc_engine/capture_pages.js`: The core Playwright script handling browser automation.
- `docs/screenshots/`: The final destination where all screenshots are saved. **This folder is wiped out completely at the start of every run.**
- `docs/generated/`: Contains internal states like the server PID (`server.pid`), cancellation flags (`cancel.flag`), and the live-updating `capture_status.json`.
- `scripts/generate_docs.py`: The master execution script intended for both CLI use and backend integration.
- `scripts/start_doc_server.py`: Spins up the Django server required for taking screenshots on port 8001.
- `scripts/stop_doc_server.py`: Kills the screenshot server.

## Installation
The documentation engine shares the WealthFlow root structure and Python environment.

1. Install Python dependencies (from WealthFlow root):
   ```bash
   pip install -r requirements.txt
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Install Playwright browser binaries:
   ```bash
   npx playwright install chromium
   ```

## Manual Execution
You can run the engine directly from the WealthFlow root.
```bash
# Default (English, Dark theme, Desktop)
python scripts/generate_docs.py

# Arabic, Light theme, Mobile emulation
python scripts/generate_docs.py --lang ar --theme light --device "iPhone 13"
```
The script will automatically start the server, generate screenshots into `docs/screenshots/`, and cleanly terminate the server when complete.

## How Future UI Will Call the Engine
The UI will **not** invoke the command line. Instead, it will directly import and run the python function exposed by the engine:
```python
from scripts.generate_docs import run_capture

# Future Django view/Celery task:
success = run_capture(
    language='en',    # Passed from UI dropdown
    theme='dark',     # Passed from UI dropdown
    device=None,      # Passed from UI dropdown, e.g., 'iPhone 13'
    host='127.0.0.1', 
    port='8001'
)
```
The engine uses `docs/generated/capture_status.json` to stream live progress, which the UI can poll to show a progress bar to the end user.

## Troubleshooting
- **Server fails to start**: Make sure port 8001 is not blocked. You can run `python scripts/stop_doc_server.py` to kill any orphaned processes manually.
- **Node module errors**: Ensure you ran `npm install` and that `node_modules` exists in the WealthFlow root.
- **Missing binaries**: If you see Playwright errors about missing browsers, run `npx playwright install chromium`.
- **Cancellation**: If you need to stop the script mid-execution programmatically, create an empty file at `docs/generated/cancel.flag`.
