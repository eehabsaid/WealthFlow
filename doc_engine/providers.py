import json
import logging
from .config import MANIFEST_FILE, CONTENT_FILE

logger = logging.getLogger(__name__)

class ManifestProvider:
    def __init__(self, path=MANIFEST_FILE):
        self.path = path
        
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load manifest {self.path}: {e}")
            return None

class ContentProvider:
    def __init__(self, path=CONTENT_FILE):
        self.path = path
        
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load content {self.path}: {e}")
            return {}
