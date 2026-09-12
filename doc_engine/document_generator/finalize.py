"""FinalizeMixin: post-run bookkeeping - refreshing the "latest" output
folder, writing the execution summary/validation report, and persisting
live status updates. See this package's __init__.py for the sibling list
and composition conventions."""
import os
import json
import shutil
import time
import logging
from datetime import datetime

from ..config import GENERATED_DIR, STATUS_FILE

logger = logging.getLogger(__name__)


class FinalizeMixin:
    def _update_latest_symlink(self):
        try:
            if os.path.exists(self.latest_symlink) or os.path.islink(self.latest_symlink):
                if os.path.isdir(self.latest_symlink) and not os.path.islink(self.latest_symlink):
                    shutil.rmtree(self.latest_symlink)
                else:
                    os.unlink(self.latest_symlink)
            shutil.copytree(self.output_base_dir, self.latest_symlink, dirs_exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to update latest folder: {e}")

    def _write_execution_summary(self):
        duration = time.time() - self.start_time
        pages_gen = len(self._flatten_tree(self.doc_model.nodes)) if self.doc_model else 0
        missing = len([w for w in self.validation_warnings if "Missing page description" in w])
        
        summary = {
            "started": self.timestamp,
            "finished": datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            "duration_seconds": round(duration, 2),
            "language": self.manifest.get('language', 'en') if self.manifest else 'en',
            "theme": self.manifest.get('theme', 'dark') if self.manifest else 'dark',
            "device": self.manifest.get('device', 'desktop') if self.manifest else 'desktop',
            "screenshot_count": self.metadata.get('screenshots', 0) if self.metadata else 0,
            "pages_generated": pages_gen,
            "missing_content_count": missing,
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "output_directory": self.output_base_dir
        }
        
        sum_path = os.path.join(self.output_base_dir, "generation_summary.json") if not self.validation_errors else os.path.join(GENERATED_DIR, f"generation_summary_{self.timestamp}.json")
        rep_path = os.path.join(self.output_base_dir, "validation_report.md") if not self.validation_errors else os.path.join(GENERATED_DIR, f"validation_report_{self.timestamp}.md")
        try:
            os.makedirs(os.path.dirname(sum_path), exist_ok=True)
            with open(sum_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=4)
                
            with open(rep_path, "w", encoding="utf-8") as f:
                f.write("# Documentation Validation Report\n\n")
                f.write(f"**Date:** {summary['started']}\n\n")
                if self.validation_errors:
                    f.write("## Fatal Errors\n")
                    for e in self.validation_errors:
                        f.write(f"- {e}\n")
                if self.validation_warnings:
                    f.write("\n## Warnings\n")
                    for w in self.validation_warnings:
                        f.write(f"- {w}\n")
                if not self.validation_errors and not self.validation_warnings:
                    f.write("No errors or warnings. Generation clean.\n")
        except Exception as e:
            logger.error(f"Failed to write summary: {e}")
            
    def _update_status(self, updates):
        try:
            status = {}
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    status = json.load(f)
            status.update(updates)
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(status, f)
        except Exception as e:
            logger.error(f"Failed to update status: {e}")

