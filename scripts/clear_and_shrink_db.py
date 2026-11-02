import os
import sys
from pathlib import Path
import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wealthflow.settings")
django.setup()

from django.db import connection

# Delete all AI training traces
with connection.cursor() as cursor:
    cursor.execute('DELETE FROM "ai_training_agenttrace"')
    cursor.execute('DELETE FROM "axes_accesslog"')

print("All AI training traces deleted.")

# Compact SQLite database
connection.ensure_connection()
connection.connection.isolation_level = None

with connection.cursor() as cursor:
    cursor.execute("VACUUM")

print("SQLite database compacted successfully.")