"""NamingMixin: output-folder creation, filename templating, and the
hierarchical tree-flattening helper used before rendering. See this
package's __init__.py for the sibling list and composition conventions."""
import os

from ..config import SUPPORTED_FORMATS


class NamingMixin:
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

