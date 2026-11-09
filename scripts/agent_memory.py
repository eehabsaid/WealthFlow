"""Persistent coding-agent memory: python scripts/agent_memory.py add "text" | list"""

import sys

import agent_cli
from ai.services.coding import memory

ROOT = agent_cli.ROOT  # importing agent_cli sets up Django

if sys.argv[1:2] == ["add"] and len(sys.argv) > 2:
    print(memory.add(sys.argv[2]))
else:
    print("\n".join(memory.entries()))
