"""The push the loop gives a model that refuses, announces or returns nothing: it names only the tools that fit the request.

The tools are chosen from the request's shape, not from a fixed favourite: a written document that no computed data was handed
for is documentation of the app (screens, guide, files); a question with a hint or without a document is about the user's data.
A tool that is not offered in this chat domain is never named, and when none fits the nudge names no tool at all."""

from __future__ import annotations

APP_DOCUMENTATION = ("app_routes", "app_knowledge_search", "app_read_file")
USER_DATA = ("app_screen_data", "app_data_models", "app_data_query", "app_computed_figures", "app_knowledge_search")


def relevant_tools(names: set, *, document: bool, hinted: bool) -> list[str]:
    wanted = APP_DOCUMENTATION if document and not hinted else USER_DATA
    return [t for t in wanted if t in names]


def investigate_nudge(names: set, *, document: bool = False, hinted: bool = False) -> str:
    tools = relevant_tools(names, document=document, hinted=hinted)
    which = f" ({', '.join(tools)})" if tools else ""
    return ("You DO have full read access through your tools. Do not say you lack tools, data or access, and do not answer from memory. "
            f"Investigate now: call one of the tools you were given{which}, read the result, then answer from it.")
