"""InitMixin: DocumentationGenerator construction - output paths, provider
and renderer/guide registration. See this package's __init__.py for the
sibling list and composition conventions."""
import os
import time
from datetime import datetime

from ..config import GENERATED_DIR
from ..providers import ManifestProvider, ContentProvider
from ..renderers import MarkdownRenderer, HtmlRenderer, PdfRenderer, DocxRenderer
from ..guides import UserGuideGenerator, AdminGuideGenerator, TechnicalGuideGenerator


class InitMixin:
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

