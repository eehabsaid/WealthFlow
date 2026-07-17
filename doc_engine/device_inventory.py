import json
import os
from django.conf import settings

import hashlib

DEVICE_INVENTORY_FILE = os.path.join(settings.BASE_DIR, "doc_engine", "device_inventory.json")

_inventory_cache = None

def load_inventory(force_reload=False):
    global _inventory_cache
    if not force_reload and _inventory_cache is not None:
        return _inventory_cache
        
    if not os.path.exists(DEVICE_INVENTORY_FILE):
        return {}
    try:
        with open(DEVICE_INVENTORY_FILE, "r", encoding="utf-8") as f:
            _inventory_cache = json.load(f)
            return _inventory_cache
    except Exception:
        return {}

def get_inventory_hash():
    if not os.path.exists(DEVICE_INVENTORY_FILE):
        return ""
    try:
        with open(DEVICE_INVENTORY_FILE, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return ""

def validate_inventory():
    inventory = load_inventory(force_reload=True)
    
    if not isinstance(inventory, dict):
        return False, "Inventory must be a JSON object"
        
    if "version" not in inventory:
        return False, "Inventory missing version field"
        
    if inventory["version"] != 1:
        return False, f"Unsupported inventory version: {inventory['version']}"
        
    categories = inventory.get("categories")
    if not isinstance(categories, dict):
        return False, "Inventory missing valid categories object"
    
    seen_ids = set()
    seen_playwright = set()
    
    for cat_name, items in categories.items():
        if not isinstance(items, list):
            return False, f"Category '{cat_name}' must be a list"
        
        default_count = 0
        for item in items:
            item_id = item.get("id")
            if not item_id:
                return False, f"Missing id in category '{cat_name}'"
            if item_id in seen_ids:
                return False, f"Duplicate id: {item_id}"
            seen_ids.add(item_id)
            
            if item.get("default"):
                if not item.get("enabled", True):
                    return False, f"Default device '{item_id}' must be enabled"
                default_count += 1
                
            execution = item.get("execution")
            if not execution or not isinstance(execution, dict):
                return False, f"Device '{item_id}' missing valid execution object"
            
            exec_type = execution.get("type")
            if exec_type not in ["current", "viewport", "playwright"]:
                return False, f"Device '{item_id}' has invalid execution type '{exec_type}'"
            
            if exec_type == "viewport":
                val = execution.get("value")
                if not isinstance(val, dict) or "width" not in val or "height" not in val:
                    return False, f"Device '{item_id}' viewport must have width and height"
            elif exec_type == "playwright":
                val = execution.get("value")
                if not val:
                    return False, f"Device '{item_id}' playwright execution must have value"
                if val in seen_playwright:
                    return False, f"Duplicate playwright name: {val}"
                seen_playwright.add(val)
                
        if default_count != 1:
            return False, f"Category '{cat_name}' must have exactly one default device. Found {default_count}."
            
    return True, ""

def get_categories():
    inventory = load_inventory()
    categories = inventory.get("categories", {})
    return categories

def get_devices(category):
    categories = get_categories()
    return categories.get(category, [])

def get_default_device(category):
    devices = get_devices(category)
    for device in devices:
        if device.get("default"):
            return device
    return None
