"""Before changing files: python scripts/agent_plan.py path1 path2 ..."""

import json
import sys

import agent_cli
from core.services.ai.coding.plan import plan_check

ROOT = agent_cli.ROOT  # importing agent_cli sets up Django

print(json.dumps(plan_check(sys.argv[1:]), indent=2, ensure_ascii=False))
