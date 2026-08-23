import os

class DocNode:
    def __init__(self, node_id, title, purpose, navigation, steps, screenshot_path, is_admin=False):
        self.id = node_id
        self.title = title
        self.purpose = purpose
        self.navigation = navigation # List of strings e.g. ["Dashboard", "Balance"]
        self.screenshots = [] # list of paths
        if screenshot_path:
            self.screenshots.append(screenshot_path)
        self.steps = steps
        self.children = [] # List of DocNode
        self.hierarchical_number = ""
        self.siblings = []
        self.route = None
        self.is_admin = is_admin

class DocumentationModel:
    def __init__(self, manifest, content):
        self.manifest = manifest
        self.content = content
        self.nodes = []
        self.validation_warnings = []
        self._build_tree()
        
    def _auto_purpose(self, title, tab, nested_tab, modal, route_title):
        """
        Generates a readable, generic purpose sentence for pages/tabs/modals
        that have no hand-written entry in content/page_descriptions.json.
        This keeps generated docs readable for anything discovered
        automatically (new pages, tabs, or CRUD popups added to the app)
        without requiring a matching manual content entry for every one.
        """
        if modal:
            return f"Provides the '{title}' form/view within {route_title}."
        if nested_tab:
            return f"Shows the '{title}' view within {route_title}."
        if tab:
            return f"Covers the '{title}' section of {route_title}."
        return f"Overview of the {title} page."

    def _get_stable_key(self, page_entry):
        keys = [page_entry.get('route')]
        if page_entry.get('tab_id'):
            keys.append(page_entry.get('tab_id'))
        if page_entry.get('nested_tab_id'):
            keys.append(page_entry.get('nested_tab_id'))
        if page_entry.get('modal_id'):
            keys.append(page_entry.get('modal_id'))
        return "::".join(filter(None, keys))

    def _build_tree(self):
        pages = self.manifest.get("pages", [])
        
        # Sort by capture timestamp to preserve the order in which screenshots were taken
        pages.sort(key=lambda x: x.get("capture_timestamp", ""))
        
        routes_map = {}
        
        # Validation and mapping
        for s in pages:
            route = s.get('route')
            tab = s.get('tab_id')
            nested_tab = s.get('nested_tab_id')
            modal = s.get('modal_id')
            
            stable_key = self._get_stable_key(s)
            desc = self.content.get(stable_key) or self.content.get(route) or {}
            if not desc:
                self.validation_warnings.append(f"Missing page description for: {stable_key}")
                
            raw_title = s.get('page_title') or modal or nested_tab or tab or s.get('page_id') or route
            title = str(raw_title).replace('-', ' ').replace('_', ' ').title()
            route_title = str(route).replace('-', ' ').replace('_', ' ').title() if route else ""

            purpose = desc.get("purpose") or self._auto_purpose(title, tab, nested_tab, modal, route_title)
            steps = desc.get("steps", [])
            s_path = s.get('screenshot_path')
            if s_path:
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                s_path = os.path.join(base_dir, "docs", "screenshots", "latest", os.path.basename(s_path))
            
            navigation = []
            if route: navigation.append(route_title)
            
            if not tab and not nested_tab and not modal:
                if s.get('page_title'):
                    navigation[0] = str(s.get('page_title')).replace('-', ' ').replace('_', ' ').title()
            
            if tab: navigation.append(str(tab).replace('-', ' ').replace('_', ' ').title())
            if nested_tab: navigation.append(str(nested_tab).replace('-', ' ').replace('_', ' ').title())
            if modal: navigation.append(str(modal).replace('-', ' ').replace('_', ' ').title())
            
            is_admin = s.get('is_admin', False)
            node = DocNode(stable_key, title, purpose, navigation, steps, s_path, is_admin)
            node.route = route
            node.is_modal = bool(modal)
            
            if route not in routes_map:
                routes_map[route] = { 'node': DocNode(route, navigation[0], "", [navigation[0]], [], None, is_admin), 'tabs': {} }
                routes_map[route]['node'].route = route
                
            if not tab and not modal:
                routes_map[route]['node'].title = title
                routes_map[route]['node'].purpose = purpose
                routes_map[route]['node'].steps = steps
                routes_map[route]['node'].is_admin = is_admin
                if s_path:
                    routes_map[route]['node'].screenshots.append(s_path)
            elif tab and not nested_tab and not modal:
                if tab not in routes_map[route]['tabs']:
                    routes_map[route]['tabs'][tab] = { 'node': node, 'nested': [], 'modals': [] }
                else:
                    routes_map[route]['tabs'][tab]['node'] = node
            elif tab and nested_tab and not modal:
                if tab not in routes_map[route]['tabs']:
                    routes_map[route]['tabs'][tab] = { 'node': DocNode(tab, navigation[1], "", navigation[:2], [], None, is_admin), 'nested': [], 'modals': [] }
                routes_map[route]['tabs'][tab]['nested'].append({ 'node': node, 'id': nested_tab, 'modals': [] })
            elif modal:
                if tab and nested_tab:
                    if tab not in routes_map[route]['tabs']:
                        routes_map[route]['tabs'][tab] = { 'node': DocNode(tab, navigation[1], "", navigation[:2], [], None, is_admin), 'nested': [], 'modals': [] }
                    
                    target_nested = None
                    for item in reversed(routes_map[route]['tabs'][tab]['nested']):
                        if item['id'] == nested_tab:
                            target_nested = item
                            break
                            
                    if not target_nested:
                        target_nested = { 'node': DocNode(nested_tab, navigation[2], "", navigation[:3], [], None, is_admin), 'id': nested_tab, 'modals': [] }
                        routes_map[route]['tabs'][tab]['nested'].append(target_nested)
                        
                    target_nested['modals'].append(node)
                elif tab:
                    if tab not in routes_map[route]['tabs']:
                        routes_map[route]['tabs'][tab] = { 'node': DocNode(tab, navigation[1], "", navigation[:2], [], None, is_admin), 'nested': [], 'modals': [] }
                    routes_map[route]['tabs'][tab]['modals'].append(node)
                else:
                    routes_map[route]['node'].children.append(node)
                    
        for r_key, r_data in routes_map.items():
            r_node = r_data['node']
            for t_key, t_data in r_data['tabs'].items():
                t_node = t_data['node']
                for n_data in t_data['nested']:
                    n_node = n_data['node']
                    n_node.children.extend(n_data['modals'])
                    t_node.children.append(n_node)
                t_node.children.extend(t_data['modals'])
                r_node.children.append(t_node)
            self.nodes.append(r_node)
