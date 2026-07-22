import os
import json
import copy
from typing import Dict, List, Any, Optional, Tuple
from doc_engine.config import DOC_ENGINE_DIR

class InventoryProvider:
    """
    Service responsible for loading and resolving inventory data (pages, tabs, modals, devices).
    Isolates discovery source from automation execution.
    """
    def __init__(self, inventory_path: Optional[str] = None, device_inventory_path: Optional[str] = None):
        self.inventory_path = inventory_path or os.path.join(DOC_ENGINE_DIR, "inventory.json")
        self.device_inventory_path = device_inventory_path or os.path.join(DOC_ENGINE_DIR, "device_inventory.json")

    def get_page_inventory(self) -> List[Dict[str, Any]]:
        """Loads and returns a deep copy of raw page inventory items."""
        if not os.path.exists(self.inventory_path):
            raise FileNotFoundError(f"Page inventory file missing: {self.inventory_path}")
        with open(self.inventory_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return copy.deepcopy(data)

    def get_device_inventory(self) -> Dict[str, Any]:
        """Loads and returns device inventory data if available."""
        if not os.path.exists(self.device_inventory_path):
            return {}
        try:
            with open(self.device_inventory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def resolve_device_config(self, device_name: Optional[str]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Resolves context options and launch args for Playwright based on requested device.
        Returns (context_options, launch_args).
        """
        default_context = {"viewport": None}
        default_args = ["--start-maximized"]

        if not device_name or device_name == "Desktop Chrome" or device_name == "current" or device_name == "Desktop":
            return default_context, default_args

        inventory = self.get_device_inventory()
        found_device = None
        if inventory and "categories" in inventory:
            for cat_items in inventory["categories"].values():
                for item in cat_items:
                    if isinstance(item, dict) and item.get("id") == device_name:
                        found_device = item
                        break
                if found_device:
                    break

        if found_device and "execution" in found_device:
            exec_cfg = found_device["execution"]
            exec_type = exec_cfg.get("type")
            exec_val = exec_cfg.get("value")

            if exec_type == "current":
                return default_context, default_args
            elif exec_type == "viewport" and isinstance(exec_val, dict):
                return {"viewport": exec_val}, []
            elif exec_type == "playwright" and isinstance(exec_val, str):
                return {"playwright_device": exec_val}, []

        # Fallback to direct Playwright device name match
        return {"playwright_device": device_name}, []
