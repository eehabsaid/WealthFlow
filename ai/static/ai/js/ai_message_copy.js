"use strict";

/**
 * AI Workspace — Copy response button
 * Extracts plain text from rendered assistant messages (headings, lists, tables,
 * code blocks, callouts, inline formatting) and copies to clipboard.
 * Depends on: ai_core.js (_aiT), ai_feedback.js (feedback bar structure)
 */

/**
 * Strip HTML tags and decode entities to produce readable plain text.
 * Preserves structure: headings become lines, lists get bullets, tables get tabs,
 * code blocks keep their content, callouts add a label prefix.
 */
function _extractPlainTextFromHTML(html) {
  if (!html) return "";

  let text = html;

  // 1. Headings → plain lines (remove tags, keep text)
  text = text.replace(/<h[1-6][^>]*>(.*?)<\/h[1-6]>/gi, "$1\n");

  // 2. Callouts → "NOTE: content" etc.
  text = text.replace(
    /<div[^>]*class="[^"]*ai-ws-callout[^"]*"[^>]*>(.*?)<\/div>/gi,
    function (_match, inner) {
      const labelMatch = inner.match(/<strong>(NOTE|WARNING|TIP|IMPORTANT):<\/strong>/i);
      const label = labelMatch ? labelMatch[1] + ": " : "";
      const content = inner.replace(/<[^>]+>/g, "").trim();
      return label + content + "\n";
    }
  );

  // 3. Code blocks → preserve content as-is
  text = text.replace(
    /<div[^>]*class="[^"]*ai-ws-code-wrap[^"]*"[^>]*>(.*?)<\/div>/gis,
    function (_match, inner) {
      const codeMatch = inner.match(/<code>(.*?)<\/code>/is);
      return codeMatch
        ? codeMatch[1].replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&") + "\n"
        : "";
    }
  );

  // 4. Tables → tab-separated rows
  text = text.replace(/<table[^>]*>(.*?)<\/table>/gis, function (_match, inner) {
    const rows = inner.match(/<tr[^>]*>(.*?)<\/tr>/gis) || [];
    return (
      rows
        .map((row) => {
          const cells = row.match(/<t[dh][^>]*>(.*?)<\/t[dh]>/gis) || [];
          return cells.map((cell) => cell.replace(/<[^>]+>/g, "").trim()).join("\t");
        })
        .join("\n") + "\n"
    );
  });

  // 5. Lists → bullet/number prefix
  text = text.replace(/<ul[^>]*>/gi, "");
  text = text.replace(/<\/ul>/gi, "\n");
  text = text.replace(/<ol[^>]*>/gi, "");
  text = text.replace(/<\/ol>/gi, "\n");
  text = text.replace(/<li[^>]*>(.*?)<\/li>/gi, "• $1\n");

  // 6. Blockquotes
  text = text.replace(/<blockquote[^>]*>(.*?)<\/blockquote>/gis, "$1\n");

  // 7. Horizontal rules
  text = text.replace(/<hr[^>]*\/?>/gi, "\n---\n");

  // 8. Line breaks and paragraphs
  text = text.replace(/<br[^>]*\/?>/gi, "\n");
  text = text.replace(/<p[^>]*>/gi, "");
  text = text.replace(/<\/p>/gi, "\n");

  // 9. Inline formatting → strip tags
  text = text.replace(/<strong[^>]*>(.*?)<\/strong>/gi, "$1");
  text = text.replace(/<b[^>]*>(.*?)<\/b>/gi, "$1");
  text = text.replace(/<em[^>]*>(.*?)<\/em>/gi, "$1");
  text = text.replace(/<i[^>]*>(.*?)<\/i>/gi, "$1");
  text = text.replace(/<code[^>]*>(.*?)<\/code>/gi, "$1");
  text = text.replace(/<[^>]+>/g, "");

  // 10. Decode common HTML entities
  text = text.replace(/&amp;/g, "&");
  text = text.replace(/&lt;/g, "<");
  text = text.replace(/&gt;/g, ">");
  text = text.replace(/&quot;/g, '"');
  text = text.replace(/&#039;/g, "'");
  text = text.replace(/&nbsp;/g, " ");

  // 11. Clean up whitespace
  text = text.replace(/\n{3,}/g, "\n\n").trim();

  return text;
}

/**
 * Copy the assistant message text to clipboard.
 * Shows transient "Copied!" feedback in the feedback bar.
 */
async function _aiCopyResponse(button) {
  const msgBody = button.closest(".ai-ws-msg-body");
  if (!msgBody) return;

  const contentEl = msgBody.querySelector(".ai-ws-msg-content");
  if (!contentEl) return;

  const plainText = _extractPlainTextFromHTML(contentEl.innerHTML);
  if (!plainText) return;

  const feedbackBar = button.closest(".ai-ws-feedback");
  const errorEl = feedbackBar ? feedbackBar.querySelector(".ai-ws-fb-error") : null;
  const originalTitle = button.getAttribute("title");

  try {
    await navigator.clipboard.writeText(plainText);
    button.setAttribute("title", _aiT("ai_ws_copy_ok", "Copied!"));
    button.classList.add("active");
    if (errorEl) {
      errorEl.textContent = _aiT("ai_ws_copy_ok", "Copied!");
      errorEl.hidden = false;
      errorEl.style.color = "var(--bs-success, #198754)";
    }
    setTimeout(() => {
      button.setAttribute("title", originalTitle);
      button.classList.remove("active");
      if (errorEl) {
        errorEl.hidden = true;
        errorEl.textContent = "";
        errorEl.style.color = "";
      }
    }, 1500);
  } catch {
    button.setAttribute("title", _aiT("ai_ws_copy_error", "Copy failed"));
    if (errorEl) {
      errorEl.textContent = _aiT("ai_ws_copy_error", "Copy failed");
      errorEl.hidden = false;
      errorEl.style.color = "var(--bs-danger, #dc3545)";
    }
    setTimeout(() => {
      button.setAttribute("title", originalTitle);
      if (errorEl) {
        errorEl.hidden = true;
        errorEl.textContent = "";
        errorEl.style.color = "";
      }
    }, 2000);
  }
}

// Delegate clicks on copy buttons within the messages container.
document.addEventListener("click", (event) => {
  const button = event.target.closest(".ai-ws-copy-btn");
  if (button) _aiCopyResponse(button);
});

window._extractPlainTextFromHTML = _extractPlainTextFromHTML;
window._aiCopyResponse = _aiCopyResponse;
