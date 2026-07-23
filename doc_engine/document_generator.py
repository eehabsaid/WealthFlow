import os
import json
import logging
import shutil
import time
from datetime import datetime

# Import plugins
from .config import GENERATED_DIR, MANIFEST_FILE, METADATA_FILE, CANCEL_FILE, STATUS_FILE, SUPPORTED_FORMATS
from .providers import ManifestProvider, ContentProvider
from .models import DocumentationModel
from .renderers import MarkdownRenderer, HtmlRenderer, PdfRenderer, DocxRenderer
from .guides import UserGuideGenerator, AdminGuideGenerator, TechnicalGuideGenerator

logger = logging.getLogger(__name__)

class DocumentationGenerator:
    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.start_time = time.time()
        self.output_base_dir = os.path.join(GENERATED_DIR, self.timestamp)
        self.latest_symlink = os.path.join(GENERATED_DIR, "latest")
        
        self.manifest = None
        self.metadata = None
        self.content = None
        self.doc_model = None
        
        # Load providers
        self.manifest_provider = ManifestProvider()
        self.content_provider = ContentProvider()
        
        # Register Renderers
        self.renderers = {
            "markdown": MarkdownRenderer(),
            "html": HtmlRenderer(),
            "pdf": PdfRenderer(),
            "docx": DocxRenderer(),
        }
        
        # Register Guide Types
        self.guides = [
            UserGuideGenerator,
            AdminGuideGenerator,
            TechnicalGuideGenerator
        ]

    def _t(self, key):
        if not hasattr(self, 'translations'):
            return key
        if key not in self.translations:
            logger.warning(f"Missing translation key: {key}")
            if f"Missing translation key: {key}" not in self.validation_warnings:
                self.validation_warnings.append(f"Missing translation key: {key}")
            return key
        return self.translations[key]

    def _load_metadata(self):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None

    def _validate_inputs(self):
        self.manifest = self.manifest_provider.load()
        self.content = self.content_provider.load()
        self.metadata = self._load_metadata()
        
        if not self.manifest:
            self.validation_errors.append("Fatal: manifest.json missing")
        if not self.metadata:
            self.validation_errors.append("Fatal: capture_metadata.json missing")
            
        if self.validation_errors:
            logger.error("Generation stopped due to fatal errors.")
            return False
            
        self.doc_model = DocumentationModel(self.manifest, self.content)
        self.validation_warnings.extend(self.doc_model.validation_warnings)
        
        # Load Translations
        self.translations = {}
        self.reverse_en = {}
        
        # Try metadata first, fallback to first page, default to 'en'
        lang = "en"
        if self.metadata and self.metadata.get("language"):
            lang = self.metadata.get("language")
        elif self.manifest and self.manifest.get("pages") and len(self.manifest["pages"]) > 0:
            lang = self.manifest["pages"][0].get("language", "en")
            
        lang = lang.lower()
        if lang == 'ar':
            lang = 'ar'
            
        i18n_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "i18n")
        
        # Load English for reverse lookup (to translate hardcoded English strings)
        en_path = os.path.join(i18n_dir, "en.json")
        try:
            if os.path.exists(en_path):
                with open(en_path, "r", encoding="utf-8") as f:
                    en_data = json.load(f)
                    self.reverse_en = {v.strip(): k for k, v in en_data.items() if isinstance(v, str)}
        except Exception as e:
            logger.warning(f"Could not load English translations for reverse lookup: {e}")

        i18n_path = os.path.join(i18n_dir, f"{lang}.json")
        try:
            if os.path.exists(i18n_path):
                with open(i18n_path, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
            else:
                self.validation_warnings.append(f"Translation file missing for language: {lang}")
        except Exception as e:
            logger.warning(f"Could not load translations for {lang}: {e}")
            
        return True

    def _t_title(self, text):
        if not text:
            return text
        text_strip = text.strip()
        # Direct key lookup
        if text_strip in self.translations:
            return self.translations[text_strip]
        # Reverse English lookup
        key = self.reverse_en.get(text_strip)
        if key and key in self.translations:
            return self.translations[key]
        return text

    def _create_folders(self, guide_type):
        guide_dir = os.path.join(self.output_base_dir, f"{guide_type}_guide")
        for fmt in SUPPORTED_FORMATS:
            os.makedirs(os.path.join(guide_dir, fmt), exist_ok=True)
        return guide_dir

    def _get_filename(self, guide_type, ext):
        lang = self.metadata.get('language', 'EN').upper() if self.metadata else 'EN'
        theme = self.metadata.get('theme', 'Dark').capitalize() if self.metadata else 'Dark'
        device = self.metadata.get('device', 'Desktop').capitalize() if self.metadata else 'Desktop'
        device = "".join(x for x in device if x.isalnum())
        return f"{guide_type.capitalize()}Guide_{lang}_{theme}_{device}.{ext}"

    def _flatten_tree(self, nodes, prefix="", sibling_nodes=None):
        flat = []
        if sibling_nodes is None:
            sibling_nodes = nodes
        for i, n in enumerate(nodes, 1):
            n.hierarchical_number = f"{prefix}{i}"
            
            if prefix == "":
                n.siblings = []
            else:
                n.siblings = [sn.title for sn in sibling_nodes if sn != n and not getattr(sn, 'is_modal', False)]
                
            if n.children and not getattr(n, 'is_modal', False):
                tab_children = [c.title for c in n.children if not getattr(c, 'is_modal', False)]
                if tab_children:
                    n.siblings = tab_children
                
            flat.append(n)
            flat.extend(self._flatten_tree(n.children, f"{n.hierarchical_number}.", n.children))
        return flat

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

    def _generate_guide(self, guide):
        filtered_nodes = guide.filter_model()
        if not filtered_nodes:
            return
            
        guide_type = guide.get_guide_type()
        guide_dir = self._create_folders(guide_type)
        
        md_path = os.path.join(guide_dir, "markdown", self._get_filename(guide_type, "md"))
        html_path = os.path.join(guide_dir, "html", self._get_filename(guide_type, "html"))
        pdf_path = os.path.join(guide_dir, "pdf", self._get_filename(guide_type, "pdf"))
        docx_path = os.path.join(guide_dir, "docx", self._get_filename(guide_type, "docx"))

        flat_model = self._flatten_tree(filtered_nodes)
        
        # Translate node titles
        for node in flat_model:
            node.title = self._t_title(node.title)
            node.navigation = [self._t_title(x) for x in node.navigation]
            
        context = {
            "app_name": self.manifest.get('application', 'WealthFlow'),
            "guide_type": guide_type.capitalize() + " Guide",
            "title": f"{self.manifest.get('application', 'WealthFlow')} - {guide_type.capitalize()} Guide",
            "date": datetime.now().strftime('%Y-%m-%d'),
            "language": self.metadata.get('language', 'EN').upper() if self.metadata else 'EN',
            "theme": self.metadata.get('theme', 'Dark').capitalize() if self.metadata else 'Dark',
            "device": self.metadata.get('device', 'Desktop').capitalize() if self.metadata else 'Desktop',
            "version": self.manifest.get('version', '1.0'),
            "toc_title": self._t_title("Table of Contents"),
            "nav_title": self._t_title("Navigation Path"),
            "purpose_title": self._t_title("Purpose"),
            "steps_title": self._t_title("Steps"),
            "tech_notes_title": self._t_title("Technical Details"),
            "page_title": self._t_title(guide_type.capitalize() + " Guide"),
            "figure_title": self._t_title("Figure"),
            "lbl_generated": self._t_title("Generated") if self._t_title("Generated") != "Generated" else "تاريخ الإنشاء",
            "lbl_language": self._t_title("Language") if self._t_title("Language") != "Language" else "اللغة",
            "lbl_theme": self._t_title("Theme") if self._t_title("Theme") != "Theme" else "المظهر",
            "lbl_device": self._t_title("Device") if self._t_title("Device") != "Device" else "الجهاز",
            "lbl_version": self._t_title("Version") if self._t_title("Version") != "Version" else "الإصدار",
            "lbl_generated_by": self._t_title("Generated By") if self._t_title("Generated By") != "Generated By" else "تم الإنشاء بواسطة",
            "is_technical": guide.is_technical()
        }
        
        # If language is AR, fallback these labels just in case
        if context["language"] == "AR":
            if context["guide_type"] == "User Guide": context["guide_type"] = "دليل المستخدم"
            if context["guide_type"] == "Admin Guide": context["guide_type"] = "دليل المسؤول"
            if context["guide_type"] == "Technical Guide": context["guide_type"] = "الدليل الفني"
            if context["title"].endswith("User Guide"): context["title"] = "WealthFlow - دليل المستخدم"
            if context["title"].endswith("Admin Guide"): context["title"] = "WealthFlow - دليل المسؤول"
            if context["title"].endswith("Technical Guide"): context["title"] = "WealthFlow - الدليل الفني"

        self._update_status({
            "status": "RUNNING",
            "current_guide": guide_type.capitalize(),
            "current_page": "Markdown",
            "current_output_format": "Markdown",
            "validation_stage": "Generating Markdown",
            "progress_percent": int(((self.current_guide_idx - 1) / self.total_guides) * 100) + 0,
            "elapsed": int(time.time() - self.start_time)
        })
        if "markdown" in SUPPORTED_FORMATS:
            self.renderers["markdown"].render(flat_model, md_path, context)
            
        self._update_status({
            "current_page": "HTML",
            "current_output_format": "HTML",
            "validation_stage": "Generating HTML",
            "progress_percent": int(((self.current_guide_idx - 1) / self.total_guides) * 100) + 6,
            "elapsed": int(time.time() - self.start_time)
        })
        if "html" in SUPPORTED_FORMATS:
            self.renderers["html"].render(md_path, html_path, context)
            
        self._update_status({
            "current_page": "PDF",
            "current_output_format": "PDF",
            "validation_stage": "Generating PDF",
            "progress_percent": int(((self.current_guide_idx - 1) / self.total_guides) * 100) + 12,
            "elapsed": int(time.time() - self.start_time)
        })
        if "pdf" in SUPPORTED_FORMATS:
            self.renderers["pdf"].render(html_path, pdf_path)
            
        self._update_status({
            "current_page": "DOCX",
            "current_output_format": "DOCX",
            "validation_stage": "Generating DOCX",
            "progress_percent": int(((self.current_guide_idx - 1) / self.total_guides) * 100) + 18,
            "elapsed": int(time.time() - self.start_time)
        })
        if "docx" in SUPPORTED_FORMATS:
            self.renderers["docx"].render(flat_model, docx_path, context)

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

if __name__ == "__main__":
    gen = DocumentationGenerator()
    gen.generate_all()
