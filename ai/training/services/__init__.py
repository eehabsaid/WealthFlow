"""Agent-trace training data (milestone 1): record Agent runs, judge them with code only, export the proven ones.

recorder.py   stores a run (context.py switches it on)      judges.py     data / method / repeat checks, no model involved
generator.py  questions + expected answers from live data   runner.py     asks the questions through the real chat endpoint
export.py     JSONL of kept traces + plain report            textutil.py   number and script helpers (no word lists)
"""
