from PyQt6.QtWidgets import QSplitter,QDialog, QColorDialog,QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QComboBox, QLabel, QTreeWidget, QTreeWidgetItem, QScrollArea, QFrame, QWidget, QGridLayout, QFileDialog, QMenu
from PyQt6.QtGui import QColor, QEventPoint
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QSize, QEvent, QRect 
import psutil
from .states import TabState

class TabListDialog(QDialog):
    def __init__(self, tab_widget, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Tab Manager")
        self.setMinimumSize(800, 600)
        layout = QVBoxLayout(self)

        # Search bar
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search tabs...")
        self.search.textChanged.connect(self.filter_tabs)
        layout.addWidget(self.search)

        # Split view
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Group tree
        self.group_tree = QTreeWidget()
        self.group_tree.setHeaderLabel("Groups")
        self.group_tree.itemSelectionChanged.connect(self.on_group_selected)
        splitter.addWidget(self.group_tree)

        # Tab list
        self.tab_list = QTreeWidget()
        self.tab_list.setHeaderLabels(["Title", "URL", "Status"])
        self.tab_list.setColumnWidth(0, 300)
        splitter.addWidget(self.tab_list)

        # Buttons
        button_layout = QHBoxLayout()
        
        self.new_group_btn = QPushButton("New Group")
        self.new_group_btn.clicked.connect(self.create_new_group)
        
        self.move_btn = QPushButton("Move to Group")
        self.move_btn.clicked.connect(self.move_to_group)
        
        self.snooze_btn = QPushButton("Snooze Selected")
        self.snooze_btn.clicked.connect(self.snooze_selected)
        
        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self.duplicate_selected)
        
        self.merge_btn = QPushButton("Merge Windows")
        self.merge_btn.clicked.connect(self.merge_windows)
        
        self.export_btn = QPushButton("Export Tabs")
        self.export_btn.clicked.connect(self.export_tabs)
        
        self.stats_btn = QPushButton("Tab Stats")
        self.stats_btn.clicked.connect(self.show_stats)
        
        button_layout.addWidget(self.new_group_btn)
        button_layout.addWidget(self.move_btn)
        button_layout.addWidget(self.snooze_btn)
        button_layout.addWidget(self.duplicate_btn)
        button_layout.addWidget(self.merge_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.stats_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)

        self.populate_groups()
        self.populate_tabs()

        # Add context menu to tab list
        self.tab_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_list.customContextMenuRequested.connect(self.show_tab_context_menu)

    def populate_groups(self):
        """Populate group tree with nested structure"""
        self.group_tree.clear()
        
        # Add "All Tabs" root item
        all_tabs = QTreeWidgetItem(["All Tabs"])
        self.group_tree.addTopLevelItem(all_tabs)
        
        # Add "Ungrouped" item
        ungrouped = QTreeWidgetItem(["Ungrouped"])
        self.group_tree.addTopLevelItem(ungrouped)
        
        def add_group_item(group, parent_item=None):
            item = QTreeWidgetItem([group.name])
            item.setData(0, Qt.ItemDataRole.UserRole, group)
            
            # Set group color indicator
            item.setBackground(0, group.color)
            
            if parent_item:
                parent_item.addChild(item)
            else:
                self.group_tree.addTopLevelItem(item)
            
            # Add subgroups recursively
            for subgroup in group.subgroups.values():
                add_group_item(subgroup, item)
        
        # Add all groups - Fixed reference
        for group in self.tab_widget.groups.values():
            if not group.parent:  # Only add top-level groups
                add_group_item(group)

    def populate_tabs(self, group=None, search_text=None):
        """Populate tab list based on selected group and search"""
        self.tab_list.clear()
        
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            title = self.tab_widget.tabText(i)
            url = tab.url().toString() if hasattr(tab, 'url') else ""
            
            # Check if tab belongs to selected group - Fixed reference
            tab_group = self.tab_widget.tab_groups.get(i)
            
            if ((group is None or tab_group == group.name) and
                (not search_text or 
                 search_text.lower() in title.lower() or 
                 search_text.lower() in url.lower())):
                
                item = QTreeWidgetItem([title, url])
                item.setData(0, Qt.ItemDataRole.UserRole, i)
                
                # Add status indicator - Fixed reference
                status = "Active"
                if self.tab_widget.memory_manager.states.get(i) == TabState.SNOOZED:
                    status = "Snoozed 💤"
                item.setText(2, status)
                
                self.tab_list.addTopLevelItem(item)

    def filter_tabs(self):
        """Filter tabs based on search text"""
        search_text = self.search.text()
        selected = self.group_tree.selectedItems()
        group = None if not selected else selected[0].data(0, Qt.ItemDataRole.UserRole)
        self.populate_tabs(group, search_text)

    def on_group_selected(self):
        """Handle group selection"""
        selected = self.group_tree.selectedItems()
        if selected:
            group = selected[0].data(0, Qt.ItemDataRole.UserRole)
            self.populate_tabs(group, self.search.text())

    def create_new_group(self):
        """Create a new group or subgroup"""
        selected = self.group_tree.selectedItems()
        parent_group = None if not selected else selected[0].data(0, Qt.ItemDataRole.UserRole)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Group")
        layout = QVBoxLayout(dialog)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Group Name")
        layout.addWidget(name_input)
        
        color_btn = QPushButton("Choose Color")
        color = None
        
        def choose_color():
            nonlocal color
            color = QColorDialog.getColor()
            if color.isValid():
                color_btn.setStyleSheet(f"background-color: {color.name()}")
        
        color_btn.clicked.connect(choose_color)
        layout.addWidget(color_btn)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text()
            if name:
                if parent_group:
                    parent_group.add_subgroup(name, color)
                else:
                    self.tab_widget.createGroup(name, color)
                self.populate_groups()

    def show_tab_context_menu(self, position):
        menu = QMenu()
        
        # Basic actions
        open_new = menu.addAction("Open in New Window")
        duplicate = menu.addAction("Duplicate")
        pin = menu.addAction("Pin Tab")
        
        # Group submenu - Fixed reference
        group_menu = menu.addMenu("Move to Group")
        for group_name in self.tab_widget.groups:
            group_menu.addAction(group_name)
        
        # Advanced actions
        menu.addSeparator()
        bookmark = menu.addAction("Bookmark All in Group")
        export = menu.addAction("Export Group as Session")
        hibernate = menu.addAction("Hibernate Group")
        
        action = menu.exec(self.tab_list.mapToGlobal(position))
        if action:
            self.handle_context_action(action)

    def show_stats(self):
        """Show tab statistics"""
        stats_dialog = QDialog(self)
        stats_dialog.setWindowTitle("Tab Statistics")
        layout = QVBoxLayout(stats_dialog)
        
        # Count tabs by group
        group_counts = {}
        total_tabs = self.tab_widget.count()
        active_tabs = sum(1 for i in range(total_tabs) 
                         if self.tab_widget.memory_manager.states.get(i) == TabState.ACTIVE)
        
        
        for i in range(total_tabs):
            group = self.tab_widget.tab_groups.get(i, "Ungrouped")
            group_counts[group] = group_counts.get(group, 0) + 1
        
        # Create stats display
        stats_text = f"""
        Total Tabs: {total_tabs}
        Active Tabs: {active_tabs}
        Snoozed Tabs: {total_tabs - active_tabs}
        Memory Usage: {psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB
        
        Tabs by Group:
        {'-' * 20}
        """
        for group, count in group_counts.items():
            stats_text += f"\n{group}: {count} tabs"
        
        stats_label = QLabel(stats_text)
        layout.addWidget(stats_label)
        
        stats_dialog.exec()

    def export_tabs(self):
        """Export tabs to various formats"""
        selected_items = self.tab_list.selectedItems()
        if not selected_items:
            return
            
        export_dialog = QDialog(self)
        export_dialog.setWindowTitle("Export Tabs")
        layout = QVBoxLayout(export_dialog)
        
        format_combo = QComboBox()
        format_combo.addItems(["Bookmarks HTML", "URL List", "Session File", "Markdown"])
        layout.addWidget(format_combo)
        
        export_btn = QPushButton("Export")
        layout.addWidget(export_btn)
        
        def do_export():
            fmt = format_combo.currentText()
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Tabs",
                filter=f"*.{fmt.lower().split()[0]}"
            )
            if path:
                self.export_tabs_to_file(path, fmt, selected_items)
        
        export_btn.clicked.connect(do_export)
        export_dialog.exec()

    def merge_windows(self):
        """Merge tabs from other windows"""
        # This would require window management code in the main browser
        pass

    def duplicate_selected(self):
        """Duplicate selected tabs"""
        selected_items = self.tab_list.selectedItems()
        for item in selected_items:
            tab_index = item.data(0, Qt.ItemDataRole.UserRole)
            tab = self.tab_widget.widget(tab_index)
            if hasattr(tab, 'url'):
                new_index = self.tab_widget.add_new_tab(tab.url())
                # Copy group assignment if any
                group = self.tab_widget.tab_groups.get(tab_index)
                if group:
                    self.tab_widget.addTabToGroup(new_index, group)

    def move_to_group(self):
        """Move selected tabs to a different group"""
        selected_items = self.tab_list.selectedItems()
        if not selected_items:
            return
            
        menu = QMenu(self)
        # Add "Remove from Group" option
        remove_action = menu.addAction("Remove from Group")
        menu.addSeparator()
        
        # Add existing groups - Fixed reference
        for group_name in self.tab_widget.groups:
            action = menu.addAction(group_name)
            action.triggered.connect(
                lambda checked, g=group_name: self._do_move_to_group(g)
            )
        menu.exec(self.move_btn.mapToGlobal(QPoint(0, self.move_btn.height())))

    def _do_move_to_group(self, group_name):
        """Actually move the selected tabs to the group"""
        for item in self.tab_list.selectedItems():
            tab_index = item.data(0, Qt.ItemDataRole.UserRole)
            if group_name:
                self.tab_widget.addTabToGroup(tab_index, group_name)
            else:
                # Remove from current group
                self.tab_widget.remove_from_group(tab_index)
        self.populate_tabs()

    def snooze_selected(self):
        """Snooze selected tabs"""
        selected_items = self.tab_list.selectedItems()
        for item in selected_items:
            tab_index = item.data(0, Qt.ItemDataRole.UserRole)
            self.tab_widget.memory_manager.snooze_tab(tab_index)
        self.populate_tabs()  # Refresh the list

