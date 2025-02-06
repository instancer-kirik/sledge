class TabSpreadView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_widget = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QGridLayout()
        self.setLayout(layout)
        
        # Search bar at the top
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search tabs...")
        self.search_bar.textChanged.connect(self.filter_tabs)
        layout.addWidget(self.search_bar, 0, 0, 1, -1)
        
        # Grid for tab previews
        self.grid = QGridLayout()
        layout.addLayout(self.grid, 1, 0)
        
        self.update_previews()
        
    def update_previews(self):
        # Clear existing previews
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)
            
        # Create new previews
        row = 0
        col = 0
        max_cols = 3  # Adjust based on window width
        
        for index in range(self.tab_widget.count()):
            preview = self.create_tab_preview(index)
            self.grid.addWidget(preview, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
    def create_tab_preview(self, index):
        tab = self.tab_widget.widget(index)
        preview = QWidget()
        preview.setMinimumSize(300, 200)
        
        layout = QVBoxLayout()
        preview.setLayout(layout)
        
        # Title
        title = QLabel(self.tab_widget.tabText(index))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Thumbnail (if available)
        if hasattr(tab, 'grab'):
            thumbnail = tab.grab().scaled(280, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            thumb_label = QLabel()
            thumb_label.setPixmap(thumbnail)
            thumb_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(thumb_label)
            
        # Make the preview clickable
        preview.mousePressEvent = lambda e: self.select_tab(index)
        preview.setCursor(Qt.PointingHandCursor)
        preview.setStyleSheet("""
            QWidget {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 5px;
                padding: 10px;
            }
            QWidget:hover {
                background: palette(alternate-base);
                border-color: palette(highlight);
            }
        """)
        
        return preview
        
    def select_tab(self, index):
        self.tab_widget.setCurrentIndex(index)
        self.hide()  # Close the spread view after selection
        
    def filter_tabs(self, text):
        text = text.lower()
        for i in range(self.grid.count()):
            item = self.grid.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                title = widget.layout().itemAt(0).widget().text().lower()
                widget.setVisible(text in title)
                
    def showEvent(self, event):
        super().showEvent(event)
        self.update_previews()
        self.search_bar.setFocus()
        self.search_bar.clear() 