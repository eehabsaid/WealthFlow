"""Page script that hides what is private before a screenshot: every number (amounts, balances, dates), e-mail addresses,
field values and charts are blurred. Labels, menus and layout stay readable, so the image still teaches the screen."""

BLUR_JS = r"""() => {
  const css = 'filter: blur(6px) !important; user-select: none;';
  const num = /(\d[\d.,\s]*\d|\d)/g, mail = /[\w.+-]+@[\w-]+\.[\w.]+/g;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const parent = node.parentElement, text = node.nodeValue;
    if (!parent || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(parent.tagName) || parent.closest('[data-wf-blur]')) continue;
    if (!/\d|@/.test(text)) continue;
    const frag = document.createDocumentFragment();
    let last = 0;
    const hits = [];
    for (const re of [mail, num]) for (const m of text.matchAll(re)) hits.push([m.index, m.index + m[0].length]);
    hits.sort((a, b) => a[0] - b[0]);
    for (const [from, to] of hits) {
      if (from < last) continue;
      frag.append(text.slice(last, from));
      const span = document.createElement('span');
      span.setAttribute('data-wf-blur', '1');
      span.style.cssText = css;
      span.textContent = text.slice(from, to);
      frag.append(span);
      last = to;
    }
    frag.append(text.slice(last));
    parent.replaceChild(frag, node);
  }
  for (const el of document.querySelectorAll('input, textarea, select, canvas, .apexcharts-canvas, svg.chart, .chart-container'))
    el.style.cssText += css;
}"""
