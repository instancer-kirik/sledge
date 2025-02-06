from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QLabel, QProgressBar, QHBoxLayout,
    QPushButton, QMenu, QDialog, QLineEdit, QComboBox, QInputDialog, QDialogButtonBox,
    QButtonGroup, QGroupBox, QSlider, QCheckBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon
import os
import json

class HTMLViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Web view for rendered HTML
        self.web_view = QWebEngineView()
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        
        # Text editor for HTML source
        self.source_editor = QTextEdit()
        self.source_editor.setReadOnly(True)
        
        self.layout.addWidget(self.web_view)
        self.layout.addWidget(self.source_editor)
        
    def set_html(self, html_content):
        """Update both the rendered view and source view"""
        self.web_view.setHtml(html_content)
        self.source_editor.setText(html_content)
        
    def clear(self):
        """Clear both views"""
        self.web_view.setHtml("")
        self.source_editor.clear()

class BookmarkWidget(QWidget):
    bookmark_clicked = pyqtSignal(str)  # Signal emits URL when bookmark clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Bookmark tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Name', 'URL'])
        self.tree.setColumnWidth(0, 200)
        self.tree.itemDoubleClicked.connect(self._on_bookmark_clicked)
        
        # Add bookmark button
        self.add_btn = QPushButton("Add Folder")
        self.add_btn.clicked.connect(self._add_folder)
        
        self.layout.addWidget(self.tree)
        self.layout.addWidget(self.add_btn)
        
        # Initialize default folders
        self._init_default_folders()
    
    def _init_default_folders(self):
        self.folders = {
            'toolbar': QTreeWidgetItem(self.tree, ['Bookmarks Bar']),
            'mobile': QTreeWidgetItem(self.tree, ['Mobile Bookmarks']),
            'other': QTreeWidgetItem(self.tree, ['Other Bookmarks'])
        }
        
    def add_bookmark(self, title, url, folder='other'):
        if folder in self.folders:
            item = QTreeWidgetItem(self.folders[folder])
            item.setText(0, title)
            item.setText(1, url)
            
    def _add_folder(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Folder")
        layout = QVBoxLayout(dialog)
        
        name_input = QLineEdit()
        layout.addWidget(QLabel("Folder Name:"))
        layout.addWidget(name_input)
        
        btn = QPushButton("Create")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text()
            if name:
                self.folders[name.lower()] = QTreeWidgetItem(self.tree, [name])
    
    def _on_bookmark_clicked(self, item, column):
        url = item.text(1)
        if url:  # Only emit if URL exists (not a folder)
            self.bookmark_clicked.emit(url)

class DownloadWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Downloads list
        self.list = QListWidget()
        self.layout.addWidget(self.list)
        
        # Clear completed button
        self.clear_btn = QPushButton("Clear Completed")
        self.clear_btn.clicked.connect(self._clear_completed)
        self.layout.addWidget(self.clear_btn)
        
        self.downloads = {}  # Store download items
    
    def add_download(self, download):
        """Add new download to the list"""
        item = DownloadItem(download)
        list_item = QListWidgetItem(self.list)
        list_item.setSizeHint(item.sizeHint())
        self.list.addItem(list_item)
        self.list.setItemWidget(list_item, item)
        self.downloads[download] = (list_item, item)
        
        # Connect download signals
        download.downloadProgress.connect(item.update_progress)
        download.finished.connect(item.finished)
    
    def _clear_completed(self):
        """Remove completed downloads from the list"""
        for download, (list_item, item) in list(self.downloads.items()):
            if item.is_completed:
                self.list.takeItem(self.list.row(list_item))
                del self.downloads[download]

class DownloadItem(QWidget):
    def __init__(self, download):
        super().__init__()
        self.download = download
        self.is_completed = False
        
        layout = QHBoxLayout(self)
        
        # Filename
        self.name_label = QLabel(download.path().split('/')[-1])
        layout.addWidget(self.name_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        layout.addWidget(self.progress)
        
        # Status label
        self.status = QLabel("Starting...")
        layout.addWidget(self.status)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.download.cancel)
        layout.addWidget(self.cancel_btn)
    
    def update_progress(self, received, total):
        """Update download progress"""
        progress = (received * 100) / total
        self.progress.setValue(int(progress))
        self.status.setText(f"{progress:.1f}%")
    
    def finished(self):
        """Handle download completion"""
        self.is_completed = True
        self.progress.setValue(100)
        self.status.setText("Completed")
        self.cancel_btn.setText("Remove")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.deleteLater)

class LinkStorageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Search and filter bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search links...")
        self.search_input.textChanged.connect(self.filter_links)
        search_layout.addWidget(self.search_input)
        
        # Category selector
        self.category_selector = QComboBox()
        self.category_selector.addItems(["All", "Reading List", "Reference", "Tools", "Articles"])
        self.category_selector.currentTextChanged.connect(self.filter_links)
        search_layout.addWidget(self.category_selector)
        
        self.layout.addLayout(search_layout)
        
        # Links tree with categories
        self.links_tree = QTreeWidget()
        self.links_tree.setHeaderLabels(["Title", "URL", "Tags", "Added"])
        self.links_tree.setColumnWidth(0, 250)
        self.links_tree.setColumnWidth(1, 300)
        self.links_tree.setColumnWidth(2, 150)
        self.links_tree.itemDoubleClicked.connect(self._open_link)
        self.layout.addWidget(self.links_tree)
        
        # Bottom toolbar
        toolbar = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Link")
        self.add_btn.clicked.connect(self.add_link)
        toolbar.addWidget(self.add_btn)
        
        self.add_category_btn = QPushButton("Add Category")
        self.add_category_btn.clicked.connect(self.add_category)
        toolbar.addWidget(self.add_category_btn)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_links)
        toolbar.addWidget(self.export_btn)
        
        self.layout.addLayout(toolbar)
        
        # Context menu
        self.links_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.links_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        self._load_links()
    
    def add_link(self, url=None, title=None):
        """Add a new link with dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Link")
        layout = QVBoxLayout(dialog)
        
        # Title input
        title_input = QLineEdit()
        title_input.setPlaceholderText("Title")
        if title:
            title_input.setText(title)
        layout.addWidget(title_input)
        
        # URL input
        url_input = QLineEdit()
        url_input.setPlaceholderText("URL")
        if url:
            url_input.setText(url)
        layout.addWidget(url_input)
        
        # Category selector
        category_input = QComboBox()
        category_input.addItems(self._get_categories())
        layout.addWidget(category_input)
        
        # Tags input
        tags_input = QLineEdit()
        tags_input.setPlaceholderText("Tags (comma separated)")
        layout.addWidget(tags_input)
        
        # Notes input
        notes_input = QTextEdit()
        notes_input.setPlaceholderText("Notes")
        notes_input.setMaximumHeight(100)
        layout.addWidget(notes_input)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            category = category_input.currentText()
            if not self._get_category_item(category):
                category_item = QTreeWidgetItem(self.links_tree, [category])
            
            link_item = QTreeWidgetItem([
                title_input.text(),
                url_input.text(),
                tags_input.text(),
                QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm")
            ])
            link_item.setData(0, Qt.ItemDataRole.UserRole, notes_input.toPlainText())
            
            self._get_category_item(category).addChild(link_item)
            self._save_links()
    
    def add_category(self):
        """Add a new category"""
        name, ok = QInputDialog.getText(self, "New Category", "Category name:")
        if ok and name:
            self.category_selector.addItem(name)
            QTreeWidgetItem(self.links_tree, [name])
            self._save_links()
    
    def show_context_menu(self, position):
        """Show context menu for links"""
        item = self.links_tree.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        
        # Add actions based on item type
        if item.parent():  # This is a link
            open_action = menu.addAction("Open")
            open_action.triggered.connect(lambda: self._open_link(item, 0))
            
            edit_action = menu.addAction("Edit")
            edit_action.triggered.connect(lambda: self._edit_link(item))
            
            copy_action = menu.addAction("Copy URL")
            copy_action.triggered.connect(lambda: QApplication.clipboard().setText(item.text(1)))
            
            menu.addSeparator()
            
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_link(item))
        else:  # This is a category
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self._rename_category(item))
            
            delete_action = menu.addAction("Delete Category")
            delete_action.triggered.connect(lambda: self._delete_category(item))
        
        menu.exec(self.links_tree.viewport().mapToGlobal(position))
    
    def _open_link(self, item, column):
        """Open the link in the browser"""
        if item.parent():  # Only if it's a link, not a category
            url = item.text(1)
            if url:
                self.parent().parent().add_new_tab(QUrl(url))
    
    def _save_links(self):
        """Save links to storage"""
        links = {}
        for i in range(self.links_tree.topLevelItemCount()):
            category = self.links_tree.topLevelItem(i)
            category_links = []
            for j in range(category.childCount()):
                link = category.child(j)
                category_links.append({
                    'title': link.text(0),
                    'url': link.text(1),
                    'tags': link.text(2),
                    'added': link.text(3),
                    'notes': link.data(0, Qt.ItemDataRole.UserRole)
                })
            links[category.text(0)] = category_links
        
        # Save to file
        with open(os.path.expanduser('~/.sledge/links.json'), 'w') as f:
            json.dump(links, f)
    
    def _load_links(self):
        """Load links from storage"""
        try:
            with open(os.path.expanduser('~/.sledge/links.json'), 'r') as f:
                links = json.load(f)
                
            for category, items in links.items():
                category_item = QTreeWidgetItem(self.links_tree, [category])
                for link in items:
                    link_item = QTreeWidgetItem([
                        link['title'],
                        link['url'],
                        link['tags'],
                        link['added']
                    ])
                    link_item.setData(0, Qt.ItemDataRole.UserRole, link.get('notes', ''))
                    category_item.addChild(link_item)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create default categories if no file exists
            for category in ["Reading List", "Reference", "Tools", "Articles"]:
                QTreeWidgetItem(self.links_tree, [category])
    
    def filter_links(self):
        """Filter links based on search text and category"""
        search_text = self.search_input.text().lower()
        category = self.category_selector.currentText()
        
        for i in range(self.links_tree.topLevelItemCount()):
            category_item = self.links_tree.topLevelItem(i)
            category_item.setHidden(
                category != "All" and category != category_item.text(0)
            )
            
            for j in range(category_item.childCount()):
                link_item = category_item.child(j)
                link_item.setHidden(
                    search_text and not any(
                        search_text in link_item.text(col).lower()
                        for col in range(link_item.columnCount())
                    )
                )

class StyleAdjusterPanel(QWidget):
    """Panel for adjusting browser theme and style settings"""
    
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Theme selection
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout(theme_group)
        
        self.theme_buttons = {}
        for theme_name in ['dark', 'light', 'sepia', 'nord', 'solarized']:
            btn = QPushButton(theme_name.title())
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, tn=theme_name: self._change_theme(tn))
            theme_layout.addWidget(btn)
            self.theme_buttons[theme_name] = btn
            
        # Set initial theme button state
        current_theme = 'dark' if self.theme.force_dark else self.theme.current_theme
        if current_theme in self.theme_buttons:
            self.theme_buttons[current_theme].setChecked(True)
            
        self.layout.addWidget(theme_group)
        
        # Force dark mode toggle
        self.force_dark = QCheckBox("Force Dark Mode")
        self.force_dark.setChecked(self.theme.force_dark)
        self.force_dark.toggled.connect(self._toggle_force_dark)
        self.layout.addWidget(self.force_dark)
        
        # Style adjustments
        adjust_group = QGroupBox("Style Adjustments")
        adjust_layout = QVBoxLayout(adjust_group)
        
        # Font size
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Size:"))
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setMinimum(12)
        self.font_slider.setMaximum(24)
        self.font_slider.setValue(self.theme.font_size)
        self.font_slider.valueChanged.connect(self._update_font_size)
        font_layout.addWidget(self.font_slider)
        self.font_label = QLabel(f"{self.theme.font_size}px")
        font_layout.addWidget(self.font_label)
        adjust_layout.addLayout(font_layout)
        
        # Line height
        line_layout = QHBoxLayout()
        line_layout.addWidget(QLabel("Line Height:"))
        self.line_slider = QSlider(Qt.Orientation.Horizontal)
        self.line_slider.setMinimum(10)
        self.line_slider.setMaximum(20)
        self.line_slider.setValue(int(self.theme.line_height * 10))
        self.line_slider.valueChanged.connect(self._update_line_height)
        line_layout.addWidget(self.line_slider)
        self.line_label = QLabel(f"{self.theme.line_height:.1f}")
        line_layout.addWidget(self.line_label)
        adjust_layout.addLayout(line_layout)
        
        # Max width
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Max Width:"))
        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setMinimum(400)
        self.width_slider.setMaximum(1200)
        self.width_slider.setValue(self.theme.max_width)
        self.width_slider.valueChanged.connect(self._update_max_width)
        width_layout.addWidget(self.width_slider)
        self.width_label = QLabel(f"{self.theme.max_width}px")
        width_layout.addWidget(self.width_label)
        adjust_layout.addLayout(width_layout)
        
        self.layout.addWidget(adjust_group)
        
        # Additional options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        self.hide_images = QCheckBox("Hide Images")
        self.hide_images.setChecked(self.theme.hide_images)
        self.hide_images.toggled.connect(self._update_options)
        options_layout.addWidget(self.hide_images)
        
        self.hide_ads = QCheckBox("Hide Ads")
        self.hide_ads.setChecked(self.theme.hide_ads)
        self.hide_ads.toggled.connect(self._update_options)
        options_layout.addWidget(self.hide_ads)
        
        self.justify_text = QCheckBox("Justify Text")
        self.justify_text.setChecked(self.theme.justify_text)
        self.justify_text.toggled.connect(self._update_options)
        options_layout.addWidget(self.justify_text)
        
        self.use_dyslexic_font = QCheckBox("Use Dyslexic Font")
        self.use_dyslexic_font.setChecked(self.theme.use_dyslexic_font)
        self.use_dyslexic_font.toggled.connect(self._update_options)
        options_layout.addWidget(self.use_dyslexic_font)
        
        self.layout.addWidget(options_group)
        
        # Add stretch at the end
        self.layout.addStretch()
        
    def _change_theme(self, theme_name):
        """Change the current theme"""
        self.theme.set_theme(theme_name)
        # Update UI to reflect changes
        if hasattr(self.parent(), 'update_theme'):
            self.parent().update_theme()
            
    def _toggle_force_dark(self, checked):
        """Toggle force dark mode"""
        self.theme.toggle_force_dark(checked)
        # Update theme buttons state
        current_theme = 'dark' if checked else self.theme.current_theme
        for name, btn in self.theme_buttons.items():
            btn.setChecked(name == current_theme)
        # Update UI
        if hasattr(self.parent(), 'update_theme'):
            self.parent().update_theme()
            
    def _update_font_size(self, value):
        """Update font size setting"""
        self.font_label.setText(f"{value}px")
        self.theme.update_style_settings(font_size=value)
        self._refresh_page()
        
    def _update_line_height(self, value):
        """Update line height setting"""
        height = value / 10
        self.line_label.setText(f"{height:.1f}")
        self.theme.update_style_settings(line_height=height)
        self._refresh_page()
        
    def _update_max_width(self, value):
        """Update max width setting"""
        self.width_label.setText(f"{value}px")
        self.theme.update_style_settings(max_width=value)
        self._refresh_page()
        
    def _update_options(self):
        """Update additional options"""
        self.theme.update_style_settings(
            hide_images=self.hide_images.isChecked(),
            hide_ads=self.hide_ads.isChecked(),
            justify_text=self.justify_text.isChecked(),
            use_dyslexic_font=self.use_dyslexic_font.isChecked()
        )
        self._refresh_page()
        
    def _refresh_page(self):
        """Refresh the current page to apply style changes"""
        if hasattr(self.parent(), 'current_tab'):
            tab = self.parent().current_tab()
            if tab and tab.page():
                url = tab.page().url()
                css, js = self.theme.inject_style(url)
                tab.page().runJavaScript(js)
