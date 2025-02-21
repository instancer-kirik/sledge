def setup_toolbar(explorer, toolbar_layout):
    """Setup toolbar buttons with modern styling"""
    # Apply base toolbar styling
    toolbar_layout.setSpacing(4)
    toolbar_layout.setContentsMargins(4, 4, 4, 4)

    # Navigation group
    nav_group = create_nav_group(explorer, button_style)
    toolbar_layout.addWidget(nav_group)
    add_toolbar_separator(toolbar_layout)

    # View group
    view_group = create_view_group(explorer, button_style)
    toolbar_layout.addWidget(view_group)
    add_toolbar_separator(toolbar_layout)

    # File operations group
    file_ops = create_file_ops_group(explorer, button_style)
    toolbar_layout.addWidget(file_ops)
    add_toolbar_separator(toolbar_layout)

    # Testing and documentation group
    test_docs = create_test_docs_group(explorer, button_style)
    toolbar_layout.addWidget(test_docs)
    add_toolbar_separator(toolbar_layout)

    # Settings group
    settings_group = create_settings_group(explorer, button_style)
    toolbar_layout.addWidget(settings_group)

    # Add flexible spacer
    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    toolbar_layout.addWidget(spacer)

    # Project type indicator (right-aligned)
    explorer.project_type = QLabel()
    explorer.project_type.setStyleSheet("QLabel { padding: 4px; }")
    toolbar_layout.addWidget(explorer.project_type)

def create_view_group(explorer, button_style):
    """Create view operations button group"""
    view_group = QWidget()
    view_layout = QHBoxLayout(view_group)
    view_layout.setContentsMargins(0, 0, 0, 0)
    view_layout.setSpacing(2)

    # View mode buttons
    explorer.list_view_btn = QPushButton("List")
    explorer.list_view_btn.setIcon(QIcon.fromTheme("view-list-symbolic"))
    explorer.list_view_btn.setCheckable(True)
    explorer.list_view_btn.setChecked(True)
    explorer.list_view_btn.setToolTip("List View")
    explorer.list_view_btn.clicked.connect(lambda: explorer.switch_view_mode('list'))
    explorer.list_view_btn.setStyleSheet(button_style)
    view_layout.addWidget(explorer.list_view_btn)

    explorer.grid_view_btn = QPushButton("Grid")
    explorer.grid_view_btn.setIcon(QIcon.fromTheme("view-grid-symbolic"))
    explorer.grid_view_btn.setCheckable(True)
    explorer.grid_view_btn.setToolTip("Grid View")
    explorer.grid_view_btn.clicked.connect(lambda: explorer.switch_view_mode('grid'))
    explorer.grid_view_btn.setStyleSheet(button_style)
    view_layout.addWidget(explorer.grid_view_btn)

    # Show/Hide hidden files
    explorer.hidden_files_btn = QPushButton("Hidden")
    explorer.hidden_files_btn.setIcon(QIcon.fromTheme("view-hidden"))
    explorer.hidden_files_btn.setCheckable(True)
    explorer.hidden_files_btn.setToolTip("Show Hidden Files")
    explorer.hidden_files_btn.clicked.connect(explorer.toggle_hidden_files)
    explorer.hidden_files_btn.setStyleSheet(button_style)
    view_layout.addWidget(explorer.hidden_files_btn)

    # Preview toggle
    explorer.preview_btn = QPushButton("Preview")
    explorer.preview_btn.setIcon(QIcon.fromTheme("document-preview"))
    explorer.preview_btn.setCheckable(True)
    explorer.preview_btn.setToolTip("Toggle Preview Panel")
    explorer.preview_btn.clicked.connect(explorer.toggle_preview)
    explorer.preview_btn.setStyleSheet(button_style)
    view_layout.addWidget(explorer.preview_btn)

    return view_group

def create_settings_group(explorer, button_style):
    """Create settings button group"""
    settings_group = QWidget()
    settings_layout = QHBoxLayout(settings_group)
    settings_layout.setContentsMargins(0, 0, 0, 0)
    settings_layout.setSpacing(2)

    explorer.settings_button = QPushButton("Settings")
    explorer.settings_button.setIcon(QIcon.fromTheme("preferences-system"))
    explorer.settings_button.setToolTip("Application Settings")
    explorer.settings_button.clicked.connect(explorer.show_settings)
    explorer.settings_button.setStyleSheet(button_style)
    settings_layout.addWidget(explorer.settings_button)

    return settings_group 