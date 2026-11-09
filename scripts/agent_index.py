"""Search the auto-built repo index: python scripts/agent_index.py <name part> [--callers]"""

import json
import sys

import agent_cli
from ai.services.coding import index

ROOT = agent_cli.ROOT  # importing agent_cli sets up Django

if len(sys.argv) < 2:
    sys.exit("usage: agent_index.py <name part> [--callers]")
query = sys.argv[1]
print(json.dumps({"callers": index.callers(query)} if "--callers" in sys.argv else {"matches": index.find(query)}, indent=2, ensure_ascii=False))
