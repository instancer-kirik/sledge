from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSpinBox, QComboBox, QCheckBox, QGroupBox,
    QTextEdit, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal

class TabDebugPanel(QWidget):
    """Debug panel for testing tab functionality"""
    
    # Signals for test operations
    trigger_hibernation = pyqtSignal(int)  # Tab index to hibernate
    trigger_restoration = pyqtSignal(int)  # Tab index to restore
    create_group = pyqtSignal(str, list)  # Group name, list of tab indices
    
    def __init__(self, tab_widget, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the debug panel UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Tab Operations Group
        tab_ops = QGroupBox("Tab Operations")
        tab_ops_layout = QVBoxLayout(tab_ops)
        
        # Tab Selection
        tab_select = QHBoxLayout()
        self.tab_index = QSpinBox()
        self.tab_index.setRange(0, 100)
        tab_select.addWidget(QLabel("Tab Index:"))
        tab_select.addWidget(self.tab_index)
        tab_ops_layout.addLayout(tab_select)
        
        # Operation Buttons
        btn_layout = QHBoxLayout()
        hibernate_btn = QPushButton("Hibernate Tab")
        hibernate_btn.clicked.connect(lambda: self.trigger_hibernation.emit(self.tab_index.value()))
        
        restore_btn = QPushButton("Restore Tab")
        restore_btn.clicked.connect(lambda: self.trigger_restoration.emit(self.tab_index.value()))
        
        btn_layout.addWidget(hibernate_btn)
        btn_layout.addWidget(restore_btn)
        tab_ops_layout.addLayout(btn_layout)
        
        layout.addWidget(tab_ops)
        
        # Group Operations
        group_ops = QGroupBox("Group Operations")
        group_ops_layout = QVBoxLayout(group_ops)
        
        # Group Creation
        group_create = QHBoxLayout()
        self.group_name = QComboBox()
        self.group_name.setEditable(True)
        self.group_name.addItems(["Work", "Personal", "Shopping", "Research"])
        group_create.addWidget(QLabel("Group Name:"))
        group_create.addWidget(self.group_name)
        
        create_group_btn = QPushButton("Create Group")
        create_group_btn.clicked.connect(self._create_group)
        group_create.addWidget(create_group_btn)
        group_ops_layout.addLayout(group_create)
        
        # Tab Selection for Group
        self.tab_selection = QTextEdit()
        self.tab_selection.setPlaceholderText("Enter tab indices separated by commas (e.g., 0,1,3)")
        self.tab_selection.setMaximumHeight(50)
        group_ops_layout.addWidget(self.tab_selection)
        
        layout.addWidget(group_ops)
        
        # State Display
        state_group = QGroupBox("Current State")
        state_layout = QVBoxLayout(state_group)
        
        # State refresh button
        refresh_btn = QPushButton("Refresh State")
        refresh_btn.clicked.connect(self.refresh_state)
        state_layout.addWidget(refresh_btn)
        
        # Scrollable state text
        self.state_display = QTextEdit()
        self.state_display.setReadOnly(True)
        state_layout.addWidget(self.state_display)
        
        layout.addWidget(state_group)
        
        # Update max tab index based on current count
        self.tab_widget.currentChanged.connect(self._update_tab_range)
        self._update_tab_range()
        
        # Initial state refresh
        self.refresh_state()
    
    def _update_tab_range(self):
        """Update the maximum value of the tab index spinbox"""
        self.tab_index.setMaximum(max(0, self.tab_widget.count() - 1))
    
    def _create_group(self):
        """Handle group creation button click"""
        try:
            indices = [int(i.strip()) for i in self.tab_selection.toPlainText().split(',')]
            self.create_group.emit(self.group_name.currentText(), indices)
        except ValueError:
            self.state_display.append("Error: Invalid tab indices format")
    
    def refresh_state(self):
        """Update the state display"""
        state = []
        state.append("=== Tab Widget State ===")
        state.append(f"Total Tabs: {self.tab_widget.count()}")
        state.append(f"Current Index: {self.tab_widget.currentIndex()}")
        state.append(f"Hibernated Tabs: {list(self.tab_widget.hibernated_tabs.keys())}")
        state.append(f"Hibernation Pending: {list(self.tab_widget.hibernation_pending)}")
        state.append(f"Restoration Pending: {list(self.tab_widget.restoration_pending)}")
        state.append("\n=== Groups ===")
        for group, tabs in self.tab_widget.groups.items():
            state.append(f"Group '{group}': {[i for i in range(self.tab_widget.count()) if self.tab_widget.tab_groups.get(i) == group]}")
            if group in self.tab_widget.group_representatives:
                state.append(f"  Representative: {self.tab_widget.group_representatives[group]}")
        
        self.state_display.setPlainText('\n'.join(state)) 