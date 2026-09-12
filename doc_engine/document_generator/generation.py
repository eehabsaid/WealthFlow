"""GenerationMixin: top-level generate_all() orchestration - validates
inputs, snapshots manifest/metadata, and drives each guide type through
rendering. See this package's __init__.py for the sibling list and
composition conventions."""
import os
import shutil

from ..config import MANIFEST_FILE, METADATA_FILE, CANCEL_FILE


class GenerationMixin:
    def generate_all(self, doc_type="all"):
        if not self._validate_inputs():
            self._write_execution_summary()
            return
            
        os.makedirs(self.output_base_dir, exist_ok=True)
        
        if os.path.exists(MANIFEST_FILE):
            shutil.copy2(MANIFEST_FILE, os.path.join(self.output_base_dir, "manifest.json"))
        if os.path.exists(METADATA_FILE):
            shutil.copy2(METADATA_FILE, os.path.join(self.output_base_dir, "capture_metadata.json"))
            
        guides_to_run = [g for g in self.guides if doc_type == "all" or g(None).get_guide_type() == doc_type]
        self.total_guides = len(guides_to_run)
        if self.total_guides == 0:
            self._write_execution_summary()
            return
            
        self.current_guide_idx = 0
            
        for guide_cls in guides_to_run:
            self.current_guide_idx += 1
            if os.path.exists(CANCEL_FILE):
                self._update_status({"status": "CANCELLED"})
                break
            
            guide = guide_cls(self.doc_model)
            self._generate_guide(guide)
            
        if not os.path.exists(CANCEL_FILE):
            self._update_latest_symlink()
            self._write_execution_summary()

