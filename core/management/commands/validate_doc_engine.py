import os
from django.core.management.base import BaseCommand
from django.conf import settings
from doc_engine.device_inventory import validate_inventory

class Command(BaseCommand):
    help = 'Validates the Documentation Engine architecture, including device inventory and required directories.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Validating Documentation Engine...")
        
        has_error = False

        # 1. Validate device_inventory.json
        self.stdout.write("Checking device_inventory.json...")
        is_valid, err_msg = validate_inventory()
        
        if not is_valid:
            self.stdout.write(self.style.ERROR(f"[FAIL] {err_msg}"))
            has_error = True
        else:
            self.stdout.write(self.style.SUCCESS("[PASS] device_inventory.json is valid (version, schema, duplicates, defaults)."))

        # 2. Validate folders
        docs_dir = os.path.join(settings.BASE_DIR, "docs")
        generated_dir = os.path.join(docs_dir, "generated")
        screenshots_dir = os.path.join(docs_dir, "screenshots")
        
        folders_to_check = [docs_dir, generated_dir, screenshots_dir]
        for folder in folders_to_check:
            self.stdout.write(f"Checking directory: {os.path.relpath(folder, settings.BASE_DIR)}...")
            if not os.path.exists(folder):
                self.stdout.write(self.style.ERROR(f"[FAIL] Directory missing: {folder}"))
                has_error = True
            else:
                self.stdout.write(self.style.SUCCESS(f"[PASS] Directory exists: {folder}"))

        # 3. Validate README
        readme_path = os.path.join(settings.BASE_DIR, "README.md")
        self.stdout.write(f"Checking root README.md...")
        if not os.path.exists(readme_path):
            self.stdout.write(self.style.ERROR(f"[FAIL] Root README.md missing: {readme_path}"))
            has_error = True
        else:
            self.stdout.write(self.style.SUCCESS(f"[PASS] README.md exists."))

        if has_error:
            self.stdout.write(self.style.ERROR("\nValidation finished with errors. The Documentation Engine is NOT healthy."))
        else:
            self.stdout.write(self.style.SUCCESS("\nValidation finished successfully. The Documentation Engine is healthy."))
