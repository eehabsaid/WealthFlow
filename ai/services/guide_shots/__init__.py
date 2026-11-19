"""Live screenshots for the AI-written user guide.

After the guide text is written, each screen (## chapter) and tab (### sub-section) gets a screenshot of the REAL app as the
asking user sees it. Captured with a headless Chromium logged in through a short-lived session of that user, stored per user
(runtime/guide_shots/<user id>/), and referenced from the guide as an ordinary Markdown image pointing at an owner-scoped URL, so
the chat, the HTML guide, Word and PDF all show them. Two sysadmin switches (Settings > AI Advisor): screenshots on/off and
blur amounts, e-mails and charts (default on). Everything here is best effort: no browser or a failed page means no image, never
a failed guide."""

from ai.services.guide_shots.apply import add_screenshots

__all__ = ["add_screenshots"]
