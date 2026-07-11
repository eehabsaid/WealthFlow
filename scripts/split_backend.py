import ast
import os
import shutil

ROOT_DIR = r"d:\MyApps\WealthFlow"
VIEWS_FILE = os.path.join(ROOT_DIR, "core", "views", "fixed_asset_views.py")

SERVICES_DIR = os.path.join(ROOT_DIR, "core", "services", "fixed_assets")
VIEWS_DIR = os.path.join(ROOT_DIR, "core", "views", "fixed_assets")

os.makedirs(SERVICES_DIR, exist_ok=True)
os.makedirs(VIEWS_DIR, exist_ok=True)

with open(VIEWS_FILE, "r", encoding="utf-8") as f:
    source = f.read()

lines = source.splitlines(keepends=True)

tree = ast.parse(source)

# We want to identify the import block and pyright suppression
imports_lines = []
for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        imports_lines.extend(lines[node.lineno - 1:node.end_lineno])
    # Also grab sys imports and try-except imports
    elif isinstance(node, ast.If) and hasattr(node.test, "left") and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__":
        imports_lines.extend(lines[node.lineno - 1:node.end_lineno])

# Let's get the pyright line
pyright_line = lines[0]

header = "".join([pyright_line, "\n"] + imports_lines + ["\n\n"])

def extract_node(node):
    # include leading decorators for classes/functions
    start = node.lineno - 1
    if hasattr(node, "decorator_list") and node.decorator_list:
        start = node.decorator_list[0].lineno - 1
    end = node.end_lineno
    return "".join(lines[start:end]) + "\n\n"

# Mapping of file names to the list of function/class names
file_map = {
    "core/services/fixed_assets/gold_sync_service.py": [
        "_to_decimal", "_gold_unit_factor", "_gold_weight_in_grams", "_normalize_gold_purity", 
        "_gold_sell_price_per_gram", "_gold_cashback_per_gram", "_latest_gold_price", 
        "_refresh_gold_asset_pricing", "_sync_gold_balance_from_assets", 
        "_refresh_all_gold_assets_from_live_prices", "_sync_gold_details"
    ],
    "core/services/fixed_assets/vehicle_service.py": [
        "_sync_vehicle_details"
    ],
    "core/services/fixed_assets/property_service.py": [
        "_sync_asset_mortgage", "_sync_asset_rental"
    ],
    "core/services/fixed_assets/asset_maintenance_service.py": [
        "_sync_asset_maintenance", "_sync_asset_insurance", "_sync_asset_furniture"
    ],
    "core/services/fixed_assets/asset_purchase_service.py": [
        "_normalize_purchase_payments_payload", "_apply_asset_purchase_rows_delta", 
        "_purchase_rows_from_instances", "_sync_asset_purchase_payments",
        "_normalize_asset_payment_method", "_asset_payment_requires_bank",
        "_asset_payment_currency_required", "_default_egp_currency_id",
        "_get_asset_cash_balance_entry", "_apply_asset_balance_delta"
    ],
    "core/services/fixed_assets/asset_sale_service.py": [
        "_resolve_sale_deposit_values", "_sale_payment_row"
    ],
    "core/views/fixed_assets/fixed_asset_core_views.py": [
        "FixedAssetListView", "FixedAssetDetailView"
    ],
    "core/views/fixed_assets/fixed_asset_photo_views.py": [
        "FixedAssetPhotoView", "AssetPhotoView"
    ],
    "core/views/fixed_assets/fixed_asset_document_views.py": [
        "DocumentListUploadView", "DocumentFileView", "DocumentCategoriesView"
    ],
    "core/views/fixed_assets/fixed_asset_renovation_views.py": [
        "AssetRenovationListView", "AssetRenovationDetailView"
    ],
    "core/views/fixed_assets/fixed_asset_maintenance_views.py": [
        "AssetMaintenanceListView", "AssetMaintenanceDetailView"
    ],
    "core/views/fixed_assets/fixed_asset_insurance_views.py": [
        "AssetInsuranceListView", "AssetInsuranceDetailView"
    ],
    "core/views/fixed_assets/fixed_asset_furniture_views.py": [
        "AssetFurnitureListView", "AssetFurnitureDetailView"
    ],
    "core/views/fixed_assets/fixed_asset_valuation_views.py": [
        "AssetValuationHistoryListView", "AssetValuationHistoryDetailView"
    ],
    "core/views/fixed_assets/fixed_asset_sale_views.py": [
        "AssetSaleView"
    ]
}

# Any function/class not in this map but present in the file
# needs to be handled.
# _clear_non_selected_asset_details -> maybe put in fixed_asset_core_views.py? Or asset_purchase_service?
# wait, it is a helper. I will put it in fixed_asset_core_views.py for now if not mapped, or a common file.
# Also _document_validation_error_response, _document_database_error_response -> fixed_asset_document_views.py
# _sync_other_asset_details -> we can put in property_service.py or create other_asset_service.py
# _sync_asset_valuation_history -> put in fixed_asset_valuation_views.py or similar service?

file_map["core/services/fixed_assets/property_service.py"].append("_sync_other_asset_details")
file_map["core/services/fixed_assets/asset_maintenance_service.py"].append("_sync_asset_valuation_history")
file_map["core/views/fixed_assets/fixed_asset_core_views.py"].append("_clear_non_selected_asset_details")
file_map["core/views/fixed_assets/fixed_asset_document_views.py"].extend(["_document_validation_error_response", "_document_database_error_response"])

# Create a mapping of entity to file
entity_to_file = {}
for path, entities in file_map.items():
    for e in entities:
        entity_to_file[e] = path

file_contents = {path: [header] for path in file_map.keys()}
unmapped = []

# Populate file contents
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        name = node.name
        if name in entity_to_file:
            path = entity_to_file[name]
            file_contents[path].append(extract_node(node))
        else:
            unmapped.append(name)

# Ensure all files are written
for path, blocks in file_contents.items():
    full_path = os.path.join(ROOT_DIR, os.path.normpath(path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as out:
        out.write("".join(blocks))

# Now, generate the shim for fixed_asset_views.py
shim_lines = [pyright_line, "\n"]
for path, entities in file_map.items():
    module_path = path.replace("core/", "core.").replace(".py", "").replace("/", ".")
    for e in entities:
        shim_lines.append(f"from {module_path} import {e}\n")

with open(VIEWS_FILE, "w", encoding="utf-8") as f:
    f.write("".join(shim_lines))

# Generate empty __init__.py files for the new dirs just in case
open(os.path.join(SERVICES_DIR, "__init__.py"), "a").close()
open(os.path.join(VIEWS_DIR, "__init__.py"), "a").close()

print(f"Unmapped entities: {unmapped}")
print("Done splitting backend.")
