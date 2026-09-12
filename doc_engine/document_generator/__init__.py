"""DocumentationGenerator, split into a package to stay under the
200-line-per-file ceiling. Structural split only - no logic changes.

Siblings:
- init_mixin.py: InitMixin - construction, output paths, provider/renderer/
  guide registration.
- translation.py: TranslationMixin - single-key and title translation
  lookups.
- validation.py: ValidationMixin - loads/validates manifest, metadata, and
  i18n translations; builds the DocumentationModel.
- naming.py: NamingMixin - output-folder creation, filename templating,
  and tree flattening.
- generation.py: GenerationMixin - generate_all() top-level orchestration.
- guide_render.py: GuideRenderMixin - per-guide multi-format rendering.
- finalize.py: FinalizeMixin - latest-folder refresh, execution summary,
  and status persistence.

DocumentationGenerator below composes all mixins via multiple inheritance
so every method still shares a single `self` exactly as it did in the
original monolithic class. This __init__.py is the only place the composed
class is defined - always import from this package root
(`doc_engine.document_generator`), never from a sibling module directly.
"""
from .init_mixin import InitMixin
from .translation import TranslationMixin
from .validation import ValidationMixin
from .naming import NamingMixin
from .generation import GenerationMixin
from .guide_render import GuideRenderMixin
from .finalize import FinalizeMixin


class DocumentationGenerator(
    InitMixin,
    TranslationMixin,
    ValidationMixin,
    NamingMixin,
    GenerationMixin,
    GuideRenderMixin,
    FinalizeMixin,
):
    pass


if __name__ == "__main__":
    gen = DocumentationGenerator()
    gen.generate_all()
