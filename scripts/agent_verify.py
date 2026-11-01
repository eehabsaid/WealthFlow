"""Automated verification of a change: python scripts/agent_verify.py [files...] [--full]  (no files = every changed file in git)"""

import sys

import agent_cli
from core.services.ai.coding.verify import render, verify

ROOT = agent_cli.ROOT  # importing agent_cli sets up Django

args = [a for a in sys.argv[1:] if not a.startswith("--")]
result = verify(args or None, full_suite="--full" in sys.argv)
print(render(result))
sys.exit(0 if result["overall"].startswith("VERIFIED") else 1)
