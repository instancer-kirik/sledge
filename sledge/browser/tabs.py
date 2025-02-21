from PyQt6.QtCore import Qt, QRect, QPoint, QSize, QTimer, pyqtSignal, QPointF, QRectF
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QTabWidget, QTabBar, QStylePainter, QStyleOptionTab, QStyle, QTreeWidget, QTreeWidgetItem,
    QMenu, QToolButton, QWidget, QHBoxLayout, QLabel, QDialog, QVBoxLayout, QLineEdit, QSplitter,
    QTreeWidgetItem, QPushButton, QDialogButtonBox, QColorDialog, QComboBox, QFileDialog,
    QScrollArea, QFrame, QGridLayout, QCheckBox
)
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QCursor
from datetime import datetime, timedelta
import psutil
import math
from PyQt6.QtWebEngineCore import QWebEnginePage
from typing import Optional
from .webview import WebView

class TabState:
    ACTIVE = "active"
    SNOOZED = "snoozed"
    HIBERNATED = "hibernated"
    FROZEN = "frozen"

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

class TabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_tab_width = 60
        self.max_tab_width = 150
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setElideMode(Qt.TextElideMode.ElideMiddle)
        self.setUsesScrollButtons(True)
        
        # Group management
        self.groups = {}  # Dictionary to store tab groups
        self.tab_groups = {}  # Maps tab index to group name
        self.group_representatives = {}  # Maps group name to shown tab index
        self.collapsed_groups = set()  # Groups that are showing only one tab
        self.min_group_collapse_threshold = 3  # Min tabs in group before collapsing
        self.active_group = None
        
        # Preview management
        self.hover_buffer = 20  # Pixels of buffer zone for hover detection
        self.group_preview = QWidget(self.parent())
        self.group_preview.setWindowFlags(Qt.WindowType.Popup)
        self.group_preview.setStyleSheet("""
            QWidget {
                background: #1b1b1b;
                border: 1px solid #3b3b3b;
            }
        """)
        self.group_preview.hide()
        
        # Timers for hover behavior
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.show_group_preview)
        
        self.hover_reset_timer = QTimer()
        self.hover_reset_timer.setSingleShot(True)
        self.hover_reset_timer.timeout.connect(self.reset_hover_state)
        
        # Scroll handling
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.handle_debounced_scroll)
        self.scroll_delta = 0
        self.scroll_threshold = 120
        
        # Collapse timer
        self.collapse_timer = QTimer()
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.timeout.connect(self.check_and_collapse_groups)
        
        # Force initial collapse
        QTimer.singleShot(0, self.force_initial_collapse)

        # Set up context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_tab_context_menu)

    def createGroup(self, name, color=None):
        """Create a new tab group and ensure it's collapsed if eligible"""
        self.groups[name] = TabGroup(name, color)
        
        # Immediately check if this group should be collapsed
        group_tabs = [i for i in range(self.count()) 
                     if self.tab_groups.get(i) == name]
        
        if len(group_tabs) >= self.min_group_collapse_threshold:
            self.collapsed_groups.add(name)
            self.group_representatives[name] = group_tabs[0]
            self.update_tab_sizes()
            self.update()
        
    def addTabToGroup(self, index, group_name):
        """Add a tab to a group and force collapse check"""
        if group_name in self.groups:
            self.tab_groups[index] = group_name
            self.groups[group_name].tabs.append(index)
            
            # Force immediate collapse check
            self.check_and_collapse_groups()
            
            # Reorder tabs to keep groups together
            self.reorganizeGroups()
            self.update_tab_sizes()
            self.update()

    def remove_from_group(self, index):
        """Remove a tab from its group"""
        if index in self.tab_groups:
            group_name = self.tab_groups[index]
            self.groups[group_name].tabs.remove(index)
            del self.tab_groups[index]
            self.check_and_collapse_groups()

    def reorganizeGroups(self):
        """Keep tabs in the same group together"""
        # Create a map of groups to their tabs
        group_tabs = {}
        ungrouped = []
        
        for i in range(self.count()):
            group = self.tab_groups.get(i)
            if group:
                if group not in group_tabs:
                    group_tabs[group] = []
                group_tabs[group].append(i)
            else:
                ungrouped.append(i)
        
        # Move tabs to keep groups together
        new_position = 0
        for group in group_tabs:
            for tab_index in group_tabs[group]:
                if tab_index != new_position:
                    self.moveTab(tab_index, new_position)
                new_position += 1
        
        # Move ungrouped tabs to the end
        for tab_index in ungrouped:
            if tab_index != new_position:
                self.moveTab(tab_index, new_position)
            new_position += 1

    def update_tab_sizes(self):
        """Update tab sizes and handle overflow"""
        if self.count() == 0:
            return
            
        available_width = self.width()
        
        # Calculate minimum width needed for all tabs
        min_width_needed = self.min_tab_width * self.count()
        
        # Get groups with enough tabs to collapse
        collapsible_groups = {}
        for i in range(self.count()):
            group = self.tab_groups.get(i)
            if group:
                if group not in collapsible_groups:
                    collapsible_groups[group] = []
                collapsible_groups[group].append(i)
        
        # Force collapse if we need to
        if min_width_needed > available_width:
            # Collapse all groups with 3+ tabs
            for group, indices in collapsible_groups.items():
                if len(indices) >= self.min_group_collapse_threshold:
                    self.collapsed_groups.add(group)
                    self.group_representatives[group] = indices[0]
        else:
            # Check if we can expand any groups
            self.expand_groups()
        
        # Calculate width for visible tabs
        visible_count = self.get_visible_tabs_count()
        if visible_count == 0:
            return
            
        # Use minimum width if we still can't fit
        if available_width / visible_count < self.min_tab_width:
            tab_width = self.min_tab_width
        else:
            # Otherwise distribute space evenly
            tab_width = min(self.max_tab_width, available_width / visible_count)
        
        self.setStyleSheet(f"""
            QTabBar::tab {{
                min-width: {int(tab_width)}px;
                max-width: {int(tab_width)}px;
                padding: 2px 4px;
                margin: 1px 1px;
            }}
        """)

    def get_visible_tabs_count(self):
        """Get count of visible tabs after collapse"""
        visible = 0
        seen_groups = set()
        
        for i in range(self.count()):
            group = self.tab_groups.get(i)
            if group in self.collapsed_groups:
                if group not in seen_groups:
                    visible += 1
                    seen_groups.add(group)
                else:
                visible += 1
                
        return visible

    def expand_groups(self):
        """Expand previously collapsed groups"""
        self.collapsed_groups.clear()
        self.group_representatives.clear()

    def force_initial_collapse(self):
        """Force collapse all groups on initial setup"""
        for group_name in list(self.groups.keys()):
            group_tabs = [i for i in range(self.count()) 
                         if self.tab_groups.get(i) == group_name]
            
            if len(group_tabs) >= self.min_group_collapse_threshold:
                self.collapsed_groups.add(group_name)
                current_index = self.currentIndex()
                if current_index in group_tabs:
                    self.group_representatives[group_name] = current_index
            else:
                    self.group_representatives[group_name] = group_tabs[0]
            
        self.update_tab_sizes()
                self.update()

    def check_and_collapse_groups(self):
        """Force collapse all eligible groups"""
        changed = False
        for group_name in list(self.groups.keys()):
            group_tabs = [i for i in range(self.count()) 
                         if self.tab_groups.get(i) == group_name]
            
            if len(group_tabs) >= self.min_group_collapse_threshold:
                if group_name not in self.collapsed_groups:
                    self.collapsed_groups.add(group_name)
                    current_index = self.currentIndex()
                    if current_index in group_tabs:
                        self.group_representatives[group_name] = current_index
            else:
                        self.group_representatives[group_name] = group_tabs[0]
                    changed = True
        
        if changed:
        self.update()

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self.check_and_handle_overflow()
        self.update_tab_sizes()

        # Schedule collapse check
        self.collapse_timer.start(100)  # Small delay to avoid too frequent updates

    def check_and_handle_overflow(self):
        """Check for tab overflow and auto-group if needed"""
        if self.count() > self.max_visible_tabs:
            ungrouped_tabs = []
            
            # Collect ungrouped tabs
            for i in range(self.count()):
                if i not in self.tab_groups:
                    ungrouped_tabs.append(i)
            
            if ungrouped_tabs:
                # Create overflow group if it doesn't exist
                if self.overflow_group_name not in self.groups:
                    self.createGroup(self.overflow_group_name, QColor(150, 150, 150))
                
                # Move tabs to overflow group
                for tab_index in ungrouped_tabs[:-self.max_visible_tabs]:
                    self.addTabToGroup(tab_index, self.overflow_group_name)
                
                self.reorganizeGroups()

    def suggest_group_for_url(self, url):
        """Suggest appropriate group for a URL"""
        url_str = url.toString()
        domain = url.host()
        
        # Check exact URL matches
        if url_str in self.link_groups:
            return self.link_groups[url_str]
        
        # Check domain patterns
        for pattern, group in self.domain_groups.items():
            if pattern in domain:
                return group
        
        # Auto-categorize based on URL patterns
        if any(term in url_str.lower() for term in ['docs', 'documentation', 'api']):
            return 'Reference'
        elif any(term in url_str.lower() for term in ['github', 'gitlab', 'bitbucket']):
            return 'Development'
        elif any(term in url_str.lower() for term in ['youtube', 'video', 'media']):
            return 'Media'
        
        return None

    def add_url_to_group(self, url, group_name):
        """Associate a URL with a group"""
        self.link_groups[url.toString()] = group_name
        
        # Optionally add domain pattern
        domain = url.host()
        if domain:
            self.domain_groups[domain] = group_name

    def wheelEvent(self, event):
        """Handle mouse wheel with debounce and group navigation"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Accumulate scroll delta
            self.scroll_delta += event.angleDelta().y()
            
            # Reset timer
            self.scroll_timer.start(150)  # 150ms debounce
        else:
            # Regular tab scrolling with group awareness
            delta = event.angleDelta().y()
            if abs(delta) >= self.scroll_threshold:
                if delta > 0:
                    self.scroll_to_previous_section()
                else:
                    self.scroll_to_next_section()
                event.accept()
                return
            
            super().wheelEvent(event)

    def enterEvent(self, event):
        """Handle mouse entering tab area"""
        super().enterEvent(event)
        # QEnterEvent in Qt6 uses position() instead of pos()
        self.update_hover_state(event.position().toPoint())

    def leaveEvent(self, event):
        """Handle mouse leaving tab area"""
        super().leaveEvent(event)
        self.hover_timer.stop()
        # Start reset timer when mouse leaves
        self.hover_reset_timer.start(300)  # 300ms delay before reset

    def mouseMoveEvent(self, event):
        """Handle mouse movement over tabs"""
        super().mouseMoveEvent(event)
        pos = event.pos()
        
        # Check if mouse is in buffer zone
        if pos.y() > self.height() - self.hover_buffer:
            # Mouse is in bottom buffer, keep preview open
            self.hover_reset_timer.stop()
            self.update_hover_state(pos)
        else:
            # Start reset timer if mouse moves away
            if self.group_preview.isVisible():
                self.hover_reset_timer.start(300)

    def update_hover_state(self, pos):
        """Update hover state and trigger preview if needed"""
        index = self.tabAt(pos)
        if index >= 0:
            group = self.tab_groups.get(index)
            if group in self.collapsed_groups:
                if group != self.active_group:
                    self.active_group = group
                    self.hover_timer.start(200)  # 200ms delay before showing
                    self.hover_reset_timer.stop()  # Cancel any pending reset
                return
        
        # Only start hover timer if we're not in preview or buffer zone
        if not self.group_preview.isVisible() or pos.y() <= self.height() - self.hover_buffer:
            self.hover_timer.stop()
            self.hover_reset_timer.start(300)

    def reset_hover_state(self):
        """Reset hover state and hide preview"""
        cursor_pos = self.mapFromGlobal(QCursor.pos())
        preview_rect = self.group_preview.geometry()
        preview_rect.adjust(-self.hover_buffer, -self.hover_buffer, 
                          self.hover_buffer, self.hover_buffer)
        
        # Only hide if mouse is outside buffer zones
        if not preview_rect.contains(cursor_pos) and cursor_pos.y() <= self.height() - self.hover_buffer:
            self.group_preview.hide()
            self.active_group = None

    def show_group_preview(self):
        """Show preview of group contents with improved appearance"""
        if not self.active_group or self.active_group not in self.collapsed_groups:
            return
            
        # Create or update preview widget
        if not hasattr(self.group_preview, 'layout'):
            layout = QVBoxLayout(self.group_preview)
            layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)
        else:
            layout = self.group_preview.layout()
        # Clear existing content
        while layout.count():
            layout.takeAt(0).widget().deleteLater()
            
        # Add group header
        header = QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background: {self.groups[self.active_group].color.darker(120).name()};
                border-radius: 2px;
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        
        # Add group label
        label = QLabel(f"Group: {self.active_group}")
        label.setStyleSheet("color: white; font-weight: bold;")
        header_layout.addWidget(label)
        
        # Add tab count
        count = sum(1 for i in range(self.count()) 
                   if self.tab_groups.get(i) == self.active_group)
        count_label = QLabel(f"({count} tabs)")
        count_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        header_layout.addWidget(count_label)
        
        header_layout.addStretch()
        layout.addWidget(header)
        
        # Add scrollable tab area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        
        tab_container = QWidget()
        tab_layout = QVBoxLayout(tab_container)
        tab_layout.setSpacing(1)
        tab_layout.setContentsMargins(1, 1, 1, 1)
        
        # Add tab buttons with improved appearance
        for i in range(self.count()):
            if self.tab_groups.get(i) == self.active_group:
                btn = QPushButton(self.tabText(i))
                btn.setFixedHeight(30)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(43, 43, 43, 0.8);
                        border: none;
                        color: white;
                        padding: 4px 12px;
                        text-align: left;
                        border-radius: 2px;
                    }
                    QPushButton:hover {
                        background: rgba(59, 59, 59, 0.9);
                    }
                    QPushButton:pressed {
                        background: rgba(70, 70, 70, 1.0);
                    }
                """)
                
                # Add click handler
                btn.clicked.connect(lambda x, idx=i: (
                    self.setCurrentIndex(idx),
                    self.group_preview.hide()
                ))
                
                tab_layout.addWidget(btn)
        
        tab_layout.addStretch()
        scroll.setWidget(tab_container)
        layout.addWidget(scroll)
        
        # Position preview below tab bar
        pos = self.mapToGlobal(QPoint(0, self.height()))
        self.group_preview.move(pos)
        
        # Set fixed size
        preview_width = min(self.width(), 300)  # Max width of 300px
        preview_height = min(count * 32 + 50, 300)  # Max height of 300px
        self.group_preview.setFixedSize(preview_width, preview_height)
        
        # Show and raise
        self.group_preview.show()
        self.group_preview.raise_()

class TabManager:
    def __init__(self, parent=None):
        self.tab_widget = QTabWidget(parent)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)  # More modern look
        
        # Fast tab switching shortcuts
        self.setup_shortcuts()
        
        # Pre-warm a pool of web views for instant tab creation
        self.view_pool = []
        self.warm_view_pool(size=3)
    
    def warm_view_pool(self, size: int):
        """Pre-create web views for instant tab opening"""
        for _ in range(size):
            view = WebView()
            view.hide()  # Keep hidden until needed
            self.view_pool.append(view)
    
    def new_tab(self, url: Optional[str] = None) -> WebView:
        """Create new tab instantly using pre-warmed view"""
        if self.view_pool:
            view = self.view_pool.pop()
        else:
            view = WebView()
            
        if url:
            view.load(url)
        view.show()
        
        index = self.tab_widget.addTab(view, "New Tab")
        self.tab_widget.setCurrentIndex(index)
        
        # Start warming new view for pool
        self.warm_view_pool(size=1)
        
        return view

# ... rest of the file ...


