"""The skills, decisions and files relevant to a task: python scripts/agent_context.py "task text" [budget_chars]"""

import sys

import agent_cli
from ai.services.coding import context

ROOT = agent_cli.ROOT  # importing agent_cli sets up Django

if len(sys.argv) < 2:
    sys.exit('usage: agent_context.py "task text" [budget_chars]')
picked = context.pick(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 6000)
for s in picked["skills"]:
    print(f"## SKILL {s['name']}\n{s['text']}\n")
print("## DECISIONS\n" + "\n".join(picked["decisions"]) + "\n\n## FILES\n" + "\n".join(picked["index"]))
