"""Shared helpers for the Commitments Calendar E2E module."""

import re

RAW_KEY = re.compile(r"commitments_[a-z_]+")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def eval_js(context, script):
    return context.page.evaluate(script)


def open_tab(context):
    context.page.evaluate(
        "if (typeof switchFinancialAdvisorTab === 'function') switchFinancialAdvisorTab('commitments-calendar');"
    )
    context.page.wait_for_selector("#commitments-toolbar", timeout=15000)
    context.page.wait_for_timeout(800)


def click(context, selector, wait=500):
    context.page.click(selector)
    context.page.wait_for_timeout(wait)


def blank_and_raw(context, scope_selectors):
    """Blank data-i18n nodes and raw translation keys visible inside the given scopes."""
    return context.page.evaluate(
        """(scopes) => {
          const blank = []; const raw = [];
          for (const sel of scopes) {
            const root = document.querySelector(sel);
            if (!root) { blank.push('missing ' + sel); continue; }
            root.querySelectorAll('[data-i18n]').forEach(el => {
              if (!el.textContent.trim()) blank.push(el.getAttribute('data-i18n'));
            });
            const m = root.innerText.match(/commitments_[a-z_]+/g);
            if (m) raw.push(...m);
          }
          return { blank, raw };
        }""",
        scope_selectors,
    )
