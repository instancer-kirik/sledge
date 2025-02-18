from PyQt6.QtWidgets import QSplitter,QDialog, QColorDialog,QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QComboBox, QLabel, QTreeWidget, QTreeWidgetItem, QScrollArea, QFrame, QWidget, QGridLayout, QFileDialog, QMenu, QMainWindow, QSizePolicy
from PyQt6.QtGui import QColor, QEventPoint
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QSize, QEvent, QRect 
import psutil
from .states import TabState
from PyQt6.QtCore import pyqtSignal

class PopoutWindow(QMainWindow):
    def __init__(self, tab_widget, tab_index, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.tab_index = tab_index
        self.init_ui()
        
    def init_ui(self):
        # Get the tab content
        tab = self.tab_widget.widget(self.tab_index)
        title = self.tab_widget.tabText(self.tab_index)
        self.setWindowTitle(f"Popout: {title}")
        
        # Create a toolbar with controls
        toolbar = self.addToolBar("Controls")
        
        # Add always on top toggle
        self.pin_action = toolbar.addAction("📌 Pin on Top")
        self.pin_action.setCheckable(True)
        self.pin_action.toggled.connect(self.toggle_always_on_top)
        
        # Add size presets
        size_combo = QComboBox()
        size_combo.addItems(["Custom", "360p", "480p", "720p", "1080p"])
        size_combo.currentTextChanged.connect(self.change_size)
        toolbar.addWidget(size_combo)
        
        # Add opacity control
        opacity_label = QLabel("Opacity:")
        toolbar.addWidget(opacity_label)
        opacity_combo = QComboBox()
        opacity_combo.addItems(["100%", "90%", "80%", "70%", "60%", "50%"])
        opacity_combo.currentTextChanged.connect(self.change_opacity)
        toolbar.addWidget(opacity_combo)
        
        # Add stream fix button
        fix_btn = toolbar.addAction("🔄 Fix Stream")
        fix_btn.triggered.connect(self.fix_stream)
        
        # Add debug button
        debug_btn = toolbar.addAction("🔧 Debug")
        debug_btn.triggered.connect(self.show_debug_info)
        
        # Add codec info button
        codec_btn = toolbar.addAction("ℹ️ Codec Info")
        codec_btn.triggered.connect(self.show_codec_info)
        
        # Set the tab as central widget
        self.setCentralWidget(tab)
        
        # Set a reasonable default size
        self.resize(480, 320)
        
        # Inject stream handlers
        self.inject_stream_handlers()
        
    def inject_stream_handlers(self):
        """Inject JavaScript to handle streams and fix common issues"""
        if hasattr(self.centralWidget(), 'page'):
            script = """
            // Store original VideoJS error handler
            if (window.videojs) {
                const originalError = videojs.getComponent('ErrorDisplay');
                
                // Custom error handler for VideoJS
                class CustomError extends originalError {
                    constructor(player, options) {
                        super(player, options);
                        this.originalCreateEl = this.createEl;
                        this.createEl = () => {
                            const el = this.originalCreateEl();
                            // Add retry button
                            const retryBtn = document.createElement('button');
                            retryBtn.textContent = '🔄 Retry';
                            retryBtn.onclick = () => this.player_.load();
                            el.appendChild(retryBtn);
                            return el;
                        };
                    }
                }
                
                // Register custom error handler
                videojs.registerComponent('ErrorDisplay', CustomError);
            }
            
            // WCO specific fixes
            function fixWCOStream() {
                const videos = document.getElementsByTagName('video');
                for (const video of videos) {
                    // Force HTML5 mode
                    video.setAttribute('playsinline', '');
                    video.setAttribute('webkit-playsinline', '');
                    
                    // Try to extract direct stream URL if available
                    if (video.src && video.src.includes('wco')) {
                        const possibleSources = Array.from(document.querySelectorAll('source'))
                            .map(s => s.src)
                            .filter(s => s && !s.includes('blob:'));
                        
                        if (possibleSources.length > 0) {
                            video.src = possibleSources[0];
                        }
                    }
                    
                    // Add error recovery
                    video.addEventListener('error', (e) => {
                        if (e.target.error.code === 4) {
                            // Try to reload with different source type
                            const currentSrc = e.target.src;
                            if (currentSrc) {
                                // Try alternative format
                                const newSrc = currentSrc.replace('.m3u8', '.mp4')
                                    .replace('.mp4', '.m3u8');
                                e.target.src = newSrc;
                                e.target.load();
                            }
                        }
                    });
                }
                
                // Handle VideoJS player if present
                if (window.videojs) {
                    const players = document.getElementsByClassName('video-js');
                    for (const player of players) {
                        if (player.player) {
                            // Force HTML5 tech
                            player.player.options_.techOrder = ['html5'];
                            // Add HLS support
                            if (player.player.options_.sources) {
                                player.player.src(player.player.options_.sources);
                            }
                        }
                    }
                }
            }
            
            // Run fixes
            fixWCOStream();
            // Watch for dynamic content
            new MutationObserver(() => fixWCOStream())
                .observe(document.body, {childList: true, subtree: true});
            """
            self.centralWidget().page().runJavaScript(script)
        
    def fix_stream(self):
        """Manually trigger stream fixes"""
        if hasattr(self.centralWidget(), 'page'):
            self.centralWidget().page().runJavaScript("fixWCOStream();")
            
    def toggle_always_on_top(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()  # Need to show again after changing flags
        
    def change_size(self, preset):
        sizes = {
            "360p": (640, 360),
            "480p": (854, 480),
            "720p": (1280, 720),
            "1080p": (1920, 1080)
        }
        if preset in sizes:
            self.resize(*sizes[preset])
            
    def change_opacity(self, value):
        """Change window opacity"""
        opacity = int(value.replace('%', '')) / 100.0
        self.setWindowOpacity(opacity)
            
    def show_debug_info(self):
        """Show video playback debug information"""
        if hasattr(self.centralWidget(), 'page'):
            script = """
            const debugInfo = {
                videos: Array.from(document.getElementsByTagName('video')).map(v => ({
                    src: v.currentSrc,
                    readyState: v.readyState,
                    networkState: v.networkState,
                    error: v.error ? {
                        code: v.error.code,
                        message: v.error.message
                    } : null,
                    played: v.played.length > 0,
                    duration: v.duration,
                    videoWidth: v.videoWidth,
                    videoHeight: v.videoHeight,
                    muted: v.muted,
                    volume: v.volume
                })),
                player: window.videojs ? 
                    Array.from(document.getElementsByClassName('video-js')).map(p => ({
                        id: p.id,
                        error: p.player ? p.player.error() : null,
                        sources: p.player ? p.player.currentSources() : []
                    })) : 'VideoJS not found'
            };
            debugInfo;
            """
            
            def show_debug(result):
                dialog = QDialog(self)
                dialog.setWindowTitle("Video Debug Info")
                layout = QVBoxLayout(dialog)
                
                text = QLabel(f"Debug Information:\n\n{str(result)}")
                text.setWordWrap(True)
                layout.addWidget(text)
                
                copy_btn = QPushButton("Copy to Clipboard")
                copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(str(result)))
                layout.addWidget(copy_btn)
                
                dialog.exec()
                
            self.centralWidget().page().runJavaScript(script, show_debug)
            
    def show_codec_info(self):
        """Show supported codec information"""
        if hasattr(self.centralWidget(), 'page'):
            script = """
            const videoEl = document.createElement('video');
            const codecInfo = {
                webm: videoEl.canPlayType('video/webm; codecs="vp8, vorbis"'),
                webmVP9: videoEl.canPlayType('video/webm; codecs="vp9"'),
                mp4H264: videoEl.canPlayType('video/mp4; codecs="avc1.42E01E"'),
                mp4H265: videoEl.canPlayType('video/mp4; codecs="hevc,mp4a.40.2"'),
                ogg: videoEl.canPlayType('video/ogg; codecs="theora"'),
                hls: videoEl.canPlayType('application/vnd.apple.mpegurl'),
                dash: videoEl.canPlayType('application/dash+xml'),
            };
            codecInfo;
            """
            
            def show_codec_info(result):
                dialog = QDialog(self)
                dialog.setWindowTitle("Supported Codecs")
                layout = QVBoxLayout(dialog)
                
                text = QLabel("Supported Video Formats:\n")
                for codec, support in result.items():
                    text.setText(text.text() + f"\n{codec}: {support or 'no'}")
                layout.addWidget(text)
                
                dialog.exec()
                
            self.centralWidget().page().runJavaScript(script, show_codec_info)
            
    def closeEvent(self, event):
        # Move the tab back to the main window
        tab = self.centralWidget()
        self.tab_widget.insertTab(self.tab_index, tab, self.windowTitle().replace("Popout: ", ""))
        self.tab_widget.setCurrentIndex(self.tab_index)
        super().closeEvent(event)

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
        popout = menu.addAction("Popout Player")  # Add popout option
        duplicate = menu.addAction("Duplicate")
        pin = menu.addAction("Pin Tab")
        
        # Group submenu
        group_menu = menu.addMenu("Move to Group")
        for group_name in self.tab_widget.groups:
            group_menu.addAction(group_name)
        
        # Advanced actions
        menu.addSeparator()
        bookmark = menu.addAction("Bookmark All in Group")
        export = menu.addAction("Export Group as Session")
        hibernate = menu.addAction("Hibernate Group")
        
        action = menu.exec(self.tab_list.mapToGlobal(position))
        if action == popout:  # Handle popout action
            selected_items = self.tab_list.selectedItems()
            if selected_items:
                tab_index = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
                self.popout_tab(tab_index)
                
    def popout_tab(self, tab_index):
        """Create a popout window for the selected tab"""
        popout = PopoutWindow(self.tab_widget, tab_index)
        popout.show()

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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tab Spread")
        self.setModal(True)
        
        # Create main layout
        self.layout = QVBoxLayout(self)
        
        # Create scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.layout.addWidget(self.scroll_area)
        
        # Create container widget for grid
        self.container = QWidget()
        self.scroll_area.setWidget(self.container)
        
        # Create grid layout
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(10)
        
        # Add close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        self.layout.addWidget(self.close_button)
        
    def populate_spread(self):
        """Populate the spread with tab previews"""
        # Clear existing items
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().deleteLater()
        
        # Get tab widget
        tab_widget = self.parent()
        if not tab_widget:
            return
            
        # Calculate grid dimensions
        tab_count = tab_widget.count()
        cols = min(4, tab_count)  # Max 4 columns
        rows = (tab_count + cols - 1) // cols  # Ceiling division
        
        # Add tab previews
        for i in range(tab_count):
            tab = tab_widget.widget(i)
            if not tab:
                continue
                
            # Create preview widget
            preview = TabPreviewWidget(tab)
            preview.clicked.connect(lambda idx=i: self._handle_preview_click(idx))
            
            # Add to grid
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(preview, row, col)
            
    def _handle_preview_click(self, index):
        """Handle preview click by switching to tab and closing dialog"""
        tab_widget = self.parent()
        if tab_widget:
            tab_widget.setCurrentIndex(index)
        self.close()

class TabPreviewWidget(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, tab, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout(self)
        
        # Add title label
        title = tab.windowTitle() or "Untitled"
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Add preview (if available)
        if hasattr(tab, 'grab'):
            preview = tab.grab().scaled(180, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            preview_label = QLabel()
            preview_label.setPixmap(preview)
            preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(preview_label)
        
        self.setStyleSheet("""
            QWidget {
                background: #2e3440;
                border-radius: 8px;
                padding: 8px;
            }
            QLabel {
                color: #d8dee9;
            }
        """)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()