class TabSpreadDialog(QDialog):
    def __init__(self, tab_widget, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Tab Overview")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins for mobile
        
        # Top bar with search and view mode
        top_bar = QWidget()
        top_bar.setStyleSheet("""
            QWidget {
                background: #2e3440;
                border-radius: 15px;
                padding: 5px;
            }
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setSpacing(10)
        
        # Search bar with touch-friendly styling
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search Tabs...")
        self.search.setMinimumHeight(50)  # Taller for touch
        self.search.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                padding: 10px 20px;
                border: none;
                border-radius: 25px;
                background: #3b4252;
                color: #d8dee9;
            }
            QLineEdit:focus {
                background: #434c5e;
            }
        """)
        self.search.textChanged.connect(self.filter_tabs)
        top_layout.addWidget(self.search, stretch=1)
        
        # View mode selector with touch-friendly styling
        self.view_mode = QComboBox()
        self.view_mode.addItems(["Cards", "List", "Groups"])
        self.view_mode.setMinimumHeight(50)
        self.view_mode.setMinimumWidth(120)
        self.view_mode.setStyleSheet("""
            QComboBox {
                font-size: 18px;
                padding: 10px 20px;
                border: none;
                border-radius: 25px;
                background: #3b4252;
                color: #d8dee9;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 20px;
                height: 20px;
            }
            QComboBox QAbstractItemView {
                background: #2e3440;
                border: none;
                border-radius: 15px;
                padding: 10px;
                selection-background-color: #434c5e;
            }
        """)
        self.view_mode.currentTextChanged.connect(self.change_view)
        top_layout.addWidget(self.view_mode)
        
        layout.addWidget(top_bar)
        
        # Scroll area for tab cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 20px;
                background: #2e3440;
            }
            QScrollBar::handle:vertical {
                background: #4c566a;
                min-height: 40px;
                border-radius: 10px;
                margin: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Container for tab cards
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(10)  # Reduced spacing for mobile
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        # Add swipe gesture recognition
        self._setup_touch_gestures()
        self.populate_spread()
    
    def _setup_touch_gestures(self):
        """Setup touch gesture recognition"""
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.touch_start = None
        self.current_card = None
    
    def event(self, event):
        """Handle touch events for gestures"""
        if event.type() == QEvent.Type.TouchBegin:
            points = event.points()
            if points:
                self.touch_start = points[0].position()
                # Find card under touch point
                pos = self.scroll.mapFrom(self, self.touch_start)
                self.current_card = self._find_card_at(pos)
            return True
            
        elif event.type() == QEvent.Type.TouchUpdate:
            if self.touch_start and self.current_card:
                points = event.points()
                if points:
                    pos = points[0].position()
                    delta = pos - self.touch_start
                    
                    # Handle swipe gestures
                    if abs(delta.x()) > 100:  # Horizontal swipe
                        if delta.x() > 0:
                            self._handle_swipe_right(self.current_card)
                        else:
                            self._handle_swipe_left(self.current_card)
                        self.touch_start = None
                        self.current_card = None
            return True
            
        elif event.type() == QEvent.Type.TouchEnd:
            self.touch_start = None
            self.current_card = None
            return True
            
        return super().event(event)
    
    def _find_card_at(self, pos):
        """Find the tab card widget at the given position"""
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if widget and widget.geometry().contains(pos):
                return widget
        return None
    
    def _handle_swipe_right(self, card):
        """Handle right swipe on card (e.g., add to group)"""
        index = card.property("tab_index")
        if index is not None:
            # Show quick group menu
            menu = QMenu(self)
            for group_name in self.tab_widget.groups:
                action = menu.addAction(group_name)
                action.triggered.connect(
                    lambda checked, g=group_name: self.tab_widget.addTabToGroup(index, g)
                )
            menu.exec(card.mapToGlobal(card.rect().center()))
    
    def _handle_swipe_left(self, card):
        """Handle left swipe on card (e.g., close tab)"""
        index = card.property("tab_index")
        if index is not None:
            # Animate card off screen
            animation = QPropertyAnimation(card, b"geometry")
            animation.setDuration(200)
            start_geo = card.geometry()
            end_geo = start_geo.translated(-start_geo.width(), 0)
            animation.setStartValue(start_geo)
            animation.setEndValue(end_geo)
            animation.finished.connect(lambda: self.tab_widget.removeTab(index))
            animation.start()
    
    def create_tab_preview(self, tab, title, url, index):
        """Create a touch-friendly tab preview card"""
        preview = QFrame()
        preview.setProperty("tab_index", index)  # Store index for gestures
        preview.setFrameStyle(QFrame.Shape.StyledPanel)
        preview.setMinimumSize(280, 200)  # Slightly smaller for mobile grid
        preview.setStyleSheet("""
            QFrame {
                background: #3b4252;
                border-radius: 15px;
                border: none;
            }
            QFrame:active {
                background: #434c5e;
            }
            QLabel {
                color: #d8dee9;
                font-size: 18px;  /* Increased base font size */
            }
        """)
        
        layout = QVBoxLayout(preview)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Title bar with group indicator
        title_bar = QHBoxLayout()
        group = self.tab_widget.tab_groups.get(index)
        if group:
            # Skip empty URLs for group representatives
            if hasattr(tab, 'url') and tab.url().toString():
                group_label = QLabel(f"[{group}]")
                group_label.setStyleSheet(f"""
                    QLabel {{
                        color: {self.tab_widget.groups[group].color.name()};
                        font-weight: bold;
                        font-size: 20px;  /* Increased group label size */
                        padding: 6px 12px;
                        background: rgba(0, 0, 0, 0.2);
                        border-radius: 12px;
                    }}
                """)
                title_bar.addWidget(group_label)
        
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold;")  # Increased title size
        title_bar.addWidget(title_label)
        layout.addLayout(title_bar)
        
        # Preview image (if available)
        if hasattr(tab, 'grab'):
            preview_label = QLabel()
            pixmap = tab.grab().scaled(
                260, 150, 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            preview_label.setPixmap(pixmap)
            preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(preview_label)
        
        # URL with ellipsis (only show if URL exists)
        if hasattr(tab, 'url') and tab.url().toString():
            url_label = QLabel(url)
            url_label.setWordWrap(True)
            url_label.setStyleSheet("color: #88c0d0; font-size: 16px;")  # Increased URL size
            layout.addWidget(url_label)
        
        # Status indicators
        status_layout = QHBoxLayout()
        if hasattr(tab, 'page'):
            # Add loading spinner or favicon
            pass
        
        state = self.tab_widget.memory_manager.states.get(index)
        if state == TabState.SNOOZED:
            status = QLabel("💤 Snoozed")
            status.setStyleSheet("""
                QLabel {
                    color: #88c0d0;
                    padding: 8px 16px;
                    background: rgba(136, 192, 208, 0.1);
                    border-radius: 14px;
                    font-size: 18px;  /* Increased status size */
                }
            """)
            status_layout.addWidget(status)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Touch feedback
        preview.mousePressEvent = lambda e: self._handle_card_press(preview)
        preview.mouseReleaseEvent = lambda e: self._handle_card_release(preview, index)
        
        return preview
    
    def _handle_card_press(self, card):
        """Handle card press with visual feedback"""
        animation = QPropertyAnimation(card, b"geometry")
        animation.setDuration(100)
        start_geo = card.geometry()
        # Scale down slightly
        scaled_geo = QRect(
            start_geo.x() + 5,
            start_geo.y() + 5,
            start_geo.width() - 10,
            start_geo.height() - 10
        )
        animation.setStartValue(start_geo)
        animation.setEndValue(scaled_geo)
        animation.start()
    
    def _handle_card_release(self, card, index):
        """Handle card release and activation"""
        # Animate back to original size
        animation = QPropertyAnimation(card, b"geometry")
        animation.setDuration(100)
        end_geo = card.geometry()
        start_geo = QRect(
            end_geo.x() + 5,
            end_geo.y() + 5,
            end_geo.width() - 10,
            end_geo.height() - 10
        )
        animation.setStartValue(start_geo)
        animation.setEndValue(end_geo)
        animation.finished.connect(lambda: self.activate_tab(index))
        animation.start()
    
    def populate_spread(self, filter_text=""):
        """Populate the grid with tab cards"""
        # Clear existing items
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        row = 0
        col = 0
        # Responsive grid based on window width
        width = self.width()
        if width < 600:  # Phone
            max_cols = 1
        elif width < 1024:  # Tablet
            max_cols = 2
        else:  # Desktop
            max_cols = max(3, self.width() // 320)
        
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            title = self.tab_widget.tabText(i)
            url = tab.url().toString() if hasattr(tab, 'url') else ""
            
            if filter_text.lower() in title.lower() or filter_text.lower() in url.lower():
                preview = self.create_tab_preview(tab, title, url, i)
                self.grid_layout.addWidget(preview, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
    
    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        # Reflow grid on resize
        self.populate_spread(self.search.text())
    
    def filter_tabs(self):
        """Filter tabs based on search text"""
        self.populate_spread(self.search.text())
    
    def change_view(self, mode):
        """Change view mode"""
        if mode == "Cards":
            self.populate_spread(self.search.text())
        elif mode == "List":
            # Implement list view
            pass
        elif mode == "Groups":
            # Implement grouped view
            pass
    
    def activate_tab(self, index):
        """Activate selected tab with animation"""
        self.tab_widget.setCurrentIndex(index)
        
        # Fade out dialog
        fade_out = QPropertyAnimation(self, b"windowOpacity")
        fade_out.setDuration(200)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.finished.connect(self.accept)
        fade_out.start()