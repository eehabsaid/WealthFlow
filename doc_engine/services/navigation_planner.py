import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

def sanitize_filename(name: str) -> str:
    """Converts string to lower_snake_case ASCII identifier."""
    if not name:
        return ""
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_')

def safe_filename(name: str, fallback_id: Optional[str] = None) -> str:
    """
    Sanitizes string to filename. If name contains non-ASCII characters (e.g., Arabic)
    that sanitize to empty string, falls back to fallback_id.
    """
    s = sanitize_filename(name)
    if s:
        return s
    clean_id = fallback_id or 'tab'
    clean_id = re.sub(r'[-_]tab$', '', clean_id, flags=re.IGNORECASE)
    return sanitize_filename(clean_id)


@dataclass
class CaptureContext:
    page_id: Optional[str] = None
    page_title: Optional[str] = None
    route: Optional[str] = None
    tab_id: Optional[str] = None
    tab_order: int = 0
    nested_tab_id: Optional[str] = None
    nested_tab_order: int = 0
    modal_id: Optional[str] = None
    modal_order: int = 0
    is_admin: bool = False


@dataclass
class PageItem:
    route: str
    title: str
    is_admin: bool = False
    custom_prefix: Optional[str] = None
    tabs: List[Dict[str, Any]] = field(default_factory=list)
    nested_navigation: List[Dict[str, Any]] = field(default_factory=list)


class NavigationPlanner:
    """
    Generates structured capture navigation plans from page inventory data.
    Decouples Playwright from how pages/tabs/modals are organized and named.
    """
    CHART_ROUTES = {'dashboard', 'financial-advisor', 'advanced-reports', 'reports'}

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def get_full_url(self, route: str) -> str:
        """Constructs full URL for a route."""
        if route.startswith('/'):
            return f"{self.base_url}{route}"
        return f"{self.base_url}/#{route}"

    def get_route_prefix(self, item: PageItem) -> str:
        """Generates filename prefix for a page item."""
        if item.custom_prefix:
            return item.custom_prefix
        r = item.route
        if r.startswith('/'):
            r = r.replace('/', '')
        return sanitize_filename(r) or sanitize_filename(item.title)

    def is_chart_route(self, route: str) -> bool:
        """Determines if a route contains heavy charts requiring render waits."""
        return route in self.CHART_ROUTES

    def get_navigation_tree(self, inventory: List[Dict[str, Any]]) -> List[PageItem]:
        """
        Public API exposing the normalized navigation tree for Playwright execution.
        Isolates inventory loading so future automatic discovery can replace manual inventory.
        """
        tree = []
        for raw in inventory:
            tree.append(PageItem(
                route=raw.get("route", ""),
                title=raw.get("title", ""),
                is_admin=raw.get("is_admin", False) is True,
                custom_prefix=raw.get("customPrefix"),
                tabs=raw.get("tabs", []),
                nested_navigation=raw.get("nested_navigation", [])
            ))
        return tree

