from PyQt6.QtCore import QObject
import os
import json

class SettingsManager(QObject):
    """Manages application settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_dir = os.path.expanduser("~/.config/epy_explorer")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        
        # Default settings
        self.defaults = {
            'general': {
                'theme': 'System',
                'show_hidden_files': False,
                'show_preview_panel': True,
            },
            'launch': {
                'terminal_command': 'x-terminal-emulator',
                'auto_detect_projects': True,
            },
            'view': {
                'default_view_mode': 'list',
                'icon_size': 48,
                'grid_spacing': 10,
            },
            'preview': {
                'max_text_size': 1024 * 1024,  # 1MB
                'syntax_highlighting': True,
                'word_wrap': True,
            }
        }
        
        # Current settings
        self.settings = {}
        self.load_settings()
        
    def load_settings(self):
        """Load settings from config file"""
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)
                
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.settings = json.load(f)
            else:
                self.settings = self.defaults.copy()
                self.save_settings()
                
        except Exception as e:
            print(f"Error loading settings: {str(e)}")
            self.settings = self.defaults.copy()
            
    def save_settings(self):
        """Save settings to config file"""
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)
                
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
                
        except Exception as e:
            print(f"Error saving settings: {str(e)}")
            
    def get_setting(self, section, key, default=None):
        """Get a setting value"""
        try:
            return self.settings.get(section, {}).get(key, default)
        except:
            return default
            
    def set_setting(self, section, key, value):
        """Set a setting value"""
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        self.save_settings()
        
    def get_section(self, section):
        """Get all settings in a section"""
        return self.settings.get(section, {})
        
    def reset_section(self, section):
        """Reset a section to defaults"""
        if section in self.defaults:
            self.settings[section] = self.defaults[section].copy()
            self.save_settings()
            
    def reset_all(self):
        """Reset all settings to defaults"""
        self.settings = self.defaults.copy()
        self.save_settings() 