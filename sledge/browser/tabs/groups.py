from PyQt6.QtGui import QColor

class TabGroup:
    def __init__(self, name, color=None, parent=None):
        self.name = name
        self.color = color or QColor(240, 240, 240)
        self.tabs = []
        self.keep_active = False
        self.collapsed = False
        self.parent = parent
        self.subgroups = {}  # Dictionary of child groups
        self.stored_data = None
        self.last_accessed = {}
        self._tab_count = 0  # Track number of tabs for representation

    def add_subgroup(self, name, color=None):
        """Add a nested subgroup"""
        subgroup = TabGroup(name, color, parent=self)
        self.subgroups[name] = subgroup
        return subgroup

    def get_full_path(self):
        """Get full group path (e.g., 'Research/Papers/ML')"""
        path = [self.name]
        current = self
        while current.parent:
            current = current.parent
            path.append(current.name)
        return '/'.join(reversed(path))
        
    def get_display_name(self):
        """Get the display name for the group including tab count"""
        count = len(self.tabs)
        return f">{self.name} ({count})" if count > 0 else self.name
        
    def add_tab(self, tab):
        """Add a tab to the group"""
        if tab not in self.tabs:
            self.tabs.append(tab)
            self._tab_count = len(self.tabs)
            
    def remove_tab(self, tab):
        """Remove a tab from the group"""
        if tab in self.tabs:
            self.tabs.remove(tab)
            self._tab_count = len(self.tabs)
            
    def update_representation(self):
        """Update the group's representation"""
        self._tab_count = len(self.tabs)
        return self.get_display_name() 