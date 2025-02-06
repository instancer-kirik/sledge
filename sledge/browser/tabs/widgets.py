from PyQt6.QtCore import Qt, QPoint, QEvent, QRect, QSize, QTimer, QPointF, QUrl, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QHBoxLayout, QVBoxLayout, 
    QToolButton, QMenu, QLabel, QPushButton, QDockWidget, QDialog, QDialogButtonBox, QLineEdit, QColorDialog, QComboBox, QStackedWidget, QTabBar
)
from PyQt6.QtGui import QColor, QCursor, QIcon, QShortcut
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile

from .states import TabState
from .groups import TabGroup
from .memory import TabMemoryManager, TabMemoryIndicator
from .ring_menu import RingMenu
from .dialogs import TabListDialog, TabSpreadDialog
from .debug import TabDebugPanel
        
        # # Set up tab bar styling and behavior first
        # self.setTabPosition(QTabWidget.TabPosition.North)
        # self.setDocumentMode(True)
        # self.setMovable(True)
        # self.setTabsClosable(True)
        
        # # Create and set our enhanced TabBar before any layouts
        # self._tab_bar = TabBar(self)
        # self.setTabBar(self._tab_bar)
        
        # # Initialize state tracking
        # self.tab_groups = {}  # Map of tab index to group name
        # self.groups = {}      # Map of group name to group properties
        # self.group_representatives = {}
        # self.collapsed_groups = set()
        # self.hibernated_tabs = {}  # {index: {url, title, icon, group}}
        # self.hibernation_pending = set()  # Tabs being hibernated
        # self.restoration_pending = set()  # Tabs being restored

class TabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize state tracking first
        self.groups = {}
        self.min_group_collapse_threshold = 2
        self.hibernated_tabs = {} 
        self.tab_groups = {}
        self.group_representatives = {}
        self.collapsed_groups = set()
        self.hibernation_pending = set()
        self.restoration_pending = set()
        
        # Initialize preview-related attributes
        self.group_preview = None
        self.preview_container = None
        self.current_hover = {'index': -1, 'group': None}
        self.selection_mode = False
        self.selection_cursor = -1
        
        # Set up preview timer
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(200)  # 200ms delay
        self.preview_timer.timeout.connect(self._show_delayed_preview)
        
        # Set up tab bar styling and behavior first
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setDocumentMode(True)
        self.setMovable(True)
        self.setTabsClosable(True)
        
        # Create and set our enhanced TabBar
        self._tab_bar = TabBar(self)
        self._tab_bar.setDrawBase(False)
        self._tab_bar.setExpanding(False)
        self._tab_bar.setMovable(True)
        self._tab_bar.setTabsClosable(True)
        self.setTabBar(self._tab_bar)
        
        # Set focus policy to handle keyboard navigation
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._tab_bar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Install event filter for keyboard navigation
        self._tab_bar.installEventFilter(self)
        self.installEventFilter(self)
        
        # Connect signals
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._handle_tab_change)
        
        # Create status bar at the bottom
        self.status_container = QWidget()
        self.status_container.setFixedHeight(28)
        self.status_layout = QHBoxLayout(self.status_container)
        self.status_layout.setContentsMargins(4, 0, 4, 0)
        self.status_layout.setSpacing(4)
        
        # Create breadcrumb section
        self.breadcrumb_container = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_container)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(4)
        
        # Create indicators section
        self.indicators_container = QWidget()
        self.indicators_layout = QHBoxLayout(self.indicators_container)
        self.indicators_layout.setContentsMargins(0, 0, 0, 0)
        self.indicators_layout.setSpacing(4)
        
        # Add sections to status layout
        self.status_layout.addWidget(self.breadcrumb_container, 1)
        self.status_layout.addWidget(self.indicators_container)
        
        # Set up stack widget
        self._stack = QStackedWidget()
        self.setCornerWidget(self._stack)
        
        # Initialize memory management
        try:
            self.memory_manager = TabMemoryManager(self)
            print("  initUI: Initialized memory management")
        except Exception as e:
            print(f"  initUI: Error in memory management: {e}")
            raise
        
        self._auto_manage = False
        self._memory_timer = None
        self._memory_limit = 1024 * 1024 * 1024  # 1GB
        
        # Set up styling
        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #2e3440;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background: #2e3440;
                color: #d8dee9;
                padding: 8px 20px;
                border: none;
                min-width: 150px;
                max-width: 300px;
            }
            QTabBar::tab:selected {
                background: #3b4252;
                color: #88c0d0;
            }
            QTabBar::tab:hover {
                background: #434c5e;
            }
        """)
        
        # Initialize UI components
        self._setup_corner_widget()
        self._setup_memory_indicator()
        self._setup_context_menu()
        self.setup_group_actions()
        
        # Setup debug panel last
        QTimer.singleShot(0, self._setup_debug_panel)
        
        # Ensure widget is visible
        self.show()
        self.setMinimumSize(400, 300)  # Set minimum size to ensure visibility
        
    def _setup_corner_widget(self):
        """Setup the corner widget with control buttons"""
        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.setSpacing(2)

        # Tab management buttons with improved styling
        self.tab_list_button = QToolButton(self)
        self.tab_list_button.setText("≣")
        self.tab_list_button.setToolTip("Show Tab List")
        self.tab_list_button.setFixedSize(24, 24)
        self.tab_list_button.clicked.connect(self.show_tab_list)
        self.tab_list_button.setStyleSheet("""
            QToolButton {
                background: #3b4252;
                border: none;
                border-radius: 3px;
                color: #d8dee9;
                font-size: 16px;
            }
            QToolButton:hover {
                background: #434c5e;
            }
        """)
        corner_layout.addWidget(self.tab_list_button)

        self.spread_button = QToolButton(self)
        self.spread_button.setText("⊞")
        self.spread_button.setToolTip("Show Tab Spread")
        self.spread_button.setFixedSize(24, 24)
        self.spread_button.clicked.connect(self.show_spread)
        self.spread_button.setStyleSheet("""
            QToolButton {
                background: #3b4252;
                border: none;
                border-radius: 3px;
                color: #d8dee9;
                font-size: 16px;
            }
            QToolButton:hover {
                background: #434c5e;
            }
        """)
        corner_layout.addWidget(self.spread_button)

        self.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)

    def _setup_memory_indicator(self):
        """Setup the memory usage indicator"""
        self.memory_indicator = TabMemoryIndicator(self)
        self.memory_indicator.setFixedHeight(24)
        self.indicators_layout.addWidget(self.memory_indicator)

    def _setup_context_menu(self):
        """Setup the context menu"""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_tab_context_menu)
    
    def _setup_debug_panel(self):
        """Set up the debug panel"""
        try:
            # Create dock widget for debug panel
            main_window = self.window()
            if not main_window or not hasattr(main_window, 'addDockWidget'):
                print("Debug panel requires a QMainWindow parent")
                return
                
            self.debug_dock = QDockWidget("Tab Debug Panel", main_window)
            self.debug_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable | 
                                      QDockWidget.DockWidgetFeature.DockWidgetMovable)
            
            # Create debug panel
            self.debug_panel = TabDebugPanel(self)
            self.debug_dock.setWidget(self.debug_panel)
            
            # Connect signals
            self.debug_panel.trigger_hibernation.connect(self._handle_debug_hibernation)
            self.debug_panel.trigger_restoration.connect(self._handle_debug_restoration)
            self.debug_panel.create_group.connect(self._handle_debug_group_creation)
            
            # Add to main window at bottom-left
            main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.debug_dock)
            
            # Create shortcut to toggle debug panel
            self.debug_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
            self.debug_shortcut.activated.connect(self._toggle_debug_panel)
            
            # Initial hide
            self.debug_dock.hide()
            
        except Exception as e:
            print(f"Error setting up debug panel: {e}")
            # Don't raise the error - allow tab widget to continue initializing
            pass
    
    def _toggle_debug_panel(self):
        """Toggle debug panel visibility"""
        if self.debug_dock.isVisible():
            self.debug_dock.hide()
        else:
            self.debug_dock.show()
            self.debug_panel.refresh_state()
    def _handle_tab_click(self, index):
        """Handle tab click event"""
        self.setCurrentIndex(index)
        self._tab_bar.setCurrentIndex(index)
        
    def _handle_tab_change(self, index):
        """Handle tab change event"""
        self._tab_bar.setCurrentIndex(index)
            
    def _handle_debug_hibernation(self, index):
        """Handle hibernation request from debug panel"""
        if 0 <= index < self.count():
            tab = self.widget(index)
            if hasattr(tab, 'url'):
                self.hibernated_tabs[index] = {
                    'url': tab.url().toString(),
                    'title': self.tabText(index),
                    'icon': self.tabIcon(index),
                    'group': self.tab_groups.get(index)
                }
                self.debug_panel.refresh_state()
    
    def _handle_debug_restoration(self, index):
        """Handle restoration request from debug panel"""
        if index in self.hibernated_tabs:
            self._restore_tab(index)
            self.debug_panel.refresh_state()
    
    def _handle_debug_group_creation(self, group_name, indices):
        """Handle group creation request from debug panel"""
        valid_indices = [i for i in indices if 0 <= i < self.count()]
        if valid_indices:
            # Create group if it doesn't exist
            if group_name not in self.groups:
                self.groups[group_name] = TabGroup(group_name)
            
            # Add tabs to group
            for index in valid_indices:
                self.tab_groups[index] = group_name
            
            # Set representative if needed
            if group_name not in self.group_representatives:
                self.group_representatives[group_name] = valid_indices[0]
            
            self._organize_tabs()
            self.debug_panel.refresh_state()
    
    def _restore_tab(self, index):
        """Restore a hibernated tab"""
        if index not in self.hibernated_tabs or index in self.restoration_pending:
            return
            
        try:
            self.restoration_pending.add(index)
            tab_data = self.hibernated_tabs[index]
            
            # Create new tab with stored data
            new_tab = self.widget(index)
            if hasattr(new_tab, 'load'):
                new_tab.load(QUrl(tab_data['url']))
            
            # Restore tab properties
            if tab_data.get('icon'):
                self.setTabIcon(index, tab_data['icon'])
            self.setTabText(index, tab_data['title'])
            
            # Restore group if needed
            if 'group' in tab_data:
                self.tab_groups[index] = tab_data['group']
            
            # Clean up hibernation state
            del self.hibernated_tabs[index]
            self.restoration_pending.remove(index)
            
            # Update debug panel if it exists
            if hasattr(self, 'debug_panel'):
                self.debug_panel.refresh_state()
            
        except Exception as e:
            print(f"Error restoring tab {index}: {e}")
            self.restoration_pending.remove(index)
            # Keep hibernation data in case we want to retry

    # Group management methods
    def createGroup(self, name, color=None):
        """Create a new tab group"""
        self.groups[name] = TabGroup(name, color)
        self.check_and_collapse_groups()

    def addTabToGroup(self, index, group_name):
        """Add a tab to a group with visual representation"""
        if group_name in self.groups:
            # Remove from any existing group first
            if index in self.tab_groups:
                old_group = self.tab_groups[index]
                if old_group in self.groups:
                    self.groups[old_group].tabs.remove(index)
            
            # Add to new group
            self.tab_groups[index] = group_name
            if index not in self.groups[group_name].tabs:
                self.groups[group_name].tabs.append(index)
                self.groups[group_name].tabs.sort()  # Keep tabs ordered
            
            # If this is the first tab in the group, make it the representative
            if len(self.groups[group_name].tabs) == 1:
                self.group_representatives[group_name] = index
            
            # Ensure group is initially collapsed if it meets the threshold
            if len(self.groups[group_name].tabs) >= self.min_group_collapse_threshold:
                self.collapsed_groups.add(group_name)
            
            # Update the group representative if needed
            if group_name in self.group_representatives:
                rep_tab = self.group_representatives[group_name]
                if not hasattr(self.widget(rep_tab), 'url'):
                    # Current representative is invalid, choose a new one
                    valid_tabs = [i for i in self.groups[group_name].tabs 
                                if hasattr(self.widget(i), 'url')]
                    if valid_tabs:
                        self.group_representatives[group_name] = valid_tabs[0]
            
            # Reorder tabs and update appearances
            self._organize_tabs()
            self.update_tab_appearances()

    def _create_group_header(self, group_name):
        """Create a visual header for a group"""
        header = QWidget(self)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # Group label with color indicator
        color = self.groups[group_name].color
        label = QLabel(f"  {group_name}")
        label.setStyleSheet(f"""
            QLabel {{
                background: {color.name()};
                color: black;
                padding: 2px 6px;
                border-radius: 2px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(label)

        # Collapse/expand button
        toggle_btn = QToolButton()
        toggle_btn.setText("▼" if group_name not in self.collapsed_groups else "▶")
        toggle_btn.clicked.connect(lambda: self._toggle_group(group_name))
        layout.addWidget(toggle_btn)

        layout.addStretch()
        return header

    def _organize_tabs(self, reorder=True):
        """Organize tabs by groups with improved behavior"""
        # Store current state
        current_index = self.currentIndex()
        current_group = self.tab_groups.get(current_index)
        
        # Update status container visibility first
        self.status_container.setVisible(bool(current_group and current_group in self.groups))
        
        # Update breadcrumb visibility first
        if current_group and current_group in self.groups:
            self.breadcrumb_container.show()
        else:
            self.breadcrumb_container.hide()
        
        # Collect tabs by group
        grouped_tabs = {}
        ungrouped = []
        
        for i in range(self.count()):
            group = self.tab_groups.get(i)
            if group:
                if group not in grouped_tabs:
                    grouped_tabs[group] = []
                grouped_tabs[group].append(i)
            else:
                ungrouped.append(i)

        # Track visible tabs for selection cursor
        visible_tabs = []
        
        if reorder:
            # First, hide all tabs
            for i in range(self.count()):
                self._tab_bar.setTabVisible(i, False)

            # Build new order
            new_order = []
            expanded_group = None
            
            # Find expanded group if any
            for group_name in grouped_tabs:
                if group_name not in self.collapsed_groups:
                    expanded_group = group_name
                    break
            
            if expanded_group:
                # Show expanded group's tabs
                group_tabs = sorted(grouped_tabs[expanded_group])
                new_order.extend(group_tabs)
                for tab_idx in group_tabs:
                    self._tab_bar.setTabVisible(tab_idx, True)
                    visible_tabs.append(tab_idx)
                
                # Ensure current tab stays visible if in this group
                if current_group == expanded_group:
                    if current_index not in visible_tabs:
                        visible_tabs.append(current_index)
                        self._tab_bar.setTabVisible(current_index, True)
            else:
                # Show group representatives and ungrouped tabs
                for group_name, tabs in grouped_tabs.items():
                    if not tabs:  # Skip empty groups
                        continue
                        
                    # Choose representative tab
                    rep_tab = self.group_representatives.get(group_name)
                    if rep_tab is None or rep_tab not in tabs:
                        # Prefer current tab as representative
                        if current_index in tabs:
                            rep_tab = current_index
                        else:
                            rep_tab = tabs[0]
                        self.group_representatives[group_name] = rep_tab
                    
                    # Only add representative if it's a valid tab
                    if rep_tab >= 0 and rep_tab < self.count():
                        new_order.append(rep_tab)
                        self._tab_bar.setTabVisible(rep_tab, True)
                        visible_tabs.append(rep_tab)
                
                # Add ungrouped tabs
                for tab_idx in ungrouped:
                    new_order.append(tab_idx)
                    self._tab_bar.setTabVisible(tab_idx, True)
                    visible_tabs.append(tab_idx)

            # Move tabs safely
            for i, target_idx in enumerate(new_order):
                current_idx = self._tab_bar.tabAt(self._tab_bar.tabRect(i).center())
                if current_idx != target_idx and current_idx >= 0:
                    self._tab_bar.moveTab(current_idx, i)
        
        # Update selection cursor
        if self.selection_cursor not in visible_tabs:
            self.selection_cursor = visible_tabs[0] if visible_tabs else 0
        
        # Ensure current tab stays visible and selected
        if current_index not in visible_tabs:
            if current_group and current_group in self.group_representatives:
                self.setCurrentIndex(self.group_representatives[current_group])
            elif visible_tabs:
                self.setCurrentIndex(visible_tabs[0])
        
        self.update_tab_appearances()

    def _toggle_group(self, group_name):
        """Toggle group collapse state with improved behavior"""
        if not group_name in self.groups:
            return
            
        current_index = self.currentIndex()
        current_group = self.tab_groups.get(current_index)
        
        if group_name in self.collapsed_groups:
            # Expanding this group - collapse others first
            for other_group in list(self.groups.keys()):
                if other_group != group_name:
                    self.collapsed_groups.add(other_group)
            
            # Expand this group
            self.collapsed_groups.remove(group_name)
            
            # Show first tab in group if current tab isn't in this group
            if current_group != group_name:
                group_tabs = sorted(self.groups[group_name].tabs)
                if group_tabs:
                    self.setCurrentIndex(group_tabs[0])
                    self.selection_cursor = group_tabs[0]
        else:
            # Collapsing this group
            self.collapsed_groups.add(group_name)
            
            # Ensure current tab becomes representative if it's in this group
            if current_group == group_name:
                self.group_representatives[group_name] = current_index
            
            # Update selection cursor
            if self.selection_cursor in self.groups[group_name].tabs:
                self.selection_cursor = self.group_representatives[group_name]
        
        self._organize_tabs()

    def remove_from_group(self, index):
        """Remove a tab from its group"""
        if index in self.tab_groups:
            group_name = self.tab_groups[index]
            self.groups[group_name].tabs.remove(index)
            del self.tab_groups[index]
            self.check_and_collapse_groups()

    # Collapse management methods
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
        
        self.update()

    # UI interaction methods
    def show_ring_menu(self):
        """Show ring menu around cursor"""
        cursor_pos = QCursor.pos()
        menu = RingMenu(self)
        self._populate_ring_menu(menu)
        menu.show_at(cursor_pos)

    def _populate_ring_menu(self, menu):
        """Populate the ring menu with actions"""
        current_index = self.currentIndex()
        if current_index >= 0:
            # Add common actions
            menu.add_action("Close", lambda: self.removeTab(current_index))
            menu.add_action("New Tab", self.parent().add_new_tab)
            menu.add_action("Duplicate", lambda: self.duplicate_tab(current_index))
            
            # Add group-related actions
            group = self.tab_groups.get(current_index)
            if group:
                menu.add_action(f"Leave {group}", 
                              lambda: self.remove_from_group(current_index))
            else:
                menu.add_action("Group With...", 
                              lambda: self.show_group_menu(current_index))
            
            # Add memory management actions
            state = self.memory_manager.states.get(current_index)
            if state == TabState.ACTIVE:
                menu.add_action("Snooze", 
                              lambda: self.memory_manager.snooze_tab(current_index))
            else:
                menu.add_action("Wake", 
                              lambda: self.memory_manager.wake_tab(current_index))

    def show_tab_list(self):
        """Show tab list dialog"""
        dialog = TabListDialog(self)
        dialog.exec()

    def show_spread(self):
        """Show tab spread view"""
        dialog = TabSpreadDialog(self)
        dialog.exec()

    def show_group_menu(self, index):
        """Show menu for moving tab to a group"""
        menu = QMenu(self)
        for group_name in self.groups:
            action = menu.addAction(group_name)
            action.triggered.connect(
                lambda checked, g=group_name: self.addTabToGroup(index, g)
            )
        menu.exec(QCursor.pos())

    def show_tab_context_menu(self, pos):
        """Show context menu for tab"""
        index = self._tab_bar.tabAt(pos)
        if index < 0:
            return
        
        menu = QMenu(self)
        
        # Basic actions
        menu.addAction("New Tab", self.parent().add_new_tab)
        menu.addAction("Duplicate", lambda: self.duplicate_tab(index))
        menu.addAction("Close", lambda: self.removeTab(index))
        
        # Group actions
        group = self.tab_groups.get(index)
        if group:
            menu.addAction(f"Leave {group}", 
                          lambda: self.remove_from_group(index))
        else:
            menu.addAction("Group With...", 
                          lambda: self.show_group_menu(index))
        
        # Memory actions
        state = self.memory_manager.states.get(index)
        if state == TabState.ACTIVE:
            menu.addAction("Snooze", 
                          lambda: self.memory_manager.snooze_tab(index))
        else:
            menu.addAction("Wake", 
                          lambda: self.memory_manager.wake_tab(index))
        
        menu.exec(self._tab_bar.mapToGlobal(pos))

    def duplicate_tab(self, index):
        """Duplicate a tab"""
        tab = self.widget(index)
        if hasattr(tab, 'url'):
            new_index = self.parent().add_new_tab(tab.url())
            # Copy group assignment if any
            group = self.tab_groups.get(index)
            if group:
                self.addTabToGroup(new_index, group)

    def create_test_tabs(self):
        """Create test tabs organized in groups"""
        # Create groups first with distinct colors
        self.createGroup("Research", QColor("#98c379"))  # Green
        self.createGroup("Development", QColor("#61afef"))  # Blue
        self.createGroup("Media", QColor("#e06c75"))  # Red
        
        # Add tabs one at a time and verify
        def add_tab_to_group(url, group_name):
            # Create the tab first
            idx = self.parent().add_new_tab(QUrl(url))
            if idx >= 0:  # Verify tab was added
                # Add to group and ensure it's tracked
                self.addTabToGroup(idx, group_name)
                # Make sure the URL is set in the URL bar
                tab = self.widget(idx)
                if hasattr(tab, 'url'):
                    self.parent().url_bar.setText(tab.url().toString())
                return True
            return False

        # Research tabs
        research_urls = [
            "https://arxiv.org/list/cs.AI/recent",
            "https://scholar.google.com",
            "https://paperswithcode.com"
        ]
        for url in research_urls:
            add_tab_to_group(url, "Research")

        # Development tabs
        dev_urls = [
            "https://docs.python.org/3/",
            "https://pyqt.sourceforge.io/Docs/PyQt6/",
            "https://github.com"
        ]
        for url in dev_urls:
            add_tab_to_group(url, "Development")

        # Media tabs
        media_urls = [
            "https://myanimelist.net/",
            "https://reddit.com/r/programming",
            "https://wcofun.net"
        ]
        for url in media_urls:
            add_tab_to_group(url, "Media")

        # Force initial collapse of all groups
        for group_name in self.groups:
            self.collapsed_groups.add(group_name)
            # Set first tab as representative if not set
            group_tabs = sorted(self.groups[group_name].tabs)
            if group_tabs and (group_name not in self.group_representatives or 
                             self.group_representatives[group_name] not in group_tabs):
                self.group_representatives[group_name] = group_tabs[0]

        # Organize tabs and update appearances
        self._organize_tabs()
        self.update_tab_appearances()

    def update_tab_appearances(self, index=None):
        """Update appearances of all tabs or a specific tab with improved indication"""
        styles = []
        
        # Base style for all tabs
        styles.append("""
            QTabBar::tab {
                background-color: #2e3440;
                color: #d8dee9;
                padding: 4px 8px;
                margin: 1px;
                border-radius: 3px;
                min-width: 150px;
                max-width: 300px;
            }
            QTabBar::tab:selected {
                background-color: #3b4252;
                color: #88c0d0;
                border-bottom: 2px solid #88c0d0;
            }
        """)
        
        tabs_to_update = [index] if index is not None else range(self.count())
        
        for i in tabs_to_update:
            if not self._tab_bar.isTabVisible(i):
                continue
                
            group = self.tab_groups.get(i)
            if group and group in self.groups:
                color = self.groups[group].color
                is_representative = (i == self.group_representatives.get(group))
                is_collapsed = group in self.collapsed_groups
                
                if is_representative:
                    # Show group name and count for representative
                    group_count = len(self.groups[group].tabs)
                    collapse_icon = "▼" if not is_collapsed else "►"
                    self.setTabText(i, f"{collapse_icon} {group} ({group_count})")
                    
                    styles.append(f"""
                        QTabBar::tab:nth-child({i + 1}) {{
                            background: qlineargradient(
                                x1:0, y1:0, x2:1, y2:0,
                                stop:0 {color.name()},
                                stop:1 {color.darker(110).name()}
                            );
                            color: black;
                            font-weight: bold;
                            border: none;
                            padding-left: 24px;
                            margin: 2px 4px;
                            border-radius: 5px;
                        }}
                    """)
                else:
                    # Keep original tab name for non-representatives
                    tab = self.widget(i)
                    if hasattr(tab, 'page'):
                        tab_name = tab.page().title()
                        if tab_name:
                            self.setTabText(i, tab_name)
                    
                    styles.append(f"""
                        QTabBar::tab:nth-child({i + 1}) {{
                            background-color: {color.darker(150).name()};
                            color: white;
                            border-left: 4px solid {color.name()};
                            padding: 4px 12px;
                            margin: 2px 2px 2px 16px;
                            border-radius: 0 3px 3px 0;
                        }}
                    """)
            
            # Selection cursor indicator
            if i == self.selection_cursor:
                styles.append(f"""
                    QTabBar::tab:nth-child({i + 1}) {{
                        border: 2px solid #ebcb8b !important;
                    }}
                """)
        
        # Update breadcrumbs
        self.update_breadcrumbs()
        
        # Apply styles
        self._tab_bar.setStyleSheet('\n'.join(styles))
        
        # Update tab text and indicators
        for i in tabs_to_update:
            if not self._tab_bar.isTabVisible(i):
                continue
                
            group = self.tab_groups.get(i)
            if group and group in self.groups:
                is_representative = (i == self.group_representatives.get(group))
                is_collapsed = group in self.collapsed_groups
                
                if is_representative:
                    # Update tab text with improved indicators
                    group_count = len(self.groups[group].tabs)
                    collapse_icon = "▼" if not is_collapsed else "►"
                    count_badge = f" ({group_count})" if is_collapsed else ""
                    self.setTabText(i, f"{collapse_icon} {group}{count_badge}")
                    
                    # Add tooltip with group info
                    tooltip = f"Group: {group}\nTabs: {group_count}\n"
                    if is_collapsed:
                        tooltip += "Click arrow to expand"
                    else:
                        tooltip += "Click arrow to collapse"
                    self._tab_bar.setTabToolTip(i, tooltip)

    # Alias for backward compatibility
    def update_tab_appearance(self, index):
        """Update appearance of a specific tab"""
        self.update_tab_appearances(index)

    def _is_first_in_group(self, index, group):
        """Check if tab is the first visible tab in its group"""
        for i in range(self.count()):
            if self.tab_groups.get(i) == group:
                if i == index:
                    return True
                if self._tab_bar.isTabVisible(i):
                    return False
        return False

    def find_tab(self, search_text):
        """Find tabs matching search text"""
        matches = []
        for i in range(self.count()):
            title = self.tabText(i)
            tab = self.widget(i)
            url = tab.url().toString() if hasattr(tab, 'url') else ""
            group = self.tab_groups.get(i, "")
            
            if (search_text.lower() in title.lower() or 
                search_text.lower() in url.lower()):
                matches.append({
                    'index': i,
                    'title': title,
                    'url': url,
                    'group': group,
                    'state': self.memory_manager.states.get(i, TabState.ACTIVE)
                })
        
        return matches

    def highlight_tab(self, index):
        """Temporarily highlight a tab to make it easy to find"""
        if not 0 <= index < self.count():
            return
            
        # Save original style
        original_style = self._tab_bar.tabTextColor(index)
        
        # Flash effect
        def flash(count=6):
            if count > 0:
                color = QColor("#ff9933") if count % 2 else original_style
                self._tab_bar.setTabTextColor(index, color)
                QTimer.singleShot(200, lambda: flash(count - 1))
            else:
                self.update_tab_appearances(index)
        
        flash()

    def _setup_group_preview(self):
        """Setup group preview overlay"""
        self.group_preview = QWidget(self)
        self.group_preview.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.group_preview.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.group_preview.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.group_preview.hide()
        
        # Create main layout
        layout = QVBoxLayout(self.group_preview)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create preview container with styling
        self.preview_container = QWidget()
        self.preview_container.setStyleSheet("""
            QWidget {
                background: #2e3440;
                border: 1px solid #434c5e;
                border-radius: 4px;
            }
            QWidget#tab_item {
                background: transparent;
                border: none;
                padding: 4px 8px;
                margin: 2px;
                border-radius: 3px;
            }
            QWidget#tab_item[selected="true"] {
                background: #5e81ac;
                border: 1px solid #88c0d0;
            }
            QWidget#tab_item:hover {
                background: #3b4252;
            }
            QLabel {
                color: #d8dee9;
            }
            QWidget#tab_item[selected="true"] QLabel {
                color: #eceff4;
                font-weight: bold;
            }
        """)
        container_layout = QVBoxLayout(self.preview_container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(2)
        
        # Add container to main layout
        layout.addWidget(self.preview_container)

    def _show_delayed_preview(self):
        """Show preview after delay"""
        index = self.current_hover['index']
        group = self.current_hover['group']
        
        if index < 0 or not group:
            if self.group_preview and not self._is_mouse_over_preview():
                self.group_preview.hide()
            return
        
        if not self.group_preview:
            self._setup_group_preview()
        
        # Clear existing preview items
        for i in reversed(range(self.preview_container.layout().count())): 
            widget = self.preview_container.layout().itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Get group tabs and check if it's a nested group
        group_tabs = [i for i in range(self.count()) if self.tab_groups.get(i) == group]
        group_obj = self.groups.get(group)
        has_subgroups = group_obj and group_obj.subgroups
        
        # Initialize selection cursor to first tab if not set
        if self.selection_cursor not in group_tabs:
            self.selection_cursor = group_tabs[0] if group_tabs else -1
        
        # Only add header if there are subgroups
        if has_subgroups:
            header = QPushButton(f"{group}")
            header.setStyleSheet(f"""
                QPushButton {{
                    background: {self.groups[group].color.name()};
                    color: black;
                    font-weight: bold;
                    border-radius: 2px;
                    margin: 2px;
                }}
            """)
            self.preview_container.layout().addWidget(header)
            
            # Add subgroup headers and their tabs
            for subgroup_name, subgroup in group_obj.subgroups.items():
                subheader = QPushButton(f"▸ {subgroup_name}")
                subheader.setStyleSheet(f"""
                    QPushButton {{
                        background: {subgroup.color.name()};
                        color: black;
                        font-weight: bold;
                        border-radius: 2px;
                        margin: 2px 2px 2px 12px;
                        font-size: 90%;
                    }}
                """)
                self.preview_container.layout().addWidget(subheader)
                
                # Add subgroup tabs
                for tab_index in subgroup.tabs:
                    if tab_index in group_tabs:
                        self._add_tab_button(tab_index, indent=24)
        else:
            # Just add the tabs without any headers
            for tab_index in group_tabs:
                self._add_tab_button(tab_index)
        
        # Position preview below the tab
        tab_rect = self._tab_bar.tabRect(index)
        global_pos = self._tab_bar.mapToGlobal(tab_rect.bottomLeft())
        
        # Adjust position to align with tab
        preview_x = global_pos.x()
        preview_y = global_pos.y() + 2  # Small offset to not overlap with tab
        
        # Ensure preview stays within screen bounds
        screen_rect = QApplication.primaryScreen().geometry()
        preview_width = self.group_preview.sizeHint().width()
        if preview_x + preview_width > screen_rect.right():
            preview_x = screen_rect.right() - preview_width
        
        self.group_preview.move(preview_x, preview_y)
        
        # Show preview with fade effect
        self.group_preview.show()
        self.group_preview.raise_()
        
        # Install event filter for keyboard navigation
        self.group_preview.installEventFilter(self)
        self.group_preview.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.group_preview.setFocus()

    def eventFilter(self, obj, event):
        """Handle keyboard events for tab navigation"""
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            
            # Handle keys when preview is visible
            if self.group_preview and self.group_preview.isVisible():
                if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                    # Get list of tabs in current group
                    current_group = self.current_hover['group']
                    if not current_group:
                        return False
                        
                    group_tabs = [i for i in range(self.count()) 
                                if self.tab_groups.get(i) == current_group]
                    if not group_tabs:
                        return False
                    
                    # Find current position
                    try:
                        current_pos = group_tabs.index(self.selection_cursor)
                    except ValueError:
                        current_pos = -1
                    
                    # Move selection up/down
                    if key == Qt.Key.Key_Up:
                        new_pos = (current_pos - 1) % len(group_tabs)
                    else:  # Key_Down
                        new_pos = (current_pos + 1) % len(group_tabs)
                    
                    # Update selection cursor and refresh preview
                    self.selection_cursor = group_tabs[new_pos]
                    self._show_delayed_preview()
                    event.accept()
                    return True
                    
                elif key == Qt.Key.Key_Return:
                    # Activate selected tab
                    if self.selection_cursor >= 0:
                        self.setCurrentIndex(self.selection_cursor)
                        self.group_preview.hide()
                    event.accept()
                    return True
                    
                elif key == Qt.Key.Key_Escape:
                    self.group_preview.hide()
                    event.accept()
                    return True
                    
                elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                    # Close preview and navigate in tab bar
                    self.group_preview.hide()
                    # Let the navigation be handled by the tab bar
                    return False
            
            # Handle keys when tab bar has focus
            if obj == self._tab_bar or obj == self:
                current_index = self.currentIndex()
                
                if key == Qt.Key.Key_Down:
                    # Show group preview for current tab
                    group = self.tab_groups.get(current_index)
                    if group:
                        self._show_group_preview(current_index, group)
                        event.accept()
                    return False  # Let the page handle scrolling if no group
                
                elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                    # Only handle left/right if tab bar has focus
                    if self._tab_bar.hasFocus() or self.hasFocus():
                        # Get list of visible tabs
                        visible_tabs = []
                        for i in range(self.count()):
                            if self._tab_bar.isTabVisible(i):
                                visible_tabs.append(i)
                        
                        if not visible_tabs:
                            return False
                        
                        # Find current position
                        try:
                            current_idx = visible_tabs.index(current_index)
                        except ValueError:
                            current_idx = 0
                        
                        # Move to adjacent tab
                        if key == Qt.Key.Key_Left:
                            new_idx = (current_idx - 1) % len(visible_tabs)
                        else:  # Key_Right
                            new_idx = (current_idx + 1) % len(visible_tabs)
                        
                        self.setCurrentIndex(visible_tabs[new_idx])
                        event.accept()
                        return True
                    
                    return False  # Let the page handle left/right if it has focus
        
        return super().eventFilter(obj, event)

    def focusInEvent(self, event):
        """Handle focus in event"""
        super().focusInEvent(event)
        # When tab widget gets focus, give it to the tab bar
        self._tab_bar.setFocus()

    def keyPressEvent(self, event):
        """Handle key press events"""
        # Forward all key events to the event filter
        if not self.eventFilter(self, event):
            super().keyPressEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leaving the widget"""
        super().leaveEvent(event)
        if self.group_preview and not self._is_mouse_over_preview():
            self.group_preview.hide()
            self.current_hover = {'index': -1, 'group': None}

    def _add_tab_button(self, tab_index, indent=8):
        """Add a tab button to the preview with optional indentation"""
        # Get the actual tab name, not the group representative label
        tab = self.widget(tab_index)
        is_hibernated = tab_index in self.hibernated_tabs
        
        # Create horizontal layout for icon and text
        container = QWidget()
        container.setObjectName("tab_item")
        container.setProperty("selected", str(tab_index == self.selection_cursor).lower())
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(indent, 2, 8, 2)
        layout.setSpacing(6)
        
        # Add icon
        icon_label = QLabel()
        icon_label.setFixedSize(16, 16)
        if is_hibernated:
            # Use hibernated tab's stored icon or default
            if self.hibernated_tabs[tab_index].get('icon'):
                icon_label.setPixmap(self.hibernated_tabs[tab_index]['icon'].pixmap(16, 16))
            else:
                icon_label.setPixmap(QIcon.fromTheme('text-html').pixmap(16, 16))
        elif hasattr(tab, 'icon') and not tab.icon().isNull():
            icon_label.setPixmap(tab.icon().pixmap(16, 16))
        else:
            icon_label.setPixmap(QIcon.fromTheme('text-html').pixmap(16, 16))
        layout.addWidget(icon_label)
        
        # Get the tab name
        if is_hibernated:
            tab_name = self.hibernated_tabs[tab_index].get('title', 'Hibernated Tab')
        elif hasattr(tab, 'page'):
            tab_name = tab.page().title()
            if not tab_name:  # Fallback if page title is empty
                url = tab.url().toString() if hasattr(tab, 'url') else ""
                tab_name = url.split('/')[-1] if url else self.tabText(tab_index)
        else:
            tab_name = self.tabText(tab_index)
        
        # Clean up the name if it's a group representative
        group = self.tab_groups.get(tab_index)
        if group and tab_index == self.group_representatives.get(group):
            # Strip any group-related formatting
            tab_name = tab_name.split(" [")[0]  # Remove count
            tab_name = tab_name.split(" (")[0]  # Remove count in parentheses
            tab_name = tab_name.replace("▼ ", "").replace("► ", "")  # Remove arrows
            tab_name = tab_name.replace(group, "").strip()  # Remove group name
            
            # If we stripped everything, try to get the original URL or title
            if not tab_name or tab_name == group:
                if is_hibernated:
                    url = self.hibernated_tabs[tab_index].get('url', '')
                    tab_name = url.split('/')[-1] if url else "Untitled"
                elif hasattr(tab, 'url'):
                    url = tab.url().toString()
                    tab_name = url.split('/')[-1] if url else "Untitled"
                else:
                    tab_name = "Untitled"
        
        # Add text label with hibernation indicator if needed
        text_label = QLabel(f"💤 {tab_name}" if is_hibernated else tab_name)
        text_label.setStyleSheet("""
            QLabel {
                color: #d8dee9;
                font-size: 12px;
            }
        """)
        layout.addWidget(text_label)
        
        # Make container clickable with improved handling
        def handle_click(e, i=tab_index):
            # First restore if hibernated
            if i in self.hibernated_tabs:
                self._restore_tab(i)
            
            # Full wake the tab
            if hasattr(self, 'memory_manager'):
                self.memory_manager.wake_tab(i)
                # Set keep_active flag to prevent auto-sleep
                group = self.tab_groups.get(i)
                if group and group in self.groups:
                    self.groups[group].keep_active = True
            
            # Switch to the tab
            self.setCurrentIndex(i)
            
            # Close any preview/switcher views
            if self.group_preview and self.group_preview.isVisible():
                self.group_preview.hide()
            
            # Close parent dialog if it exists (tab list or spread view)
            parent_dialog = self.window()
            if isinstance(parent_dialog, QDialog):
                parent_dialog.accept()
            
        container.mousePressEvent = handle_click
        container.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.preview_container.layout().addWidget(container)

    def _is_mouse_over_preview(self):
        """Check if mouse is over the preview popup"""
        if not self.group_preview or not self.group_preview.isVisible():
            return False
        
        mouse_pos = QCursor.pos()
        preview_rect = self.group_preview.geometry()
        tab_bar_rect = QRect(self._tab_bar.mapToGlobal(QPoint(0, 0)), self._tab_bar.size())
        
        return preview_rect.contains(mouse_pos) or tab_bar_rect.contains(mouse_pos)

    def _handle_tab_close(self, index):
        """Handle tab close requests"""
        if self.count() > 2:  # Keep at least one tab plus the new tab button
            self.removeTab(index)

    def _update_url_bar(self):
        """Update URL bar with current tab's URL"""
        tab = self.widget(self.currentIndex())
        if hasattr(tab, 'url'):
            self.parent().url_bar.setText(tab.url().toString())

    def update_breadcrumbs(self):
        """Update breadcrumb navigation"""
        # Clear existing breadcrumbs
        while self.breadcrumb_layout.count():
            item = self.breadcrumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        current = self.currentIndex()
        current_group = self.tab_groups.get(current)
        
        if current_group:
            # Add compact group indicator
            group_btn = QPushButton(self.breadcrumb_container)
            group_btn.setFixedHeight(24)
            group_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Set text based on group state
            is_collapsed = current_group in self.collapsed_groups
            btn_text = f"{'►' if is_collapsed else '▼'} {current_group}"
            group_btn.setText(btn_text)
            
            # Style the button with group color
            group_color = self.groups[current_group].color
            group_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {group_color.name()};
                    color: black;
                    font-weight: bold;
                    border: none;
                    border-radius: 3px;
                    padding: 2px 8px;
                    margin: 0;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {group_color.lighter(110).name()};
                }}
            """)
            
            group_btn.clicked.connect(lambda: self._toggle_group(current_group))
            self.breadcrumb_layout.addWidget(group_btn)
            
            # Add tab count in a more compact way
            count_label = QLabel(f"({len(self.groups[current_group].tabs)})", self.breadcrumb_container)
            count_label.setStyleSheet("""
                QLabel {
                    color: #d8dee9;
                    padding: 0 4px;
                    font-size: 11px;
                }
            """)
            self.breadcrumb_layout.addWidget(count_label)
        
        # Show/hide status container based on whether we have content
        self.status_container.setVisible(bool(current_group))

    def collapse_all_groups(self):
        """Collapse all groups immediately"""
        # Store current tab
        current_index = self.currentIndex()
        current_group = self.tab_groups.get(current_index)
        
        # Collapse all groups
        for group in list(self.groups.keys()):
            self.collapsed_groups.add(group)
        
        self._organize_tabs()
        
        # Restore current tab selection
        if current_group:
            self.setCurrentIndex(self.group_representatives[current_group])
        else:
            self.setCurrentIndex(current_index)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Close current tab
        close_tab = QShortcut(QKeySequence("Ctrl+W"), self)
        close_tab.activated.connect(self.close_current_tab)
        
        # Add shortcuts for group navigation
        next_in_group = QShortcut(QKeySequence("Alt+J"), self)
        next_in_group.activated.connect(self.next_tab_in_group)
        
        prev_in_group = QShortcut(QKeySequence("Alt+K"), self)
        prev_in_group.activated.connect(self.prev_tab_in_group)
        
        # Add shortcuts for group expansion
        expand_group = QShortcut(QKeySequence("Alt+Down"), self)
        expand_group.activated.connect(self.expand_current_group)
        
        collapse_group = QShortcut(QKeySequence("Alt+Up"), self)
        collapse_group.activated.connect(self.collapse_current_group)

    def close_current_tab(self):
        """Close the current tab"""
        current = self.currentIndex()
        if current >= 0:
            self.removeTab(current)

    def expand_current_group(self):
        """Expand the current tab's group"""
        current = self.currentIndex()
        group = self.tab_groups.get(current)
        if group and group in self.collapsed_groups:
            self.collapsed_groups.remove(group)
            self._organize_tabs()

    def collapse_current_group(self):
        """Collapse the current tab's group"""
        current = self.currentIndex()
        group = self.tab_groups.get(current)
        if group and group not in self.collapsed_groups:
            self.collapsed_groups.add(group)
            self._organize_tabs()

    def next_tab_in_group(self):
        """Switch to next tab in current group"""
        current = self.currentIndex()
        current_group = self.tab_groups.get(current)
        if not current_group:
            return
            
        group_tabs = [i for i in range(self.count()) 
                     if self.tab_groups.get(i) == current_group]
        if not group_tabs:
            return
            
        current_pos = group_tabs.index(current)
        next_tab = group_tabs[(current_pos + 1) % len(group_tabs)]
        self.setCurrentIndex(next_tab)

    def prev_tab_in_group(self):
        """Switch to previous tab in current group"""
        current = self.currentIndex()
        current_group = self.tab_groups.get(current)
        if not current_group:
            return
            
        group_tabs = [i for i in range(self.count()) 
                     if self.tab_groups.get(i) == current_group]
        if not group_tabs:
            return
            
        current_pos = group_tabs.index(current)
        prev_tab = group_tabs[(current_pos - 1) % len(group_tabs)]
        self.setCurrentIndex(prev_tab)

    def tabBarClicked(self, index):
        """Handle tab bar clicks with improved group behavior"""
        if not self._tab_bar.isTabVisible(index):
            return
            
        group = self.tab_groups.get(index)
        if group and index == self.group_representatives.get(group):
            # Show group preview for representative tab
            self._show_group_preview(index, group)
            return
        
        # Regular tab selection
        super().tabBarClicked(index)
        self.selection_cursor = index
        
        # Update URL bar
        tab = self.widget(index)
        if hasattr(tab, 'url'):
            self.parent().url_bar.setText(tab.url().toString())

    def setup_selection_shortcuts(self):
        """Setup keyboard shortcuts for tab selection"""
        # Ctrl+Tab to move forward
        next_tab = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab.activated.connect(lambda: self.move_selection_cursor(1))

    def move_selection_cursor(self, direction):
        """Move the selection cursor in the specified direction"""
        if self.count() > 1:
            self.selection_cursor = (self.selection_cursor + direction) % (self.count() - 1)
            self.setCurrentIndex(self.selection_cursor)
            self.update_tab_appearances()

    def activate_selected_tab(self):
        """Switch to the currently selected tab"""
        if self.selection_mode and self.selection_cursor is not None:
            old_index = self.currentIndex()
            self.setCurrentIndex(self.selection_cursor)
            # If we're activating a group representative, expand the group
            group = self.tab_groups.get(self.selection_cursor)
            if group and self.selection_cursor == self.group_representatives.get(group):
                if group in self.collapsed_groups:
                    self._toggle_group(group)
            self.exit_selection_mode()

    def exit_selection_mode(self):
        """Exit tab selection mode"""
        self.selection_mode = False
        self.selection_cursor = None
        self.update_tab_appearances()

    def close_tab(self, index):
        """Close the tab at the specified index"""
        self.removeTab(index)
        
    def removeTab(self, index):
        """Override removeTab to handle group representative tabs"""
        group = self.tab_groups.get(index)
        is_representative = group and index == self.group_representatives.get(group)
        
        if is_representative:
            # Find another tab from the same group to be the new representative
            group_tabs = [i for i in range(self.count()) 
                        if i != index and self.tab_groups.get(i) == group]
            if group_tabs:
                # Set new representative before removing the tab
                self.group_representatives[group] = group_tabs[0]
                super().removeTab(index)
                self._organize_tabs()
                return
            else:
                # Last tab in group - remove group
                del self.groups[group]
                if group in self.collapsed_groups:
                    self.collapsed_groups.remove(group)
                if group in self.group_representatives:
                    del self.group_representatives[group]
        
        super().removeTab(index)
        self._organize_tabs()

    def setCurrentIndex(self, index):
        """Override to handle hibernated tabs"""
        if index in self.hibernated_tabs:
            self._restore_tab(index)
        super().setCurrentIndex(index)

    def _show_group_preview(self, index, group):
        """Show group preview dropdown"""
        self.current_hover = {'index': index, 'group': group}
        self._show_delayed_preview()

    def _show_group_tabs(self, group_name):
        """Show a menu of all tabs in the group"""
        current_tab = self.currentIndex()
        menu = QMenu(self)
        
        # Get all tabs in this group
        group_tabs = [(i, self.tabText(i)) for i in range(self.count()) 
                     if self.tab_groups.get(i) == group_name]
        
        for tab_index, tab_title in group_tabs:
            action = menu.addAction(tab_title)
            action.setCheckable(True)
            action.setChecked(tab_index == current_tab)
            action.triggered.connect(lambda checked, idx=tab_index: self.setCurrentIndex(idx))
        
        # Show menu below current tab
        tab_rect = self._tab_bar.tabRect(current_tab)
        menu.popup(self._tab_bar.mapToGlobal(tab_rect.bottomLeft()))

    def show_tab_menu(self, tab_index, position):
        """Show context menu for the specified tab"""
        menu = QMenu(self)
        
        # Add basic tab actions
        close_action = menu.addAction("Close Tab")
        close_action.triggered.connect(lambda: self.close_tab(tab_index))
        
        duplicate_action = menu.addAction("Duplicate Tab")
        duplicate_action.triggered.connect(lambda: self.parent().add_new_tab(
            self.widget(tab_index).url() if hasattr(self.widget(tab_index), 'url') else None
        ))
        
        # Add group management submenu
        group_menu = menu.addMenu("Move to Group")
        
        # Add "Remove from Group" if tab is in a group
        if tab_index in self.tab_groups:
            remove_action = group_menu.addAction("Remove from Group")
            remove_action.triggered.connect(lambda: self.remove_from_group(tab_index))
            group_menu.addSeparator()
        
        # Add existing groups
        for group_name in self.groups:
            action = group_menu.addAction(group_name)
            action.triggered.connect(lambda checked, g=group_name: self.addTabToGroup(tab_index, g))
        
        # Add new group option
        group_menu.addSeparator()
        new_group_action = group_menu.addAction("New Group...")
        new_group_action.triggered.connect(lambda: self.create_new_group_for_tab(tab_index))
        
        # Add tab management actions
        menu.addSeparator()
        pin_action = menu.addAction("Pin Tab")
        pin_action.setCheckable(True)
        pin_action.setChecked(self._tab_bar.tabData(tab_index) == "pinned")
        pin_action.triggered.connect(lambda checked: self.toggle_pin_tab(tab_index, checked))
        
        # Show the menu at the specified position
        menu.popup(position)

    def duplicate_tab(self, index):
        """Duplicate the specified tab"""
        tab = self.widget(index)
        if hasattr(tab, 'url'):
            new_index = self.add_new_tab(tab.url())
            # Copy group assignment if any
            group = self.tab_groups.get(index)
            if group:
                self.addTabToGroup(new_index, group)

    def toggle_pin_tab(self, index, pinned):
        """Toggle pin state of a tab"""
        self._tab_bar.setTabData(index, "pinned" if pinned else None)
        if pinned:
            # Move to start of tab bar
            self._tab_bar.moveTab(index, 0)
        self.update_tab_appearances()

    def setup_group_actions(self):
        """Setup action buttons for group operations"""
        # Create buttons container
        self.action_container = QWidget()
        action_layout = QHBoxLayout(self.action_container)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(4)
        
        # Group navigation
        self.prev_group_btn = QPushButton("◀")
        self.prev_group_btn.setToolTip("Previous Group (Alt+Left)")
        self.prev_group_btn.clicked.connect(self.goto_prev_group)
        self.prev_group_btn.setFixedWidth(28)
        action_layout.addWidget(self.prev_group_btn)
        
        self.next_group_btn = QPushButton("▶")
        self.next_group_btn.setToolTip("Next Group (Alt+Right)")
        self.next_group_btn.clicked.connect(self.goto_next_group)
        self.next_group_btn.setFixedWidth(28)
        action_layout.addWidget(self.next_group_btn)
        
        # Group management
        self.group_menu_btn = QPushButton("Groups ▾")
        self.group_menu_btn.setToolTip("Group Operations")
        self.group_menu_btn.clicked.connect(self.show_group_menu)
        action_layout.addWidget(self.group_menu_btn)
        
        # Add separator
        separator = QLabel("|")
        separator.setStyleSheet("color: #4c566a;")
        action_layout.addWidget(separator)
        
        # Sleep management
        self.sleep_menu_btn = QPushButton("Sleep ▾")
        self.sleep_menu_btn.setToolTip("Sleep Management")
        self.sleep_menu_btn.clicked.connect(self.show_sleep_menu)
        action_layout.addWidget(self.sleep_menu_btn)
        
        # Quick actions
        self.quick_wake_btn = QPushButton("Quick Wake")
        self.quick_wake_btn.setToolTip("Light wake - tab will sleep again when inactive")
        self.quick_wake_btn.clicked.connect(self.quick_wake_current)
        action_layout.addWidget(self.quick_wake_btn)
        
        self.full_wake_btn = QPushButton("Full Wake")
        self.full_wake_btn.setToolTip("Full wake - tab stays active")
        self.full_wake_btn.clicked.connect(self.full_wake_current)
        action_layout.addWidget(self.full_wake_btn)
        
        # Add buttons container to indicators
        self.indicators_layout.addWidget(self.action_container)
        
        # Set up shortcuts
        self.setup_group_shortcuts()

    def setup_group_shortcuts(self):
        """Setup keyboard shortcuts for group navigation"""
        prev_group = QShortcut(QKeySequence("Alt+Left"), self)
        prev_group.activated.connect(self.goto_prev_group)
        
        next_group = QShortcut(QKeySequence("Alt+Right"), self)
        next_group.activated.connect(self.goto_next_group)

    def goto_prev_group(self):
        """Go to previous group"""
        current_index = self.currentIndex()
        current_group = self.tab_groups.get(current_index)
        if not current_group:
            return
            
        # Get list of groups
        groups = list(self.groups.keys())
        if not groups:
            return
            
        # Find current group index
        try:
            current_idx = groups.index(current_group)
            # Get previous group
            prev_group = groups[(current_idx - 1) % len(groups)]
            # Switch to first tab in that group
            group_tabs = [i for i in range(self.count()) 
                         if self.tab_groups.get(i) == prev_group]
            if group_tabs:
                self.setCurrentIndex(group_tabs[0])
                if prev_group in self.collapsed_groups:
                    self._toggle_group(prev_group)
        except ValueError:
            pass

    def goto_next_group(self):
        """Go to next group"""
        current_index = self.currentIndex()
        current_group = self.tab_groups.get(current_index)
        if not current_group:
            return
            
        # Get list of groups
        groups = list(self.groups.keys())
        if not groups:
            return
            
        # Find current group index
        try:
            current_idx = groups.index(current_group)
            # Get next group
            next_group = groups[(current_idx + 1) % len(groups)]
            # Switch to first tab in that group
            group_tabs = [i for i in range(self.count()) 
                         if self.tab_groups.get(i) == next_group]
            if group_tabs:
                self.setCurrentIndex(group_tabs[0])
                if next_group in self.collapsed_groups:
                    self._toggle_group(next_group)
        except ValueError:
            pass

    def show_sleep_menu(self):
        """Show sleep management menu"""
        menu = QMenu(self)
        current_index = self.currentIndex()
        
        # Quick actions for current tab
        quick_wake = menu.addAction("Quick Wake Current Tab")
        quick_wake.triggered.connect(self.quick_wake_current)
        
        full_wake = menu.addAction("Full Wake Current Tab")
        full_wake.triggered.connect(self.full_wake_current)
        
        menu.addSeparator()
        
        # Group sleep management
        if current_group := self.tab_groups.get(current_index):
            wake_group = menu.addAction(f"Wake All in '{current_group}'")
            wake_group.triggered.connect(lambda: self.wake_group(current_group))
            
            sleep_group = menu.addAction(f"Sleep All in '{current_group}'")
            sleep_group.triggered.connect(lambda: self.sleep_group(current_group))
        
        menu.addSeparator()
        
        # Global actions
        wake_all = menu.addAction("Wake All Tabs")
        wake_all.triggered.connect(self.wake_all_tabs)
        
        optimize = menu.addAction("Optimize Memory Usage")
        optimize.triggered.connect(self.memory_manager.optimize_memory_usage)
        
        menu.exec(self.sleep_menu_btn.mapToGlobal(
            QPoint(0, self.sleep_menu_btn.height())))

    def quick_wake_current(self):
        """Light wake of current tab - will sleep again when inactive"""
        current_index = self.currentIndex()
        if current_index >= 0:
            tab = self.widget(current_index)
            if hasattr(tab, 'page'):
                self.memory_manager.wake_tab(current_index)
                # Don't update keep_active flag so it can sleep again

    def full_wake_current(self):
        """Full wake of current tab - stays active"""
        current_index = self.currentIndex()
        if current_index >= 0:
            tab = self.widget(current_index)
            if hasattr(tab, 'page'):
                self.memory_manager.wake_tab(current_index)
                # Set keep_active flag to prevent auto-sleep
                group = self.tab_groups.get(current_index)
                if group:
                    self.groups[group].keep_active = True

    def wake_group(self, group_name):
        """Wake all tabs in a group"""
        for i in range(self.count()):
            if self.tab_groups.get(i) == group_name:
                self.memory_manager.wake_tab(i)
        self.groups[group_name].keep_active = True

    def sleep_group(self, group_name):
        """Put all tabs in a group to sleep"""
        self.groups[group_name].keep_active = False
        for i in range(self.count()):
            if self.tab_groups.get(i) == group_name:
                self.memory_manager.snooze_tab(i)

    def wake_all_tabs(self):
        """Wake all tabs"""
        for i in range(self.count()):
            self.memory_manager.wake_tab(i)

class TabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setExpanding(False)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setDocumentMode(True)
        self.setDrawBase(False)
        
        # Enable touch events
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        
        # Track touch state
        self.touch_start = None
        self.touch_tab_index = -1
        self.long_press_timer = QTimer(self)
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.setInterval(500)  # 500ms for long press
        self.long_press_timer.timeout.connect(self._handle_long_press)
        
        # Track drag state
        self.drag_active = False
        self.drag_threshold = 20  # pixels
        
        self.setStyleSheet("""
            QTabBar::tab {
                min-width: 150px;
                max-width: 250px;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                background: #2e3440;
                color: #d8dee9;
            }
            QTabBar::tab:selected {
                background: #3b4252;
                color: #88c0d0;
            }
            QTabBar::tab:hover:!selected {
                background: #434c5e;
            }
            QTabBar::close-button {
                image: url(close.png);
                subcontrol-position: right;
                margin: 2px;
                padding: 4px;  /* Larger touch target */
            }
            QTabBar::close-button:hover {
                background: #bf616a;
                border-radius: 4px;
                padding: 6px;  /* Even larger when hovering */
            }
        """)
    
    def event(self, event):
        """Handle touch events"""
        if event.type() == QEvent.Type.TouchBegin:
            # Get the first touch point
            touch_point = event.points()[0]
            self.touch_start = touch_point.position()
            # Find which tab was touched
            self.touch_tab_index = self.tabAt(self.touch_start.toPoint())
            if self.touch_tab_index >= 0:
                self.long_press_timer.start()
                self.drag_active = False
            return True
            
        elif event.type() == QEvent.Type.TouchEnd:
            if self.touch_start is not None:
                touch_point = event.points()[0]
                touch_end = touch_point.position()
                
                # Calculate movement
                delta = touch_end - self.touch_start
                
                if not self.drag_active:
                    tab_index = self.tabAt(touch_end.toPoint())
                    if tab_index == self.touch_tab_index:  # Same tab as touch start
                        if self.long_press_timer.isActive():  # Quick tap
                            self.long_press_timer.stop()
                            # Check if this is a group representative tab
                            tab_widget = self.parent()
                            if tab_widget and hasattr(tab_widget, 'tab_groups'):
                                group = tab_widget.tab_groups.get(tab_index)
                                if group and tab_index == tab_widget.group_representatives.get(group):
                                    # Show group preview
                                    tab_widget._show_group_preview(tab_index, group)
                                else:
                                    # Regular tab switch
                                    tab_widget.setCurrentIndex(tab_index)
                
                self.touch_start = None
                self.touch_tab_index = -1
                self.drag_active = False
            return True
            
        elif event.type() == QEvent.Type.TouchUpdate:
            if self.touch_start is not None:
                touch_point = event.points()[0]
                current_pos = touch_point.position()
                delta = current_pos - self.touch_start
                
                # Check for drag activation
                if not self.drag_active and delta.manhattanLength() > self.drag_threshold:
                    self.drag_active = True
                    self.long_press_timer.stop()
                
                # Handle drag for group preview
                if self.drag_active:
                    tab_widget = self.parent()
                    if tab_widget and hasattr(tab_widget, 'tab_groups'):
                        tab_index = self.tabAt(current_pos.toPoint())
                        if tab_index >= 0:
                            group = tab_widget.tab_groups.get(tab_index)
                            if group:
                                tab_widget._show_group_preview(tab_index, group)
            return True
            
        return super().event(event)
    
    def _handle_long_press(self):
        """Handle long press on tab"""
        if self.touch_tab_index >= 0:
            # Show context menu at tab position
            tab_rect = self.tabRect(self.touch_tab_index)
            menu_pos = self.mapToGlobal(tab_rect.bottomLeft())
            tab_widget = self.parent()
            if tab_widget and hasattr(tab_widget, 'show_tab_menu'):
                tab_widget.show_tab_menu(self.touch_tab_index, menu_pos)
            
        self.touch_start = None
        self.touch_tab_index = -1
