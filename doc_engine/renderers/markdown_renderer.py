"""MarkdownRenderer: renders a flattened doc-model tree into the
AUTO-GENERATED markdown source used as the input for HTML/PDF/DOCX
rendering. See this package's __init__.py for the sibling list."""
import os


class MarkdownRenderer:
    def render(self, flat_model, out_path, context):
        lines = []
        lines.append("<!-- AUTO-GENERATED START -->\n")
        lines.append(f"# {context['title']}\n")
        lines.append(f"**Application Name:** {context['app_name']}\n")
        lines.append(f"**Guide Type:** {context['guide_type']}\n")
        lines.append(f"**{context['lbl_generated']}:** {context['date']}  \n")
        lines.append(f"**{context['lbl_language']}:** {context['language']}  \n")
        lines.append(f"**{context['lbl_theme']}:** {context['theme']}  \n")
        lines.append(f"**{context['lbl_device']}:** {context['device']}  \n")
        lines.append(f"**{context['lbl_version']}:** {context['version']}  \n")
        lines.append(f"**{context['lbl_generated_by']}:** WealthFlow Documentation Engine  \n")
        lines.append("\n---\n")
        
        lines.append(f"## {context['toc_title']}\n")
        for item in flat_model:
            anchor = item.title.lower().replace(' ', '-')
            indent = "  " * (len(item.hierarchical_number.split('.')) - 1)
            lines.append(f"{indent}- **{item.hierarchical_number}** [{item.title}](#{anchor})\n")
        lines.append("\n---\n")

        for i, item in enumerate(flat_model, 1):
            h_level = min(2 + len(item.hierarchical_number.split('.')) - 1, 6)
            h_prefix = "#" * h_level
            lines.append(f"{h_prefix} {item.hierarchical_number} {item.title}\n")
            
            nav_path = " &rarr; ".join(item.navigation)
            lines.append(f"**{context['nav_title']}:** {nav_path}\n")
            
            if item.purpose:
                lines.append(f"**{context['purpose_title']}:** {item.purpose}\n")
            
            for s_idx, s_path in enumerate(item.screenshots):
                if os.path.exists(s_path):
                    lines.append("<figure>")
                    lines.append(f"<img src=\"file:///{s_path.replace(chr(92), '/')}\" style=\"max-width: 100%; height: auto; display: block; margin: 0 auto;\" alt=\"{item.title}\">")
                    lines.append(f"<figcaption style=\"text-align:center; font-style:italic;\">{context['figure_title']} {i}.{s_idx+1}: {item.title}</figcaption>")
                    lines.append("</figure>\n")
            
            if context['is_technical']:
                lines.append(f"**{context['tech_notes_title']}:**\n")
                lines.append(f"- Route Hierarchy: `{nav_path}`\n")
                lines.append(f"- Base Route: `{getattr(item, 'route', 'N/A')}`\n")
                lines.append("\n")
            elif item.steps:
                lines.append(f"**{context['steps_title']}:**\n")
                for s_idx, step in enumerate(item.steps, 1):
                    lines.append(f"{s_idx}. {step}")
                lines.append("\n")
                
            if item.siblings:
                lines.append("**Related Pages:**")
                for s_idx, sib in enumerate(item.siblings, 1):
                    lines.append(f"- {sib}")
                lines.append("\n")
            lines.append("---\n")
            
        lines.append("<!-- AUTO-GENERATED END -->\n")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

