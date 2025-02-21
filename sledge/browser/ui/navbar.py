class NavigationBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Navigation buttons
        self.back_button = self._create_nav_button("◀", "Back")
        self.forward_button = self._create_nav_button("▶", "Forward")
        self.reload_button = self._create_nav_button("↻", "Reload")
        
        # Port button
        self.port_button = self._create_nav_button("⚡", "Quick Port Switch")
        self.port_button.clicked.connect(self.show_port_dialog)
        
        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or search...")
        
        # Add widgets to layout
        layout.addWidget(self.back_button)
        layout.addWidget(self.forward_button)
        layout.addWidget(self.reload_button)
        layout.addWidget(self.port_button)
        layout.addWidget(self.url_bar)

    def show_port_dialog(self):
        dialog = PortGridDialog(self)
        dialog.show()

    def _create_nav_button(self, text, tooltip):
        btn = QToolButton(self)
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(28, 28)
        btn.setStyleSheet("""
            QToolButton {
                background: #3b4252;
                border: none;
                border-radius: 4px;
                color: #d8dee9;
                font-size: 16px;
            }
            QToolButton:hover {
                background: #434c5e;
            }
        """)
        return btn 