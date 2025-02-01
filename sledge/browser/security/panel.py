from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QCheckBox, QLabel

class SecurityPanel(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        layout = QVBoxLayout(self)
        
        # Security Mode Group
        mode_group = QGroupBox("Security Mode")
        mode_layout = QVBoxLayout()
        
        # Dev Mode Toggle
        self.dev_mode = QCheckBox("Developer Mode (Relaxed Security)")
        self.dev_mode.setChecked(self.settings.get('security', 'dev_mode'))
        self.dev_mode.stateChanged.connect(
            lambda state: self.settings.set('security', 'dev_mode', bool(state))
        )
        mode_layout.addWidget(self.dev_mode)
        
        # Warning Label
        warning_label = QLabel(
            "⚠️ Developer Mode disables certain security features.\n"
            "Only use during development!"
        )
        warning_label.setStyleSheet("color: #ebcb8b;")  # Warning yellow
        mode_layout.addWidget(warning_label)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Security Features Group
        features_group = QGroupBox("Security Features")
        features_layout = QVBoxLayout()
        
        # CORS Settings
        self.strict_cors = QCheckBox("Strict CORS Policy")
        self.strict_cors.setChecked(self.settings.get('security', 'strict_cors'))
        self.strict_cors.stateChanged.connect(
            lambda state: self.settings.set('security', 'strict_cors', bool(state))
        )
        features_layout.addWidget(self.strict_cors)
        
        # Mixed Content
        self.block_mixed = QCheckBox("Block Mixed Content")
        self.block_mixed.setChecked(self.settings.get('security', 'block_mixed_content'))
        self.block_mixed.stateChanged.connect(
            lambda state: self.settings.set('security', 'block_mixed_content', bool(state))
        )
        features_layout.addWidget(self.block_mixed)
        
        # Dangerous Ports
        self.block_ports = QCheckBox("Block Dangerous Ports")
        self.block_ports.setChecked(self.settings.get('security', 'block_dangerous_ports'))
        self.block_ports.stateChanged.connect(
            lambda state: self.settings.set('security', 'block_dangerous_ports', bool(state))
        )
        features_layout.addWidget(self.block_ports)
        
        # Dangerous Schemes
        self.block_schemes = QCheckBox("Block Dangerous URL Schemes")
        self.block_schemes.setChecked(self.settings.get('security', 'block_dangerous_schemes'))
        self.block_schemes.stateChanged.connect(
            lambda state: self.settings.set('security', 'block_dangerous_schemes', bool(state))
        )
        features_layout.addWidget(self.block_schemes)
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        # Status Indicator
        self.status_label = QLabel()
        self.update_status_label()
        layout.addWidget(self.status_label)
        
        # Connect dev mode to update status
        self.dev_mode.stateChanged.connect(self.update_status_label)
        
        layout.addStretch()
        
    def update_status_label(self):
        if self.dev_mode.isChecked():
            self.status_label.setText("🔓 Developer Mode Active - Security Features Relaxed")
            self.status_label.setStyleSheet("color: #bf616a;")  # Red for warning
        else:
            self.status_label.setText("🔒 Normal Security Mode - Full Protection Active")
            self.status_label.setStyleSheet("color: #a3be8c;")  # Green for secure 