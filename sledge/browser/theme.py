from PyQt6.QtGui import QColor
from PyQt6.QtCore import QUrl

class Theme:
    def __init__(self):
        # Theme colors
        self.themes = {
            'dark': {
                'bg_color': "#2e3440",
                'fg_color': "#d8dee9",
                'accent_color': "#88c0d0",
                'border_color': "#434c5e",
                'hover_color': "#3b4252",
                'active_color': "#4c566a"
            },
            'light': {
                'bg_color': "#ffffff",
                'fg_color': "#2e3440",
                'accent_color': "#5e81ac",
                'border_color': "#d8dee9",
                'hover_color': "#eceff4",
                'active_color': "#e5e9f0"
            },
            'sepia': {
                'bg_color': "#f4ecd8",
                'fg_color': "#5c4b37",
                'accent_color': "#8b6b4c",
                'border_color': "#e4d5b7",
                'hover_color': "#efe6d4",
                'active_color': "#e6dcc8"
            },
            'nord': {
                'bg_color': "#2e3440",
                'fg_color': "#d8dee9",
                'accent_color': "#88c0d0",
                'border_color': "#434c5e",
                'hover_color': "#3b4252",
                'active_color': "#4c566a"
            },
            'solarized': {
                'bg_color': "#002b36",
                'fg_color': "#839496",
                'accent_color': "#2aa198",
                'border_color': "#073642",
                'hover_color': "#073642",
                'active_color': "#586e75"
            }
        }
        
        # Current theme
        self.current_theme = 'dark'
        self.force_dark = True
        
        # Apply initial theme
        self._apply_theme()
        
        # Style settings
        self.font_size = 14
        self.line_height = 1.5
        self.max_width = 800
        self.hide_images = False
        self.hide_ads = True
        self.justify_text = False
        self.use_dyslexic_font = False
        
    def _apply_theme(self):
        """Apply the current theme colors"""
        theme = self.themes[self.current_theme]
        for key, value in theme.items():
            setattr(self, key, value)
            
    def set_theme(self, theme_name):
        """Set the current theme"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            self._apply_theme()
        
    def get_stylesheet(self):
        """Get the application stylesheet"""
        return f"""
            QMainWindow {{
                background: {self.bg_color};
                color: {self.fg_color};
            }}
            
            QWidget {{
                background: {self.bg_color};
                color: {self.fg_color};
            }}
            
            QToolBar {{
                background: {self.bg_color};
                border: none;
                spacing: 4px;
                padding: 4px;
            }}
            
            QToolBar QToolButton {{
                background: {self.hover_color};
                border: none;
                border-radius: 3px;
                color: {self.fg_color};
                padding: 4px;
            }}
            
            QToolBar QToolButton:hover {{
                background: {self.active_color};
            }}
            
            QLineEdit {{
                background: {self.hover_color};
                color: {self.fg_color};
                border: 1px solid {self.border_color};
                border-radius: 3px;
                padding: 4px 8px;
                selection-background-color: {self.accent_color};
            }}
            
            QLineEdit:focus {{
                border: 1px solid {self.accent_color};
            }}
            
            QStatusBar {{
                background: {self.bg_color};
                color: {self.fg_color};
                border-top: 1px solid {self.border_color};
            }}
            
            QTabWidget::pane {{
                border: none;
                background: {self.bg_color};
            }}
            
            QTabBar::tab {{
                background: {self.bg_color};
                color: {self.fg_color};
                padding: 8px 20px;
                border: none;
                min-width: 150px;
                max-width: 300px;
            }}
            
            QTabBar::tab:selected {{
                background: {self.hover_color};
                color: {self.accent_color};
                border-bottom: 2px solid {self.accent_color};
            }}
            
            QTabBar::tab:hover {{
                background: {self.active_color};
            }}
            
            QMenu {{
                background: {self.bg_color};
                color: {self.fg_color};
                border: 1px solid {self.border_color};
            }}
            
            QMenu::item {{
                padding: 4px 20px;
            }}
            
            QMenu::item:selected {{
                background: {self.hover_color};
            }}
            
            QScrollBar {{
                background: {self.bg_color};
                width: 12px;
                height: 12px;
            }}
            
            QScrollBar::handle {{
                background: {self.hover_color};
                border-radius: 6px;
                min-height: 24px;
            }}
            
            QScrollBar::handle:hover {{
                background: {self.active_color};
            }}
            
            QScrollBar::add-line, QScrollBar::sub-line {{
                background: none;
            }}
            
            QDialog {{
                background: {self.bg_color};
                color: {self.fg_color};
            }}
            
            QPushButton {{
                background: {self.hover_color};
                color: {self.fg_color};
                border: 1px solid {self.border_color};
                border-radius: 3px;
                padding: 4px 12px;
            }}
            
            QPushButton:hover {{
                background: {self.active_color};
                border: 1px solid {self.accent_color};
            }}
            
            QComboBox {{
                background: {self.hover_color};
                color: {self.fg_color};
                border: 1px solid {self.border_color};
                border-radius: 3px;
                padding: 4px 8px;
            }}
            
            QComboBox:hover {{
                border: 1px solid {self.accent_color};
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                width: 0;
            }}
            
            QProgressBar {{
                border: 1px solid {self.border_color};
                border-radius: 3px;
                text-align: center;
            }}
            
            QProgressBar::chunk {{
                background: {self.accent_color};
            }}
        """
        
    def apply_to_window(self, window):
        """Apply theme to a window"""
        window.setStyleSheet(self.get_stylesheet())
        
    def inject_style(self, url):
        """Get CSS and JavaScript to inject into web pages"""
        # Don't inject styles for certain URLs
        if url.scheme() in ("about", "chrome", "qrc"):
            return "", ""
            
        # Base CSS for dark mode
        css = f"""
            :root {{
                color-scheme: dark;
                
                --bg-color: {self.bg_color};
                --fg-color: {self.fg_color};
                --accent-color: {self.accent_color};
                --border-color: {self.border_color};
                --hover-color: {self.hover_color};
                
                --font-size: {self.font_size}px;
                --line-height: {self.line_height};
                --max-width: {self.max_width}px;
            }}
            
            @media (prefers-color-scheme: dark) {{
                html {{
                    background: var(--bg-color) !important;
                    color: var(--fg-color) !important;
                }}
                
                body {{
                    background: var(--bg-color) !important;
                    color: var(--fg-color) !important;
                    font-size: var(--font-size) !important;
                    line-height: var(--line-height) !important;
                    max-width: var(--max-width) !important;
                    margin: 0 auto !important;
                    padding: 20px !important;
                }}
                
                a {{
                    color: var(--accent-color) !important;
                }}
                
                input, textarea, select {{
                    background: var(--hover-color) !important;
                    color: var(--fg-color) !important;
                    border: 1px solid var(--border-color) !important;
                    border-radius: 3px !important;
                }}
                
                button {{
                    background: var(--hover-color) !important;
                    color: var(--fg-color) !important;
                    border: 1px solid var(--border-color) !important;
                    border-radius: 3px !important;
                    padding: 4px 12px !important;
                }}
                
                button:hover {{
                    background: var(--active-color) !important;
                    border-color: var(--accent-color) !important;
                }}
            }}
        """
        
        # Add optional styles
        if self.hide_images:
            css += """
                img { display: none !important; }
            """
            
        if self.hide_ads:
            css += """
                [class*="ad"], [id*="ad"],
                [class*="advertisement"], [id*="advertisement"],
                [class*="banner"], [id*="banner"] {
                    display: none !important;
                }
            """
            
        if self.justify_text:
            css += """
                p { text-align: justify !important; }
            """
            
        if self.use_dyslexic_font:
            css += """
                @import url('https://fonts.googleapis.com/css2?family=OpenDyslexic&display=swap');
                * { font-family: 'OpenDyslexic', sans-serif !important; }
            """
            
        # JavaScript to apply styles
        js = f"""
            (function() {{
                // Remove existing style element if any
                let style = document.getElementById('sledge-theme');
                if (style) {{
                    style.remove();
                }}
                
                // Create and add new style element
                style = document.createElement('style');
                style.id = 'sledge-theme';
                style.textContent = `{css}`;
                document.head.appendChild(style);
                
                // Force dark mode
                document.documentElement.style.colorScheme = 'dark';
                
                // Handle dynamic content
                const observer = new MutationObserver(function(mutations) {{
                    mutations.forEach(function(mutation) {{
                        if (mutation.addedNodes.length) {{
                            mutation.addedNodes.forEach(function(node) {{
                                if (node.nodeType === 1) {{  // Element node
                                    // Re-apply styles to new content
                                    node.style.colorScheme = 'dark';
                                    if (node.tagName === 'IFRAME') {{
                                        try {{
                                            node.contentDocument.documentElement.style.colorScheme = 'dark';
                                        }} catch(e) {{}}
                                    }}
                                }}
                            }});
                        }}
                    }});
                }});
                
                observer.observe(document.body, {{
                    childList: true,
                    subtree: true
                }});
            }})();
        """
        
        return css, js
        
    def update_style_settings(self, settings):
        """Update style settings"""
        self.font_size = settings.get('font_size', self.font_size)
        self.line_height = settings.get('line_height', self.line_height)
        self.max_width = settings.get('max_width', self.max_width)
        self.hide_images = settings.get('hide_images', self.hide_images)
        self.hide_ads = settings.get('hide_ads', self.hide_ads)
        self.justify_text = settings.get('justify_text', self.justify_text)
        self.use_dyslexic_font = settings.get('use_dyslexic_font', self.use_dyslexic_font)