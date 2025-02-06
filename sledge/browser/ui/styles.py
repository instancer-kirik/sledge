from PyQt6.QtGui import QColor

class BrowserTheme:
    """Browser theme management"""
    
    def __init__(self):
        # Nord theme colors
        self.bg_color = "#2e3440"
        self.fg_color = "#d8dee9"
        self.accent_color = "#88c0d0"
        self.border_color = "#434c5e"
        self.hover_color = "#3b4252"
        self.active_color = "#4c566a"
        
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
                border-bottom: 2px solid {self.accent_color};
            }}
            
            QTabBar::tab:hover {{
                background: {self.active_color};
            }}
            
            QStatusBar {{
                background: {self.bg_color};
                color: {self.fg_color};
                border-top: 1px solid {self.border_color};
            }}
            
            QProgressBar {{
                border: 1px solid {self.border_color};
                border-radius: 3px;
                text-align: center;
            }}
            
            QProgressBar::chunk {{
                background: {self.accent_color};
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
            
            QDockWidget {{
                titlebar-close-icon: url(close.png);
                titlebar-normal-icon: url(float.png);
            }}
            
            QDockWidget::title {{
                background: {self.hover_color};
                color: {self.fg_color};
                padding: 6px;
            }}
        """

def apply_dark_mode_js():
    """Get JavaScript for applying dark mode to web pages"""
    return """
        (function() {
            // Dark mode CSS
            const style = document.createElement('style');
            style.textContent = `
                @media (prefers-color-scheme: dark) {
                    :root {
                        color-scheme: dark;
                        forced-color-adjust: none;
                    }
                    
                    html {
                        background: #2e3440 !important;
                        color: #d8dee9 !important;
                    }
                    
                    body {
                        background: #2e3440 !important;
                        color: #d8dee9 !important;
                    }
                    
                    a {
                        color: #88c0d0 !important;
                    }
                    
                    input, textarea, select {
                        background: #3b4252 !important;
                        color: #d8dee9 !important;
                        border: 1px solid #434c5e !important;
                    }
                    
                    button {
                        background: #3b4252 !important;
                        color: #d8dee9 !important;
                        border: 1px solid #434c5e !important;
                    }
                    
                    button:hover {
                        background: #4c566a !important;
                        border-color: #88c0d0 !important;
                    }
                }
            `;
            document.head.appendChild(style);
            
            // Force dark mode
            document.documentElement.style.colorScheme = 'dark';
            
            // Monitor for dynamic content
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) {  // Element node
                            node.style.colorScheme = 'dark';
                            if (node.tagName === 'IFRAME') {
                                try {
                                    node.contentDocument.documentElement.style.colorScheme = 'dark';
                                } catch(e) {}
                            }
                        }
                    });
                });
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        })();
    """ 