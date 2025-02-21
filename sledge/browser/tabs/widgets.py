from PyQt6.QtCore import Qt, QPoint, QEvent, QRect, QSize, QTimer, QPointF, QUrl, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QHBoxLayout, QVBoxLayout, 
    QToolButton, QMenu, QLabel, QPushButton, QDockWidget, QDialog, QDialogButtonBox, QLineEdit, QColorDialog, QComboBox, QStackedWidget, QTabBar, QListWidget, QListWidgetItem, QGridLayout, QInputDialog
)
from PyQt6.QtGui import QColor, QCursor, QIcon, QShortcut
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

from .states import TabState
from .groups import TabGroup
from .memory import TabMemoryManager, TabMemoryIndicator
from .ring_menu import RingMenu
from .dialogs import TabListDialog, TabSpreadDialog
from .debug import TabDebugPanel
import os
        
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
        
        # Initialize view pool for instant tab creation
        self.view_pool = []
        self._warm_pool_size = 3
        self._setup_view_pool()
        
        # Set up tab bar styling and behavior
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setDocumentMode(True)
        self.setMovable(True)
        self.setTabsClosable(True)
        
        # Create enhanced TabBar
        self._tab_bar = TabBar(self)
        self.setTabBar(self._tab_bar)
        
        # Set up modern styling
        self.setStyleSheet("""
            QTabWidget::pane { 
                border: none;
                background: #2e3440;
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
        """)
        
        # Initialize memory management
        self.memory_manager = TabMemoryManager(self)
        
        # Set up fast tab switching
        self._setup_shortcuts()
        
        # Initialize tab groups at the widget level
        self.tab_groups = {}  # Map of tab index to group name
        self.groups = {}      # Map of group name to group properties
        
        # Initialize state tracking first
        self.min_group_collapse_threshold = 2
        self.hibernated_tabs = {} 
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
        
        # Setup debug panel last
        QTimer.singleShot(0, self._setup_debug_panel)
        
        # Ensure widget is visible
        self.show()
        self.setMinimumSize(400, 300)  # Set minimum size to ensure visibility
        
        # Touch navigation setup
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.touch_start = None
        self.touch_time = None
        self.swipe_threshold = 100  # pixels
        self.current_tab_widget = None
        
        # Initialize both preview mechanisms
        self.preview_container = None
        self.setup_preview_dropdown()
        self.tab_spread = None  # Lazy load the spread dialog
        
        # Delay initialization of tabs until parent is ready
        QTimer.singleShot(100, self._initialize_tabs)
        
    def _initialize_tabs(self):
        """Initialize tabs after parent is ready"""
        if self.parent() and hasattr(self.parent(), 'add_new_tab'):
            # Create initial tab
            self.parent().add_new_tab()
            
            # Create test groups if in development mode
            if os.getenv('SLEDGE_DEV') == '1':
                QTimer.singleShot(500, self.create_test_tabs)
        
    def _setup_view_pool(self):
        """Pre-warm WebView pool for instant tab creation"""
        while len(self.view_pool) < self._warm_pool_size:
            view = QWebEngineView()
            view.hide()
            self.view_pool.append(view)
    
    def new_tab(self, url=None):
        """Create new tab using pre-warmed view"""
        if self.view_pool:
            view = self.view_pool.pop()
        else:
            view = QWebEngineView()
            
        if url:
            view.setUrl(QUrl(url))
        view.show()
        
        index = self.addTab(view, "New Tab")
        self.setCurrentIndex(index)
        
        # Replenish pool
        QTimer.singleShot(0, self._setup_view_pool)
        
        return view

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts for fast tab switching"""
        shortcuts = [
            (QKeySequence("Ctrl+Tab"), self.next_tab),
            (QKeySequence("Ctrl+Shift+Tab"), self.prev_tab),
            (QKeySequence("Ctrl+W"), self.close_current_tab),
            (QKeySequence("Ctrl+T"), self.new_tab)
        ]
        
        for key_seq, slot in shortcuts:
            QShortcut(key_seq, self, activated=slot)

    def _setup_corner_widget(self):
        """Setup the corner widget with control buttons"""
        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.setSpacing(2)

        # Add port button
        self.port_button = QToolButton(self)
        self.port_button.setText("⚡")  # Or "🔌" or "📡"
        self.port_button.setToolTip("Quick Port Switch")
        self.port_button.setFixedSize(24, 24)
        self.port_button.clicked.connect(self.show_port_dialog)
        self.port_button.setStyleSheet("""
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
        corner_layout.addWidget(self.port_button)

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
        """Show full tab spread dialog (touch-friendly)"""
        from .dialogs import TabSpreadDialog
        if not self.tab_spread:
            self.tab_spread = TabSpreadDialog(self)
        self.tab_spread.populate_spread()
        self.tab_spread.show()

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
        self.createGroup("Anime", QColor("#c678dd"))  # Purple
        
        # Add tabs one at a time
        def add_tab_to_group(url, group_name):
            """Create and add a tab to a group"""
            # Create the tab first
            if isinstance(url, str) and any(domain in url.lower() for domain in ['wcostream', 'wcofun', 'wco.tv']):
                # Create VideoTab for video URLs
                from ..components.video_tab import VideoTab
                tab = VideoTab(url, self)
                idx = self.addTab(tab, "Video")
            else:
                # Create regular WebEngineView tab
                web_view = QWebEngineView()
                web_view.setUrl(QUrl(url))
                idx = self.addTab(web_view, "New Tab")
            
            if isinstance(idx, int) and idx >= 0:  # Verify tab was added
                # Add to group and ensure it's tracked
                self.addTabToGroup(idx, group_name)
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
            "http://localhost:5173",  # Your dev server
            "https://github.com/your-dev-repo",
            "https://chat.openai.com"
        ]
        for url in dev_urls:
            add_tab_to_group(url, "Development")

        # Media tabs
        media_urls = [
            "https://reddit.com/r/programming",
            "https://news.ycombinator.com",
            "https://youtube.com"
        ]
        for url in media_urls:
            add_tab_to_group(url, "Media")

        # Anime tabs
        anime_urls = [
            "https://myanimelist.net/",
            "https://wcofun.net",
            "https://wcostream.net"
        ]
        for url in anime_urls:
            add_tab_to_group(url, "Anime")

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
        
        # Switch to the development group and expand it
        dev_tabs = [i for i in range(self.count()) 
                    if self.tab_groups.get(i) == "Development"]
        if dev_tabs:
            self.setCurrentIndex(dev_tabs[0])
            if "Development" in self.collapsed_groups:
                self._toggle_group("Development")

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

    def setup_preview_dropdown(self):
        """Setup the quick preview dropdown for keyboard/mouse navigation"""
        self.preview_container = QWidget(self)
        self.preview_container.setWindowFlags(Qt.WindowType.Popup)
        layout = QVBoxLayout(self.preview_container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Create preview list
        self.group_preview = QListWidget(self.preview_container)
        self.group_preview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.group_preview.setStyleSheet("""
            QListWidget {
                background: #2e3440;
                border: 1px solid #4c566a;
                border-radius: 4px;
                min-width: 200px;
                max-width: 400px;
            }
            QListWidget::item {
                color: #d8dee9;
                padding: 4px 8px;
                border-bottom: 1px solid #3b4252;
            }
            QListWidget::item:hover {
                background: #3b4252;
            }
            QListWidget::item:selected {
                background: #4c566a;
                color: #88c0d0;
            }
        """)
        self.group_preview.itemClicked.connect(self._handle_preview_click)
        layout.addWidget(self.group_preview)

    def _handle_preview_click(self, item):
        """Handle click on preview item"""
        tab_index = item.data(Qt.ItemDataRole.UserRole)
        self.setCurrentIndex(tab_index)
        self.preview_container.hide()

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

    def create_group(self, name, tabs):
        """Create a new tab group"""
        if name not in self.groups:
            self.groups[name] = {'color': '#88c0d0'}  # Default color
            
        # Add tabs to group
        for tab_index in tabs:
            self.tab_groups[tab_index] = name
            
        # Set first tab as representative
        if tabs:
            self.group_representatives[name] = tabs[0]
            
        # Update tab appearances
        for tab_index in tabs:
            self._tab_bar.update_tab_appearance(tab_index)

    def _show_delayed_preview(self):
        """Show preview after a short delay to prevent flicker"""
        if hasattr(self, 'current_hover'):
            index = self.current_hover.get('index', -1)
            group = self.current_hover.get('group')
            if index >= 0 and group:
                self._show_group_preview(index, group, use_spread=False)

    def close_tab(self, index):
        """Close the tab at the given index"""
        # Check if tab is in a group
        group = self.tab_groups.get(index)
        if group:
            # Update group if this was the representative
            if self.group_representatives.get(group) == index:
                # Find new representative
                for i in range(self.count()):
                    if i != index and self.tab_groups.get(i) == group:
                        self.group_representatives[group] = i
                        break
            # Remove from group
            del self.tab_groups[index]
            
        # Clean up memory management
        if hasattr(self, 'memory_manager'):
            self.memory_manager.remove_tab(index)
            
        # Remove the tab
        self.removeTab(index)
        
        # If this was the last tab, create a new one
        if self.count() == 0:
            self.parent().add_new_tab()

    def update_breadcrumbs(self):
        """Update the breadcrumb navigation in the status bar"""
        # Clear existing breadcrumbs safely
        while self.breadcrumb_layout.count():
            item = self.breadcrumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get current tab and group
        current_index = self.currentIndex()
        current_group = self.tab_groups.get(current_index)
        
        if not current_group or current_group not in self.groups:
            self.breadcrumb_container.hide()
            return
        
        self.breadcrumb_container.show()
        
        # Add group indicator
        group_color = self.groups[current_group].color
        group_label = QLabel(f" {current_group} ")
        group_label.setStyleSheet(f"""
            QLabel {{
                background: {group_color.name()};
                color: black;
                padding: 2px 6px;
                border-radius: 2px;
                font-weight: bold;
            }}
        """)
        self.breadcrumb_layout.addWidget(group_label)
        
        # Add separator
        separator = QLabel("▶")
        separator.setStyleSheet("color: #4c566a;")
        self.breadcrumb_layout.addWidget(separator)
        
        # Add tab title
        tab = self.widget(current_index)
        if hasattr(tab, 'page'):
            title = tab.page().title()
            if title:
                title_label = QLabel(title)
                title_label.setStyleSheet("""
                    QLabel {
                        color: #d8dee9;
                        padding: 2px 6px;
                    }
                """)
                self.breadcrumb_layout.addWidget(title_label)
        
        # Add stretch to push everything to the left
        self.breadcrumb_layout.addStretch()

    def _show_group_preview(self, index, group, use_spread=False):
        """Show group preview using appropriate mechanism"""
        if use_spread:
            # Use spread dialog for touch/mobile
            from .dialogs import TabSpreadDialog
            if not self.tab_spread:
                self.tab_spread = TabSpreadDialog(self)
            self.tab_spread.populate_spread(group_filter=group)
            self.tab_spread.show()
        else:
            # Use dropdown for keyboard/mouse
            if not self.preview_container:
                return
            
            # Get all tabs in this group
            group_tabs = []
            for i in range(self.count()):
                if self.tab_groups.get(i) == group:
                    group_tabs.append(i)
            
            if not group_tabs:
                return
            
            # Clear and populate preview list
            self.group_preview.clear()
            for tab_index in group_tabs:
                item = QListWidgetItem(self.tabText(tab_index))
                item.setData(Qt.ItemDataRole.UserRole, tab_index)
                self.group_preview.addItem(item)
            
            # Position and show preview
            tab_rect = self.tabBar().tabRect(index)
            global_pos = self.tabBar().mapToGlobal(tab_rect.bottomLeft())
            self.preview_container.move(global_pos)
            self.preview_container.show()
            self.preview_container.raise_()
            
            # Focus and preselect
            self.group_preview.setFocus()
            if self.group_preview.count() > 0:
                self.group_preview.setCurrentRow(0)
            
            # Connect enter key to navigation
            self.group_preview.itemActivated.connect(self._navigate_to_preview_tab)

    def _navigate_to_preview_tab(self, item):
        """Navigate to the selected tab from preview"""
        tab_index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(tab_index, int) and 0 <= tab_index < self.count():
            self.setCurrentIndex(tab_index)
            self.preview_container.hide()

    def handle_navigation(self, direction):
        """Handle browser navigation"""
        current_tab = self.currentWidget()
        if hasattr(current_tab, 'page'):
            if direction == 'back':
                current_tab.page().triggerAction(QWebEnginePage.WebAction.Back)
            elif direction == 'forward':
                current_tab.page().triggerAction(QWebEnginePage.WebAction.Forward)
            elif direction == 'reload':
                current_tab.page().triggerAction(QWebEnginePage.WebAction.Reload)

    def next_tab(self):
        """Switch to next tab"""
        current = self.currentIndex()
        if current < self.count() - 1:
            self.setCurrentIndex(current + 1)
        else:
            # Wrap around to first tab
            self.setCurrentIndex(0)
            
    def prev_tab(self):
        """Switch to previous tab"""
        current = self.currentIndex()
        if current > 0:
            self.setCurrentIndex(current - 1)
        else:
            # Wrap around to last tab
            self.setCurrentIndex(self.count() - 1)
            
    def close_current_tab(self):
        """Close the current tab"""
        current = self.currentIndex()
        if current >= 0:
            self.removeTab(current)

    def show_port_dialog(self):
        dialog = PortGridDialog(self)
        dialog.show()

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
        
        # Enable keyboard navigation
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
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
                                    # Use spread for touch
                                    tab_widget._show_group_preview(tab_index, group, use_spread=True)
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
                                tab_widget._show_group_preview(tab_index, group, use_spread=True)
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

    def update_tab_appearance(self, index):
        """Update tab appearance based on state"""
        if not hasattr(self.parent(), 'memory_manager'):
            return
            
        # Get tab state
        is_hibernated = index in getattr(self.parent().memory_manager, 'hibernated_tabs', {})
        is_active = self.currentIndex() == index
        
        # Set style based on state
        if is_hibernated:
            self.setTabTextColor(index, QColor("#666666"))  # Dimmed for hibernated tabs
        elif is_active:
            self.setTabTextColor(index, QColor("#88c0d0"))  # Bright for active tab
        else:
            self.setTabTextColor(index, QColor("#d8dee9"))  # Normal color

    def keyPressEvent(self, event):
        """Handle keyboard navigation"""
        if event.key() == Qt.Key.Key_Left:
            # Move to previous tab
            current = self.currentIndex()
            if current > 0:
                self.setCurrentIndex(current - 1)
            event.accept()
            return
            
        elif event.key() == Qt.Key.Key_Right:
            # Move to next tab
            current = self.currentIndex()
            if current < self.count() - 1:
                self.setCurrentIndex(current + 1)
            event.accept()
            return
            
        elif event.key() == Qt.Key.Key_Down:
            # Show group preview dropdown
            current = self.currentIndex()
            tab_widget = self.parent()
            if tab_widget and hasattr(tab_widget, 'tab_groups'):
                group = tab_widget.tab_groups.get(current)
                if group and current == tab_widget.group_representatives.get(group):
                    tab_widget._show_group_preview(current, group, use_spread=False)
            event.accept()
            return
            
        super().keyPressEvent(event)

class PortGridDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Ports")
        self.setModal(True)
        
        layout = QGridLayout(self)
        
        # Common development ports
        ports = [
            ("Django", 8000),
            ("React", 3000),
            ("Vue", 8080),
            ("Flask", 5000),
            ("Node", 3001),
            ("Webpack", 8081),
            ("Gleam", 8002),
            ("Custom", None)
        ]
        
        # Create grid of port buttons
        for i, (name, port) in enumerate(ports):
            row, col = divmod(i, 3)
            btn = QPushButton(f"{name}\n:{port}" if port else "Custom")
            btn.setMinimumWidth(100)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px;
                    background: #3b4252;
                    border: none;
                    border-radius: 4px;
                    color: #d8dee9;
                }
                QPushButton:hover {
                    background: #434c5e;
                }
            """)
            if port:
                btn.clicked.connect(lambda p=port: self.use_port(p))
            else:
                btn.clicked.connect(self.custom_port)
            layout.addWidget(btn, row, col)

    def use_port(self, port):
        current_url = self.parent().url_bar.text()
        try:
            # Parse current URL and update port
            url = QUrl(current_url)
            new_url = f"{url.scheme()}://{url.host()}:{port}{url.path()}"
            self.parent().url_bar.setText(new_url)
            self.parent().navigate_to_url()
        except Exception as e:
            print(f"Error updating port: {e}")
        self.close()
    
    def custom_port(self):
        port, ok = QInputDialog.getInt(
            self, "Custom Port", "Enter port number:", 
            min=1, max=65535
        )
        if ok:
            self.use_port(port)
