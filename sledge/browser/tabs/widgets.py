from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QHBoxLayout, QVBoxLayout, 
    QToolButton, QMenu, QLabel, QPushButton, QDockWidget,
    QDialog, QDialogButtonBox, QLineEdit, QColorDialog,
    QComboBox, QStackedWidget, QTabBar, QListWidget, 
    QListWidgetItem, QGridLayout, QInputDialog, QStatusBar,
    QFrame
)
from PyQt6.QtGui import QColor, QCursor, QIcon, QShortcut
from PyQt6.QtCore import (
    Qt, QUrl, QTimer, QPoint, QSize, QEvent,
    QPropertyAnimation, QRect, pyqtSignal
)
from datetime import datetime
from .debug import TabDebugPanel
from .groups import TabGroup
from .states import TabState
from .memory import TabMemoryManager
import os

from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

from .ring_menu import RingMenu
from .dialogs import TabListDialog, TabSpreadDialog
from .memory import TabMemoryIndicator

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
        
        # Set up tab bar
        self._tab_bar = TabBar(self)
        self.setTabBar(self._tab_bar)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        
        # Initialize memory management
        self.memory_manager = TabMemoryManager(self)
        
        # Set up fast tab switching
        self.setTabBarAutoHide(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        
        # Initialize tab groups
        self.tab_groups = {}  # Maps tab index to group name
        self.groups = {}  # Maps group name to Group object
        self.group_representatives = {}  # Maps group name to representative tab index
        
        # Initialize hibernation tracking
        self.hibernated_tabs = set()
        self.frozen_tabs = set()
        self.hibernation_pending = set()  # Tabs pending hibernation
        self.restoration_pending = set()  # Tabs pending restoration
        self.collapsed_groups = set()
        
        # Initialize selection mode variables
        self.selection_mode = False
        self.selection_cursor = -1
        self.current_hover = {'index': -1, 'group': None}
        
        # Set up preview container
        self.setup_preview_container()

        # Set up the preview dropdown/group preview mechanism
        self.setup_preview_dropdown()
        
        # Set up status bar
        self.status_bar = QStatusBar(self)
        self.status_bar.setSizeGripEnabled(False)

        # Create the main container for status indicators
        self.status_container = QWidget() 
        self.indicators_layout = QHBoxLayout(self.status_container)
        self.indicators_layout.setContentsMargins(0, 0, 0, 0)
        self.indicators_layout.setSpacing(5)

        # Add status_container to the status_bar as a permanent widget
        self.status_bar.addPermanentWidget(self.status_container)
        self.status_container.hide() # Initially hidden; managed by _organize_tabs

        # Set up breadcrumbs (now part of status_container)
        self.breadcrumb_container = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_container)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.indicators_layout.addWidget(self.breadcrumb_container)
        self.breadcrumb_container.hide() # Initially hidden; managed by update_breadcrumbs/_organize_tabs

        # Initialize and call setup methods that populate indicators_layout
        self._setup_memory_indicator()
        self.setup_group_actions()
        
        # Connect signals
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._on_current_changed)
        
        # Initialize first tab if none exist
        QTimer.singleShot(0, self._initialize_tabs)
        
    def setup_preview_container(self):
        """Set up the preview container for tab groups"""
        self.preview_container = QWidget(self, Qt.WindowType.Popup)
        self.preview_container.setWindowFlags(
            Qt.WindowType.Popup | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.NoDropShadowWindowHint
        )
        
        # Create layout
        layout = QVBoxLayout(self.preview_container)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        
        # Create preview list
        self.preview_list = QListWidget()
        self.preview_list.setFrameShape(QFrame.Shape.NoFrame)
        self.preview_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.preview_list.setMaximumHeight(300)
        self.preview_list.itemClicked.connect(self._navigate_to_preview_tab)
        
        # Style the preview
        self.preview_container.setStyleSheet("""
            QWidget {
                background: #2e3440;
                border: 1px solid #4c566a;
                border-radius: 4px;
            }
            QListWidget {
                background: transparent;
                border: none;
            }
            QListWidget::item {
                color: #d8dee9;
                padding: 8px;
                border: none;
            }
            QListWidget::item:hover {
                background: #3b4252;
            }
            QListWidget::item:selected {
                background: #4c566a;
                color: #88c0d0;
            }
        """)
        
        layout.addWidget(self.preview_list)
        
    def _on_current_changed(self, index):
        """Handle tab change"""
        if index >= 0:
            # Update last accessed time
            self.memory_manager.last_accessed[index] = datetime.now()
            
            # Update tab title
            self.update_tab_title(index)
            
            # Update breadcrumbs
            self.update_breadcrumbs()
            
            # Update tab appearances
            self.update_tab_appearances()
            
            # Handle hibernated tabs
            if index in self.hibernated_tabs:
                # Start restoration process
                self.restoration_pending.add(index)
                self._restore_tab(index)
                
            # Update preview if needed
            if hasattr(self, 'preview_timer'):
                self.preview_timer.stop()
            self.preview_timer = QTimer()
            self.preview_timer.setSingleShot(True)
            self.preview_timer.timeout.connect(self._show_preview)
            self.preview_timer.start(200)  # Show preview after 200ms delay
        
    def _initialize_tabs(self):
        """Initialize tabs if none exist"""
        if self.count() == 0:
            self.new_tab()
            
    def new_tab(self, url=None, title=None, switch_to=True):
        """Create a new tab with optional URL and title"""
        # Create web view
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtCore import QUrl
        
        view = QWebEngineView()
        
        # Add to tab widget
        index = self.addTab(view, title or "New Tab")
        
        # Set up view
        if url:
            view.setUrl(QUrl(url))
            
        # Switch to new tab if requested
        if switch_to:
            self.setCurrentIndex(index)
            
        return index
        
    def new_video_tab(self, url, title=None, switch_to=True):
        """Create a new video tab with specialized video player"""
        try:
            from sledge.browser.components.video_tab import VideoTab
            
            # Create video tab
            video_tab = VideoTab(url, self)
            
            # Add to tab widget
            index = self.addTab(video_tab, title or "Video")
            
            # Switch to new tab if requested
            if switch_to:
                self.setCurrentIndex(index)
                
            return index
        except ImportError:
            # Fall back to regular tab if VideoTab is not available
            print("VideoTab component not available, falling back to regular tab")
            return self.new_tab(url, title, switch_to)
        
    def close_tab(self, index):
        """Close the tab at the given index"""
        if self.count() <= 1:
            # Don't close last tab, create new one instead
            self.new_tab()
            return
            
        # Update group representative if needed
        group = self.tab_groups.get(index)
        if group and index == self.group_representatives.get(group):
            # Find new representative
            for tab_idx, tab_group in self.tab_groups.items():
                if tab_idx != index and tab_group == group:
                    self.group_representatives[group] = tab_idx
                    break
                    
        # Clean up memory management
        self.memory_manager.remove_tab(index)
        
        # Remove tab
        self.removeTab(index)
        
        # Update indices
        self._update_tab_indices(index)
        
        # If this was the last tab, create a new one
        if self.count() == 0:
            self.parent().add_new_tab()
            
        # Update group appearances
        self.update_tab_appearances()

    def _update_tab_indices(self, removed_index):
        """Update tab indices after removing a tab"""
        # Update tab groups
        new_tab_groups = {}
        for idx, group in self.tab_groups.items():
            if idx < removed_index:
                new_tab_groups[idx] = group
            elif idx > removed_index:
                new_tab_groups[idx - 1] = group
        self.tab_groups = new_tab_groups
        
        # Update group representatives
        for group, rep_idx in self.group_representatives.items():
            if rep_idx > removed_index:
                self.group_representatives[group] = rep_idx - 1
                
        # Update hibernated and frozen sets
        self.hibernated_tabs = {idx if idx < removed_index else idx - 1 
                              for idx in self.hibernated_tabs 
                              if idx != removed_index}
        self.frozen_tabs = {idx if idx < removed_index else idx - 1 
                           for idx in self.frozen_tabs 
                           if idx != removed_index}

    def _setup_view_pool(self):
        """Pre-warm WebView pool for instant tab creation"""
        while len(self.view_pool) < self._warm_pool_size:
            view = QWebEngineView()
            view.hide()
            self.view_pool.append(view)
    
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
        """Set up the context menu"""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_tab_context_menu)
        
        # Create template menu
        self.template_menu = QMenu()
        self.setup_template_actions()
        
    def setup_template_actions(self):
        """Set up template tab actions"""
        # Marketplace template
        marketplace = self.template_menu.addAction("Open Marketplace Sites")
        marketplace.triggered.connect(self.open_marketplace_template)
        
        # News template
        news = self.template_menu.addAction("Open News Sites")
        news.triggered.connect(self.open_news_template)
        
        # Social template
        social = self.template_menu.addAction("Open Social Sites")
        social.triggered.connect(self.open_social_template)
        
    def open_marketplace_template(self):
        """Open a set of marketplace tabs in a new group"""
        # Create marketplace group
        group = self.createGroup("Marketplace", QColor("#88c0d0"))
        
        # Define marketplace sites with categories
        sites = {
            "General Marketplaces": [
                ("Craigslist", "https://craigslist.org"),
                ("Facebook Marketplace", "https://www.facebook.com/marketplace"),
                ("eBay", "https://www.ebay.com"),
           
                ("Etsy", "https://www.etsy.com"),
                ("OfferUp", "https://offerup.com"),
                ("Mercari", "https://www.mercari.com")
            ],
            "Local & Community": [
                ("Nextdoor", "https://nextdoor.com"),
                ("Letgo", "https://www.letgo.com"),
                ("VarageSale", "https://www.varagesale.com"),
                ("Freecycle", "https://www.freecycle.org"),
                ("Kijiji (Canada)", "https://www.kijiji.ca")
            ],
            "Specialty": [
                ("Poshmark", "https://poshmark.com"),
                ("ThredUp", "https://www.thredup.com"),
                ("Depop", "https://www.depop.com"),
                ("Newegg", "https://www.newegg.com"),
                ("Wayfair", "https://www.wayfair.com"),
                ("Reverb", "https://reverb.com"),
                ("StockX", "https://stockx.com")
            ],
           
        }
        
        # Create subgroups and tabs
        for category, category_sites in sites.items():
            # Create subgroup for category
            subgroup = group.add_subgroup(category, QColor("#88c0d0").lighter(110))
            
            # Create tabs for each site in category
            for title, url in category_sites:
                index = self.new_tab(url=url, title=title)
                self.addTabToGroup(index, category)
            
        # Force initial collapse
        self.check_and_collapse_groups()
        
    def open_news_template(self):
        """Open a set of news tabs in a new group"""
        # Create news group
        group = self.createGroup("News", QColor("#81a1c1"))
        
        # Define news sites
        sites = [
            ("Reuters", "https://www.reuters.com"),
            ("Associated Press", "https://apnews.com"),
            ("BBC", "https://www.bbc.com/news"),
            ("NPR", "https://www.npr.org"),
            ("The Guardian", "https://www.theguardian.com"),
            ("Al Jazeera", "https://www.aljazeera.com"),
            ("Bloomberg", "https://www.bloomberg.com"),
            ("Financial Times", "https://www.ft.com")
        ]
        
        # Create tabs for each site
        for title, url in sites:
            index = self.new_tab(url=url, title=title)
            self.addTabToGroup(index, "News")
            
        # Force initial collapse
        self.check_and_collapse_groups()
        
    def open_social_template(self):
        """Open a set of social media tabs in a new group"""
        # Create social group
        group = self.createGroup("Social", QColor("#b48ead"))
        
        # Define social sites
        sites = [
            ("Twitter", "https://twitter.com"),
            ("LinkedIn", "https://www.linkedin.com"),
            ("Reddit", "https://www.reddit.com"),
            ("Instagram", "https://www.instagram.com"),
            ("YouTube", "https://www.youtube.com"),
            ("Discord", "https://discord.com/app"),
            ("Mastodon", "https://mastodon.social"),
            ("Telegram", "https://web.telegram.org")
        ]
        
        # Create tabs for each site
        for title, url in sites:
            index = self.new_tab(url=url, title=title)
            self.addTabToGroup(index, "Social")
            
        # Force initial collapse
        self.check_and_collapse_groups()
        
    def show_tab_context_menu(self, pos):
        """Show the tab context menu"""
        menu = QMenu(self)
        
        # Add template submenu
        menu.addMenu(self.template_menu)
        menu.addSeparator()
        
        # Add standard actions
        new_tab = menu.addAction("New Tab")
        new_tab.triggered.connect(lambda: self.new_tab())
        
        close_tab = menu.addAction("Close Tab")
        close_tab.triggered.connect(lambda: self.close_tab(self.currentIndex()))
        
        duplicate_tab = menu.addAction("Duplicate Tab")
        duplicate_tab.triggered.connect(lambda: self.duplicate_tab(self.currentIndex()))
        
        # Add group submenu
        group_menu = menu.addMenu("Add to Group")
        for group_name in self.groups:
            action = group_menu.addAction(group_name)
            action.triggered.connect(
                lambda checked, g=group_name: self.addTabToGroup(self.currentIndex(), g)
            )
            
        # Add memory management submenu
        memory_menu = menu.addMenu("Memory")
        
        hibernate = memory_menu.addAction("Hibernate Tab")
        hibernate.triggered.connect(
            lambda: self.memory_manager.hibernate_tab(self.currentIndex())
        )
        
        wake = memory_menu.addAction("Wake Tab")
        wake.triggered.connect(
            lambda: self.memory_manager.wake_tab(self.currentIndex())
        )
        
        menu.exec(self.mapToGlobal(pos))

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
                self.hibernated_tabs.add(index)
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
        if index not in self.hibernated_tabs:
            return
            
        # Get the tab
        tab = self.widget(index)
        if not hasattr(tab, 'url'):
            return
            
        # Get the URL
        url = tab.url().toString()
        
        # Create a new web view
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtCore import QUrl
        
        view = QWebEngineView()
        
        # Load the URL
        view.setUrl(QUrl(url))
        
        # Replace the tab
        self.removeTab(index)
        self.insertTab(index, view, self.tabText(index))
        
        # Update state
        self.hibernated_tabs.remove(index)
        self.restoration_pending.remove(index)
        
        # Switch to the tab
        self.setCurrentIndex(index)

    # Group management methods
    def createGroup(self, name, color=None):
        """Create a new tab group"""
        if name not in self.groups:
            self.groups[name] = TabGroup(name, color)
        return self.groups[name]

    def addTabToGroup(self, index, group_name):
        """Add a tab to a group"""
        # Create group if it doesn't exist
        if group_name not in self.groups:
            self.createGroup(group_name)
            
        # Add tab to group
        self.tab_groups[index] = group_name
        self.groups[group_name].add_tab(index)
        
        # Set as representative if first tab
        if group_name not in self.group_representatives:
            self.group_representatives[group_name] = index
            
        # Update appearance
        if hasattr(self, '_tab_bar'):
            self._tab_bar.update_tab_appearance(index)
            
        # Update breadcrumbs
        self.update_breadcrumbs()
        
        # Check for group collapse
        self.check_and_collapse_groups()

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
        """Check and collapse groups that meet the threshold"""
        for group_name, group in self.groups.items():
            tabs_in_group = [i for i, g in self.tab_groups.items() if g == group_name]
            if len(tabs_in_group) >= 2:  # Minimum threshold for collapse
                # Keep representative visible
                rep_index = self.group_representatives.get(group_name)
                if rep_index is not None:
                    for tab_index in tabs_in_group:
                        if tab_index != rep_index:
                            self.setTabVisible(tab_index, False)
                            
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
        """Show the tab context menu"""
        menu = QMenu(self)
        
        # Add template submenu
        menu.addMenu(self.template_menu)
        menu.addSeparator()
        
        # Add standard actions
        new_tab = menu.addAction("New Tab")
        new_tab.triggered.connect(lambda: self.new_tab())
        
        close_tab = menu.addAction("Close Tab")
        close_tab.triggered.connect(lambda: self.close_tab(self.currentIndex()))
        
        duplicate_tab = menu.addAction("Duplicate Tab")
        duplicate_tab.triggered.connect(lambda: self.duplicate_tab(self.currentIndex()))
        
        # Add group submenu
        group_menu = menu.addMenu("Add to Group")
        for group_name in self.groups:
            action = group_menu.addAction(group_name)
            action.triggered.connect(
                lambda checked, g=group_name: self.addTabToGroup(self.currentIndex(), g)
            )
            
        # Add memory management submenu
        memory_menu = menu.addMenu("Memory")
        
        hibernate = memory_menu.addAction("Hibernate Tab")
        hibernate.triggered.connect(
            lambda: self.memory_manager.hibernate_tab(self.currentIndex())
        )
        
        wake = memory_menu.addAction("Wake Tab")
        wake.triggered.connect(
            lambda: self.memory_manager.wake_tab(self.currentIndex())
        )
        
        menu.exec(self.mapToGlobal(pos))

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
        """Update the appearance of all tabs or a specific tab"""
        if index is not None:
            # Update just one tab
            if hasattr(self, '_tab_bar'):
                self._tab_bar.update_tab_appearance(index)
            return
            
        # Update all tabs
        for i in range(self.count()):
            # Skip if tab bar not initialized
            if not hasattr(self, '_tab_bar'):
                continue
                
            # Update tab appearance based on state
            self._tab_bar.update_tab_appearance(i)
            
            # Handle selection mode highlighting
            if hasattr(self, 'selection_mode') and self.selection_mode:
                if hasattr(self, 'selection_cursor') and i == self.selection_cursor:
                    # Highlight the current selection cursor
                    self._tab_bar.setTabTextColor(i, QColor("#88c0d0"))
                else:
                    # Reset other tabs
                    self._tab_bar.setTabTextColor(i, QColor("#d8dee9"))

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
            
        # Store title and URL for history
        tab = self.widget(index)
        title = self.tabText(index)
        url = tab.url().toString() if hasattr(tab, 'url') else None
        
        # Remove the tab
        self.removeTab(index)
        
        # Update tab indices in groups and memory manager
        self._update_tab_indices(index)
        
        # If this was the last tab, create a new one
        if self.count() == 0:
            self.parent().add_new_tab()
            
        # Update group appearances
        self.update_tab_appearances()

    def _update_tab_indices(self, removed_index):
        """Update tab indices after a tab is removed"""
        # Update group mappings
        new_tab_groups = {}
        for idx, group in self.tab_groups.items():
            if idx < removed_index:
                new_tab_groups[idx] = group
            elif idx > removed_index:
                new_tab_groups[idx - 1] = group
        self.tab_groups = new_tab_groups
        
        # Update group representatives
        for group, rep_idx in self.group_representatives.items():
            if rep_idx > removed_index:
                self.group_representatives[group] = rep_idx - 1

    def update_tab_title(self, index, title=None, url=None):
        """Update the tab title and tooltip based on the current tab's content"""
        if index < 0 or index >= self.count():
            return
            
        tab = self.widget(index)
        
        # Get title from parameter or tab
        if title is None and hasattr(tab, 'page'):
            title = tab.page().title()
            
        # Get URL from parameter or tab
        if url is None and hasattr(tab, 'url'):
            url = tab.url().toString()
            
        # Use default title if none provided
        if not title:
            if url:
                # Extract domain from URL
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                title = domain or "New Tab"
            else:
                title = "New Tab"
                
        # Truncate long titles
        max_length = 30
        if len(title) > max_length:
            title = title[:max_length] + "..."
            
        # Set tab text and tooltip
        self.setTabText(index, title)
        if url:
            self.setTabToolTip(index, f"{title}\n{url}")
        else:
            self.setTabToolTip(index, title)
            
        # Update tab appearance
        if hasattr(self, '_tab_bar'):
            self._tab_bar.update_tab_appearance(index)

    def update_breadcrumbs(self):
        """Update the breadcrumb navigation"""
        # Clear existing breadcrumbs
        if hasattr(self, 'breadcrumb_layout'):
            while self.breadcrumb_layout.count():
                item = self.breadcrumb_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
        # Get current tab info
        current = self.currentIndex()
        if current < 0:
            return
            
        # Get group info
        group = self.tab_groups.get(current)
        if not group or group not in self.groups:
            self.breadcrumb_container.hide()
            return
            
        # Show breadcrumb container
        self.breadcrumb_container.show()
        
        # Add group indicator
        group_obj = self.groups[group]
        group_color = group_obj.color
        group_label = QLabel(f"⬤ {group}")
        group_label.setStyleSheet(f"color: {group_color.name()};")
        self.breadcrumb_layout.addWidget(group_label)
        
        # Add separator
        separator = QLabel("›")
        separator.setStyleSheet("color: #4c566a; margin: 0 4px;")
        self.breadcrumb_layout.addWidget(separator)
        
        # Add current tab
        tab_label = QLabel(self.tabText(current))
        tab_label.setStyleSheet("color: #d8dee9;")
        self.breadcrumb_layout.addWidget(tab_label)
        
        # Add stretch to push breadcrumbs to the left
        self.breadcrumb_layout.addStretch()

    def _show_group_preview(self, index, group, use_spread=False):
        """Show preview of tabs in the group"""
        if use_spread:
            # Use spread dialog for touch/mobile
            if not hasattr(self, 'tab_spread'):
                from .dialogs import TabSpreadDialog
                self.tab_spread = TabSpreadDialog(self)
            self.tab_spread.populate_spread()
            self.tab_spread.show()
            return
            
        # Use dropdown for keyboard/mouse
        if not hasattr(self, 'preview_container'):
            return
            
        # Clear existing items
        self.group_preview.clear()
        
        # Add items for each tab in group
        for tab_index in range(self.count()):
            if self.tab_groups.get(tab_index) == group:
                item = QListWidgetItem(self.tabIcon(tab_index), self.tabText(tab_index))
                item.setData(Qt.ItemDataRole.UserRole, tab_index)
                self.group_preview.addItem(item)
                
        # Position and show preview
        pos = self._tab_bar.tabRect(index).bottomLeft()
        global_pos = self._tab_bar.mapToGlobal(pos)
        self.preview_container.move(global_pos)
        self.preview_container.show()
        
    def _navigate_to_preview_tab(self, item):
        """Navigate to the selected preview tab"""
        if not item:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        if index >= 0:
            self.setCurrentIndex(index)
        if hasattr(self, 'preview_container'):
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
            self.close_tab(current)

    def show_port_dialog(self):
        """Show port selection dialog"""
        dialog = PortGridDialog(self)
        dialog.show()

    def _show_preview(self):
        """Show preview for the current tab"""
        if not hasattr(self, 'preview_container'):
            return
            
        current = self.currentIndex()
        if current < 0:
            return
            
        # Get group info
        group = self.tab_groups.get(current)
        if group and group in self.groups:
            self._show_group_preview(current, group)
            
    def update_breadcrumbs(self):
        """Update the breadcrumb navigation"""
        # Clear existing breadcrumbs
        if hasattr(self, 'breadcrumb_layout'):
            while self.breadcrumb_layout.count():
                item = self.breadcrumb_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
        # Get current tab info
        current = self.currentIndex()
        if current < 0:
            return
            
        # Get group info
        group = self.tab_groups.get(current)
        if not group or group not in self.groups:
            self.breadcrumb_container.hide()
            return
            
        # Show breadcrumb container
        self.breadcrumb_container.show()
        
        # Add group indicator
        group_obj = self.groups[group]
        group_color = group_obj.color
        group_label = QLabel(f"⬤ {group}")
        group_label.setStyleSheet(f"color: {group_color.name()};")
        self.breadcrumb_layout.addWidget(group_label)
        
        # Add separator
        separator = QLabel("›")
        separator.setStyleSheet("color: #4c566a; margin: 0 4px;")
        self.breadcrumb_layout.addWidget(separator)
        
        # Add current tab
        tab_label = QLabel(self.tabText(current))
        tab_label.setStyleSheet("color: #d8dee9;")
        self.breadcrumb_layout.addWidget(tab_label)
        
        # Add stretch to push breadcrumbs to the left
        self.breadcrumb_layout.addStretch()

class TabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDrawBase(False)
        self.setExpanding(False)
        self.setMovable(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Set modern styling
        self.setStyleSheet("""
            QTabBar {
                background: #2e3440;
            }
            QTabBar::tab {
                background: #2e3440;
                color: #d8dee9;
                padding: 8px 20px;
                border: none;
                min-width: 150px;
                max-width: 300px;
                margin-right: 2px;
            }
            QTabBar::tab:hover {
                background: #3b4252;
            }
            QTabBar::tab:selected {
                background: #3b4252;
                color: #88c0d0;
                border-top: 2px solid #88c0d0;
            }
            QTabBar::tab:selected:hover {
                background: #434c5e;
            }
            QTabBar::close-button {
                image: url(close.png);
                subcontrol-position: right;
                subcontrol-origin: padding;
                margin-right: 4px;
            }
            QTabBar::close-button:hover {
                background: #bf616a;
                border-radius: 2px;
            }
        """)
        
        # Enable touch support
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        
        # Track touch/mouse state
        self.press_pos = None
        self.last_pos = None
        self.dragging = False
        self.touch_timer = QTimer()
        self.touch_timer.setSingleShot(True)
        self.touch_timer.timeout.connect(self._handle_long_press)

    def keyPressEvent(self, event):
        """Handle keyboard navigation"""
        if event.key() == Qt.Key.Key_Down:
            # Show group preview for current tab
            current = self.currentIndex()
            tab_widget = self.parent()
            if tab_widget and hasattr(tab_widget, 'tab_groups'):
                group = tab_widget.tab_groups.get(current)
                if group and current == tab_widget.group_representatives.get(group):
                    tab_widget._show_group_preview(current, group)
                    event.accept()
                    return
        elif event.key() == Qt.Key.Key_Left:
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
            
        super().keyPressEvent(event)
        
    def _handle_long_press(self):
        """Handle long press gesture"""
        if self.press_pos is not None:
            index = self.tabAt(self.press_pos.toPoint())
            if index != -1:
                # Show context menu
                self.parent().show_tab_menu(index, self.mapToGlobal(self.press_pos.toPoint()))

    def tabSizeHint(self, index):
        """Return the size for the tab at index"""
        size = super().tabSizeHint(index)
        
        # Adjust width based on content
        text = self.parent().tabText(index)
        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        
        # Add space for close button and padding
        width = text_width + 60
        
        # Constrain to min/max
        width = max(150, min(width, 300))
        
        return QSize(width, size.height())
        
    def update_tab_appearance(self, index):
        """Update tab appearance based on state"""
        if not hasattr(self.parent(), 'memory_manager'):
            return
            
        # Get tab state
        memory_manager = self.parent().memory_manager
        state = memory_manager.states.get(index)
        is_active = self.currentIndex() == index
        
        # Get group info
        group = self.parent().tab_groups.get(index)
        group_color = None
        if group and group in self.parent().groups:
            group_color = self.parent().groups[group].color
        
        # Build style
        style = []
        
        # Base style
        style.append("QTabBar::tab:selected { background: #3b4252; }")
        
        # State-specific style
        if state == TabState.HIBERNATED:
            style.append(f"QTabBar::tab:selected {{ color: #666666; }}")
        elif state == TabState.SNOOZED:
            style.append(f"QTabBar::tab:selected {{ color: #81a1c1; }}")
        elif is_active:
            style.append(f"QTabBar::tab:selected {{ color: #88c0d0; }}")
        
        # Group color
        if group_color:
            style.append(f"""
                QTabBar::tab:selected {{
                    border-top: 2px solid {group_color.name()};
                }}
            """)
        
        # Apply style
        self.setStyleSheet("\n".join(style))
        
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        self.press_pos = event.pos()
        self.last_pos = event.pos()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        if self.press_pos is not None:
            # Check for drag threshold
            if not self.dragging and (event.pos() - self.press_pos).manhattanLength() > 10:
                self.dragging = True
            
            if self.dragging:
                # Handle tab reordering
                index = self.tabAt(self.last_pos)
                new_index = self.tabAt(event.pos())
                
                if index != -1 and new_index != -1 and index != new_index:
                    self.parent().moveTab(index, new_index)
                
            self.last_pos = event.pos()
        
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if not self.dragging and self.press_pos is not None:
            # Handle click
            index = self.tabAt(event.pos())
            if index != -1:
                if event.button() == Qt.MouseButton.MiddleButton:
                    # Middle click to close
                    self.parent().close_tab(index)
                else:
                    # Left click to select
                    self.parent().setCurrentIndex(index)
        
        self.press_pos = None
        self.dragging = False
        super().mouseReleaseEvent(event)
        
    def event(self, event):
        """Handle touch events"""
        if event.type() == QEvent.Type.TouchBegin:
            # Start touch timer for long press
            self.touch_timer.start(500)
            self.press_pos = event.points()[0].position()
            return True
            
        elif event.type() == QEvent.Type.TouchEnd:
            self.touch_timer.stop()
            if self.press_pos is not None:
                pos = event.points()[0].position()
                # Check if it was a tap (minimal movement)
                if (pos - self.press_pos).manhattanLength() < 10:
                    index = self.tabAt(pos.toPoint())
                    if index != -1:
                        self.parent().setCurrentIndex(index)
            self.press_pos = None
            return True
            
        elif event.type() == QEvent.Type.TouchUpdate:
            if self.press_pos is not None:
                pos = event.points()[0].position()
                # Handle swipe
                if (pos - self.press_pos).manhattanLength() > 50:
                    self.touch_timer.stop()
                    delta = pos.x() - self.press_pos.x()
                    if abs(delta) > 50:
                        # Horizontal swipe - change tabs
                        if delta > 0:
                            self.parent().prev_tab()
                        else:
                            self.parent().next_tab()
                    self.press_pos = None
            return True
            
        return super().event(event)

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
