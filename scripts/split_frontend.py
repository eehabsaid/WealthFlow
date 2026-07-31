filepath = r"d:\MyApps\WealthFlow\static\js\fixed_assets\details.js"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

tabs = [
    ("General", "renderGeneralTab"),
    ("Property", "renderPropertyTab"),
    ("Vehicle", "renderVehicleTab"),
    ("Gold", "renderGoldTab"),
    ("Other Details", "renderOtherDetailsTab"),
    ("Photos", "renderPhotosTab"),
    ("Renovation", "renderRenovationTab"),
    ("Furniture", "renderFurnitureTab"),
    ("Valuation", "renderValuationTab"),
    ("Maintenance", "renderMaintenanceTab"),
    ("Insurance", "renderInsuranceTab"),
    ("Mortgage", "renderMortgageTab"),
    ("Rental", "renderRentalTab"),
    ("Sale", "renderSaleTab"),
    ("Documents", "renderDocumentsTab"),
]

functions_code = []

for tab_name, func_name in tabs:
    # We need to find the start of the tab pane.
    # It starts with `<div class="tab-pane` and ends with `</div> <!-- End {tab_name} Tab -->`
    # Let's find the end marker first.
    end_marker = f"</div> <!-- End {tab_name} Tab -->"
    end_idx = content.find(end_marker)
    if end_idx == -1:
        print(f"Could not find end marker for {tab_name}")
        continue
    
    # Now find the preceding `<div class="tab-pane`
    start_idx = content.rfind('<div class="tab-pane', 0, end_idx)
    if start_idx == -1:
        print(f"Could not find start marker for {tab_name}")
        continue
        
    # include the end marker length
    full_end_idx = end_idx + len(end_marker)
    
    # Extract the block
    block = content[start_idx:full_end_idx]
    
    # The block might have preceding HTML comments like <!-- 1. GENERAL TAB PANE -->
    # Let's include that if it exists right before.
    comment_start = content.rfind('<!--', 0, start_idx)
    if comment_start != -1:
        # Check if it's right before (ignoring whitespace)
        between = content[comment_start:start_idx].strip()
        if between.startswith('<!--') and between.endswith('-->'):
             # it is just the comment
             start_idx = comment_start
             block = content[start_idx:full_end_idx]

    # Replace the block in content with `${func_name}()}`
    # Wait, it's inside a template literal. So `${func_name}()}` is correct.
    replacement = f"${{{func_name}()}}"
    content = content[:start_idx] + replacement + content[full_end_idx:]
    
    # Create the function code
    # We need to escape any backticks in the block just in case, though there likely aren't any.
    # The block should be wrapped in `return \` ... \`;`
    func_code = f"function {func_name}() {{\n  return `{block}`;\n}}\n"
    functions_code.append(func_code)

# Append all functions to the end of the file
content += "\n" + "\n".join(functions_code)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Frontend split complete.")
