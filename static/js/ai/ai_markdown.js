"use strict";

/**
 * AI Workspace — Markdown Renderer
 * Generic markdown & rich renderer pipeline used to render assistant messages.
 * Depends on: nothing (pure function).
 */

function _renderMarkdown(text) {
  if (!text) return "";

  let html = text;

  // 1. Protect code blocks first
  const codeBlocks = [];
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, function (match, lang, code) {
    codeBlocks.push({ lang: lang || "code", code: code });
    return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
  });

  // 2. HTML escape (excluding protected blocks)
  html = html.replace(/[&<>"']/g, function (m) {
    switch (m) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      case "'":
        return "&#039;";
      default:
        return m;
    }
  });

  // 3. Callout boxes (> [!NOTE], > [!WARNING], > [!TIP], > [!IMPORTANT])
  html = html.replace(
    /^&gt;\s*\[!(NOTE|WARNING|TIP|IMPORTANT)\]\s*(.*$)/gim,
    function (match, type, content) {
      const typeLower = type.toLowerCase();
      return `<div class="ai-ws-callout ${typeLower}"><strong>${type}:</strong> ${content}</div>`;
    }
  );

  // 4. Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // 5. Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

  // 6. Headings
  html = html.replace(/^### (.*$)/gim, "<h5>$1</h5>");
  html = html.replace(/^## (.*$)/gim, "<h4>$1</h4>");
  html = html.replace(/^# (.*$)/gim, "<h3>$1</h3>");

  // 7. Blockquotes
  html = html.replace(/^&gt;\s*(.*$)/gim, "<blockquote>$1</blockquote>");

  // 8. Horizontal rules
  html = html.replace(/^---$/gim, "<hr>");

  // 9. Checklists
  html = html.replace(/^\s*\[\s*\]\s+(.*)$/gim, '<div><i class="bi bi-square me-1"></i> $1</div>');
  html = html.replace(
    /^\s*\[[xX]\]\s+(.*)$/gim,
    '<div><i class="bi bi-check-square-fill text-success me-1"></i> $1</div>'
  );

  // 10. Unordered & Ordered Lists
  html = html.replace(/^\s*[-*]\s+(.*)$/gim, "<ul><li>$1</li></ul>");
  html = html.replace(/<\/ul>\n<ul>/g, "\n");

  html = html.replace(/^\s*\d+\.\s+(.*)$/gim, "<ol><li>$1</li></ol>");
  html = html.replace(/<\/ol>\n<ol>/g, "\n");

  // 11. Tables
  html = html.replace(/^\|(.+)\|$/gim, function (match, content) {
    const cells = content
      .split("|")
      .map((c) => `<td>${c.trim()}</td>`)
      .join("");
    return `<tr>${cells}</tr>`;
  });
  html = html.replace(
    /(<tr>.*?<\/tr>[\n\r]*)+/g,
    '<div class="ai-table-wrap"><table>$&</table></div>'
  );

  // 12. Line breaks
  html = html.replace(/\n/g, "<br>");

  // 13. Restore code blocks with language header
  html = html.replace(/__CODE_BLOCK_(\d+)__/g, function (match, index) {
    const block = codeBlocks[index];
    let codeContent = block.code.replace(/[&<>"']/g, function (m) {
      switch (m) {
        case "&":
          return "&amp;";
        case "<":
          return "&lt;";
        case ">":
          return "&gt;";
        case '"':
          return "&quot;";
        case "'":
          return "&#039;";
        default:
          return m;
      }
    });
    return `
      <div class="ai-ws-code-wrap">
        <div class="ai-ws-code-header">
          <span><i class="bi bi-code-slash me-1"></i> ${block.lang}</span>
        </div>
        <pre class="ai-ws-code-content"><code>${codeContent}</code></pre>
      </div>
    `;
  });

  return html;
}
