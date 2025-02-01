from PyQt6.QtGui import QColor

class BrowserTheme:
    """Theme manager for the browser UI"""
    
    def __init__(self):
        self.current_theme = 'dark'
        self.themes = {
            'dark': {
                'background': '#1e1e1e',
                'foreground': '#cccccc',
                'accent': '#007acc',
                'border': '#2d2d2d',
                'toolbar_bg': '#252526',
                'input_bg': '#3c3c3c',
                'button_hover': '#404040',
                'tab_active': '#1e1e1e',
                'tab_inactive': '#2d2d2d'
            },
            'light': {
                'background': '#ffffff',
                'foreground': '#000000',
                'accent': '#0066cc',
                'border': '#e0e0e0',
                'toolbar_bg': '#f3f3f3',
                'input_bg': '#ffffff',
                'button_hover': '#e5e5e5',
                'tab_active': '#ffffff',
                'tab_inactive': '#f0f0f0'
            },
            'sepia': {
                'background': '#f4ecd8',
                'foreground': '#5b4636',
                'accent': '#8b4513',
                'border': '#d3c4b4',
                'toolbar_bg': '#e8e0d0',
                'input_bg': '#fff8f0',
                'button_hover': '#e0d5c5',
                'tab_active': '#f4ecd8',
                'tab_inactive': '#e8e0d0'
            },
            'nord': {
                'background': '#2e3440',
                'foreground': '#d8dee9',
                'accent': '#88c0d0',
                'border': '#3b4252',
                'toolbar_bg': '#3b4252',
                'input_bg': '#434c5e',
                'button_hover': '#4c566a',
                'tab_active': '#2e3440',
                'tab_inactive': '#3b4252'
            },
            'solarized': {
                'background': '#002b36',
                'foreground': '#839496',
                'accent': '#268bd2',
                'border': '#073642',
                'toolbar_bg': '#073642',
                'input_bg': '#094352',
                'button_hover': '#094352',
                'tab_active': '#002b36',
                'tab_inactive': '#073642'
            }
        }
        
        # Domain-specific styles for forcing dark mode
        self.domain_styles = {
            'news.ycombinator.com': {
                'mode': 'dark',
                'css': '''
                    /* Force dark mode on HN */
                    body, .fatitem, .comment, .commtext, .subtext, .yclinks, .pagetop {
                        background-color: var(--theme-background) !important;
                        color: var(--theme-foreground) !important;
                    }
                    
                    /* Tables and layout */
                    table, tr, td {
                        background-color: var(--theme-background) !important;
                    }
                    
                    /* Links */
                    a:link, a:visited {
                        color: var(--theme-accent) !important;
                    }
                    
                    /* Remove bright backgrounds */
                    * {
                        background-image: none !important;
                    }
                    
                    /* Input fields */
                    input, textarea {
                        background-color: var(--theme-input-bg) !important;
                        color: var(--theme-foreground) !important;
                        border: 1px solid var(--theme-border) !important;
                    }
                '''
            }
        }
        
    def set_theme(self, theme_name):
        """Set the current theme"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            
    def get_theme_colors(self):
        """Get the current theme's colors"""
        return self.themes[self.current_theme]
        
    def get_stylesheet(self):
        """Get the Qt stylesheet for the current theme"""
        colors = self.get_theme_colors()
        return f'''
            /* Main window */
            QMainWindow {{
                background-color: {colors['background']};
                color: {colors['foreground']};
            }}
            
            /* Tab widget */
            QTabWidget::pane {{
                border: 1px solid {colors['border']};
                background: {colors['background']};
            }}
            
            QTabWidget::tab-bar {{
                left: 0px;
            }}
            
            QTabBar::tab {{
                background: {colors['tab_inactive']};
                color: {colors['foreground']};
                padding: 8px 12px;
                border: 1px solid {colors['border']};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            
            QTabBar::tab:selected {{
                background: {colors['tab_active']};
                margin-bottom: -1px;
            }}
            
            QTabBar::tab:hover {{
                background: {colors['button_hover']};
            }}
            
            /* Splitter */
            QSplitter::handle {{
                background: {colors['border']};
            }}
            
            /* Status bar */
            QStatusBar {{
                background: {colors['toolbar_bg']};
                color: {colors['foreground']};
            }}
            
            /* Panels */
            QWidget#right_panel {{
                background: {colors['toolbar_bg']};
                border-left: 1px solid {colors['border']};
            }}
        '''
        
    def inject_style(self, url):
        """Inject style into a webpage"""
        # Get domain-specific style if available
        domain = url.host()
        domain_style = self.domain_styles.get(domain)
        
        # Force dark mode for specific domains
        if domain_style:
            mode = domain_style['mode']
            custom_css = domain_style['css']
        else:
            mode = self.current_theme
            custom_css = ''
            
        colors = self.themes[mode]
        
        # Base CSS with CSS variables
        base_css = f'''
            :root {{
                --theme-background: {colors['background']};
                --theme-foreground: {colors['foreground']};
                --theme-accent: {colors['accent']};
                --theme-border: {colors['border']};
                --theme-toolbar-bg: {colors['toolbar_bg']};
                --theme-input-bg: {colors['input_bg']};
                --theme-button-hover: {colors['button_hover']};
            }}
        '''
        
        # JavaScript to force theme colors
        js = '''
            function forceThemeColors(node) {
                if (!node) return;
                
                // Remove background-related attributes
                node.style.removeProperty('background-color');
                node.style.removeProperty('background-image');
                node.style.removeProperty('background');
                
                // Set theme colors
                node.style.setProperty('background-color', 'var(--theme-background)', 'important');
                node.style.setProperty('color', 'var(--theme-foreground)', 'important');
                
                // Process children recursively
                for (let child of node.children) {
                    forceThemeColors(child);
                }
                
                // Handle iframes
                if (node.tagName === 'IFRAME') {
                    try {
                        forceThemeColors(node.contentDocument.body);
                    } catch (e) {
                        // Cross-origin iframe, ignore
                    }
                }
            }
            
            // Initial application
            forceThemeColors(document.body);
            
            // Watch for changes
            const observer = new MutationObserver((mutations) => {
                for (let mutation of mutations) {
                    for (let node of mutation.addedNodes) {
                        if (node.nodeType === 1) { // Element node
                            forceThemeColors(node);
                        }
                    }
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        '''
        
        return base_css + custom_css, js

def apply_dark_mode_js():
    return """
    (function() {
        function applyDarkMode() {
            if (!document.documentElement) {
                setTimeout(applyDarkMode, 10);
                return;
            }

            const darkMode = {
                background: '#212121',
                backgroundAlt: '#2b2b2b',
                backgroundLight: '#333333',
                text: '#e0e0e0',
                textDim: '#999999',
                link: '#81a1c1',
                border: '#3b4252'
            };

            const style = document.createElement('style');
            style.id = 'sledge-dark-mode';
            style.textContent = `
                :root {
                    color-scheme: dark !important;
                }
                
                html, body {
                    background-color: ${darkMode.background} !important;
                    color: ${darkMode.text} !important;
                }
                
                /* Common containers */
                div, section, nav, article, aside {
                    background-color: ${darkMode.background} !important;
                }
                
                /* Iframes and embeds */
                iframe, embed, object {
                    background-color: ${darkMode.backgroundAlt} !important;
                }
                
                /* Advertisement containers */
                [class*="ad-"], [class*="advertisement"], [id*="ad-"], [id*="advertisement"],
                [class*="sponsor"], [id*="sponsor"] {
                    background-color: ${darkMode.backgroundAlt} !important;
                    color: ${darkMode.textDim} !important;
                }
                
                /* List items and alternating backgrounds */
                tr:nth-child(even), .alternate, .alt, li:nth-child(even) {
                    background-color: ${darkMode.backgroundAlt} !important;
                }
                
                /* Common UI elements */
                header, footer, .header, .footer, .toolbar, .navbar {
                    background-color: ${darkMode.backgroundLight} !important;
                }
                
                /* Links */
                a:link, a:active {
                    color: ${darkMode.link} !important;
                }
                
                /* Form elements */
                input, textarea, select, button {
                    background-color: ${darkMode.backgroundLight} !important;
                    color: ${darkMode.text} !important;
                    border: 1px solid ${darkMode.border} !important;
                }
                
                /* Site-specific fixes */
                /* TechCrunch */
                .advertisement-container, .ad-unit, .sponsored-content {
                    background-color: ${darkMode.backgroundAlt} !important;
                    padding: 10px !important;
                    border: 1px solid ${darkMode.border} !important;
                }
                
                /* HN */
                .itemlist tr:nth-child(odd) {
                    background-color: ${darkMode.background} !important;
                }
                .itemlist tr:nth-child(even) {
                    background-color: ${darkMode.backgroundAlt} !important;
                }
                .comment { color: ${darkMode.text} !important; }
                
                /* Reddit */
                .thing { background-color: ${darkMode.backgroundAlt} !important; }
                .entry { background-color: transparent !important; }
                
                /* Force dark images with light backgrounds */
                img {
                    opacity: 0.9;
                    filter: brightness(0.8) contrast(1.2);
                }
                
                /* Override any !important light backgrounds */
                [style*="background-color: rgb(255, 255, 255)"],
                [style*="background-color: white"],
                [style*="background-color: #fff"] {
                    background-color: ${darkMode.background} !important;
                }
            `;
            
            document.documentElement.appendChild(style);
            
            // Handle dynamically loaded content
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) { // Element node
                            const elements = node.querySelectorAll('*');
                            elements.forEach((el) => {
                                if (el.style.backgroundColor === 'rgb(255, 255, 255)' ||
                                    el.style.backgroundColor === 'white' ||
                                    el.style.backgroundColor === '#fff') {
                                    el.style.backgroundColor = darkMode.background;
                                }
                            });
                        }
                    });
                });
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }

        // Initial application
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', applyDarkMode);
        } else {
            applyDarkMode();
        }
    })();
    """

class StyleAdjuster:
    """Handles website style adjustments for better readability and accessibility"""
    
    def __init__(self):
        self.default_styles = {
            'dark': self._get_dark_mode_css(),
            'light': self._get_light_mode_css(),
            'sepia': self._get_sepia_mode_css(),
            'nord': self._get_nord_theme_css(),
            'solarized': self._get_solarized_theme_css(),
            'high_contrast': self._get_high_contrast_css(),
            'readable': self._get_readable_mode_css()
        }
        
        # Map of domains to their default style mode
        self.domain_styles = {
            'news.ycombinator.com': 'dark',  # Force dark mode for HN
        }

    def inject_style(self, page, mode='readable'):
        """Inject style adjustments into the page"""
        # Check if we should override the mode based on domain
        url = page.url().toString()
        for domain, default_mode in self.domain_styles.items():
            if domain in url:
                mode = default_mode
                break
                
        css = self.default_styles.get(mode, self.default_styles['readable'])
        
        js = f"""
        (function() {{
            function forceThemeColors(el) {{
                if (!el || !el.style) return;
                
                // Remove all background-related attributes
                ['bgcolor', 'background', 'background-color', 'color'].forEach(attr => {{
                    el.removeAttribute(attr);
                }});
                
                // Force theme colors
                el.style.setProperty('background', 'var(--bg-color)', 'important');
                el.style.setProperty('background-color', 'var(--bg-color)', 'important');
                el.style.setProperty('color', 'var(--text-color)', 'important');
                
                // Process children recursively
                Array.from(el.children).forEach(forceThemeColors);
            }}

            function applyStyles() {{
                // Remove existing style adjuster
                const existingStyle = document.getElementById('sledge-style-adjuster');
                if (existingStyle) {{
                    existingStyle.remove();
                }}
                
                // Create and inject new style
                const style = document.createElement('style');
                style.id = 'sledge-style-adjuster';
                style.textContent = `{css}`;
                style.setAttribute('data-priority', 'high');
                document.head.appendChild(style);
                
                // Force theme colors at root level
                document.documentElement.style.setProperty('color-scheme', 'dark', 'important');
                document.documentElement.style.setProperty('background-color', 'var(--bg-color)', 'important');
                document.documentElement.style.setProperty('color', 'var(--text-color)', 'important');
                
                // Force theme on body
                document.body.style.setProperty('background-color', 'var(--bg-color)', 'important');
                document.body.style.setProperty('color', 'var(--text-color)', 'important');
                
                // Process all elements with background colors
                document.querySelectorAll('[bgcolor], [style*="background"], [style*="color"]').forEach(forceThemeColors);
                
                // Special handling for HN's main table
                const mainTable = document.querySelector('table[bgcolor="#f6f6ef"]');
                if (mainTable) {{
                    const processNode = (node) => {{
                        if (node.nodeType === 1) {{ // Element node
                            forceThemeColors(node);
                            // Force process all descendants
                            const walker = document.createTreeWalker(
                                node, 
                                NodeFilter.SHOW_ELEMENT,
                                null,
                                false
                            );
                            let currentNode;
                            while (currentNode = walker.nextNode()) {{
                                forceThemeColors(currentNode);
                            }}
                        }}
                    }};
                    processNode(mainTable);
                }}
                
                // Force dark mode on iframes
                document.querySelectorAll('iframe').forEach(iframe => {{
                    try {{
                        forceThemeColors(iframe.contentDocument.body);
                    }} catch (e) {{}}
                }});
            }}

            // Initial application
            applyStyles();
            
            // Re-apply multiple times to catch dynamic content
            [100, 500, 1000, 2000].forEach(delay => {{
                setTimeout(applyStyles, delay);
            }});
            
            // Monitor for dynamic content
            const observer = new MutationObserver(() => {{
                requestAnimationFrame(applyStyles);
            }});
            
            observer.observe(document.body, {{
                childList: true,
                subtree: true,
                attributes: true,
                characterData: true,
                attributeFilter: ['bgcolor', 'style', 'class', 'id']
            }});
        }})();
        """
        
        page.runJavaScript(js)
    
    def _get_dark_mode_css(self):
        """Get dark mode CSS adjustments"""
        return """
            :root {
                --bg-color: #1a1a1a !important;
                --text-color: #e0e0e0 !important;
                --link-color: #88c0d0 !important;
                --heading-color: #d8dee9 !important;
                --border-color: #3b4252 !important;
                --header-bg: #2e3440 !important;
                --layer2-bg: #242424 !important;
                color-scheme: dark !important;
            }
            
            html, body {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
            }
            
            /* Global background override */
            *:not(a):not(input):not(textarea):not(select):not(button) {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
            }
            
            /* HN specific elements */
            table, tr, td, #hnmain, .itemlist, center, .title, 
            .comment, .fatitem, .pagetop, .comment-tree, [bgcolor],
            [style*="background"], .hnuser, .subtext, .sitebit,
            .yclinks, .athing, .comhead, .commtext, .score,
            tbody, thead, tfoot, body > center > table {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
                border-color: var(--border-color) !important;
            }
            
            /* Links */
            a, .subtext a, .sitebit a, .hnuser, .age a, .hnpast a {
                color: var(--link-color) !important;
                text-decoration: none !important;
            }
            
            a:hover {
                text-decoration: underline !important;
            }
            
            /* Comment backgrounds */
            .comment-tree .comment:nth-child(even) {
                background-color: var(--layer2-bg) !important;
            }
            
            /* Force dark mode on frames */
            iframe {
                background-color: var(--bg-color) !important;
            }
            
            /* HN header */
            td[bgcolor="#ff6600"] {
                background-color: var(--header-bg) !important;
            }
        """
    
    def _get_light_mode_css(self):
        """Get light mode CSS adjustments"""
        return """
            /* Base light theme */
            :root {
                --bg-color: #ffffff;
                --text-color: #2e3440;
                --link-color: #5e81ac;
                --heading-color: #2e3440;
                --border-color: #d8dee9;
            }
            
            /* Basic elements */
            body {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
                line-height: 1.6 !important;
            }
            
            /* Text and headings */
            h1, h2, h3, h4, h5, h6 {
                color: var(--heading-color) !important;
            }
            
            a {
                color: var(--link-color) !important;
            }
            
            /* Form elements */
            input, textarea, select {
                background-color: #f8f9fb !important;
                color: var(--text-color) !important;
                border: 1px solid var(--border-color) !important;
            }
        """
    
    def _get_readable_mode_css(self):
        """Get readable mode CSS adjustments"""
        return """
            /* Readable mode */
            body {
                font-size: 18px !important;
                line-height: 1.8 !important;
                font-family: system-ui, -apple-system, BlinkMacSystemFont, 
                           'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 
                           'Open Sans', 'Helvetica Neue', sans-serif !important;
                max-width: 800px !important;
                margin: 0 auto !important;
                padding: 20px !important;
            }
            
            /* Improve text readability */
            p {
                margin-bottom: 1.5em !important;
            }
            
            /* Adjust heading sizes */
            h1 { font-size: 2.5em !important; }
            h2 { font-size: 2em !important; }
            h3 { font-size: 1.75em !important; }
            h4 { font-size: 1.5em !important; }
            
            /* Improve link visibility */
            a {
                text-decoration: underline !important;
                text-underline-offset: 2px !important;
            }
            
            /* Better list readability */
            ul, ol {
                padding-left: 2em !important;
                margin-bottom: 1.5em !important;
            }
            
            li {
                margin-bottom: 0.5em !important;
            }
            
            /* Improve code readability */
            pre, code {
                font-family: 'Fira Code', 'Consolas', monospace !important;
                padding: 0.2em 0.4em !important;
                border-radius: 3px !important;
            }
            
            /* Remove distracting elements */
            .ad, .advertisement, .social-share, .newsletter-signup {
                display: none !important;
            }
        """
    
    def _get_high_contrast_css(self):
        """Get high contrast mode CSS adjustments"""
        return """
            /* High contrast mode */
            :root {
                --bg-color: #000000;
                --text-color: #ffffff;
                --link-color: #ffff00;
                --heading-color: #ffffff;
                --border-color: #ffffff;
            }
            
            /* Basic elements */
            body {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
                font-size: 20px !important;
                line-height: 1.8 !important;
            }
            
            /* Increase contrast for text */
            p, div, span {
                color: var(--text-color) !important;
            }
            
            /* Make links stand out */
            a {
                color: var(--link-color) !important;
                text-decoration: underline !important;
                font-weight: bold !important;
            }
            
            /* Clear backgrounds */
            * {
                background-image: none !important;
                text-shadow: none !important;
            }
            
            /* Strong borders */
            input, textarea, select, button {
                border: 2px solid var(--border-color) !important;
            }
            
            /* Focus indicators */
            *:focus {
                outline: 3px solid var(--link-color) !important;
                outline-offset: 2px !important;
            }
        """

    def _get_sepia_mode_css(self):
        """Get sepia mode CSS adjustments"""
        return """
            /* Sepia theme with maximum specificity */
            :root, :root[data-theme], html, body, #hnmain {
                --bg-color: #f4ecd8 !important;
                --text-color: #5c4b37 !important;
                --link-color: #b4713d !important;
                --heading-color: #7c593b !important;
                --border-color: #d3c4a9 !important;
                --header-bg: #e4d5b7 !important;
                --layer2-bg: #ebe3d0 !important;
                background: var(--bg-color) !important;
                color: var(--text-color) !important;
            }
            
            /* Global override for sepia */
            html body *:not(a):not(input):not(textarea):not(select):not(button) {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
            }
            
            /* HN specific elements in sepia */
            html body table,
            html body center,
            html body #hnmain,
            html body .itemlist,
            html body .fatitem,
            html body .comment-tree,
            html body .comment,
            html body tr,
            html body td,
            html body tbody {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
                border-color: var(--border-color) !important;
            }
            
            /* Links in sepia */
            html body a,
            html body .subtext a,
            html body .sitebit a,
            html body .hnuser {
                color: var(--link-color) !important;
                text-decoration: none !important;
            }
            
            html body a:hover {
                text-decoration: underline !important;
            }
            
            /* Comment backgrounds in sepia */
            html body .comment-tree .comment:nth-child(even) {
                background-color: var(--layer2-bg) !important;
            }
        """

    def _get_nord_theme_css(self):
        """Get Nord theme CSS adjustments"""
        return """
            /* Nord theme with maximum specificity */
            :root, :root[data-theme], html, body, #hnmain {
                --bg-color: #2e3440 !important;
                --text-color: #d8dee9 !important;
                --link-color: #88c0d0 !important;
                --heading-color: #eceff4 !important;
                --border-color: #4c566a !important;
                --header-bg: #3b4252 !important;
                --layer2-bg: #3b4252 !important;
                background: var(--bg-color) !important;
                color: var(--text-color) !important;
            }
            
            /* Global override for nord */
            html body *:not(a):not(input):not(textarea):not(select):not(button) {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
            }
            
            /* HN specific elements in nord */
            html body table,
            html body center,
            html body #hnmain,
            html body .itemlist,
            html body .fatitem,
            html body .comment-tree,
            html body .comment {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
                border-color: var(--border-color) !important;
            }
            
            /* Links in nord */
            html body a,
            html body .subtext a,
            html body .sitebit a,
            html body .hnuser {
                color: var(--link-color) !important;
                text-decoration: none !important;
            }
            
            /* Comment backgrounds in nord */
            html body .comment-tree .comment:nth-child(even) {
                background-color: var(--layer2-bg) !important;
            }
        """

    def _get_solarized_theme_css(self):
        """Get Solarized theme CSS adjustments"""
        return """
            /* Solarized dark theme with maximum specificity */
            :root, :root[data-theme], html, body, #hnmain {
                --bg-color: #002b36 !important;
                --text-color: #839496 !important;
                --link-color: #268bd2 !important;
                --heading-color: #93a1a1 !important;
                --border-color: #073642 !important;
                --header-bg: #073642 !important;
                --layer2-bg: #073642 !important;
                background: var(--bg-color) !important;
                color: var(--text-color) !important;
            }
            
            /* Global override for solarized */
            html body *:not(a):not(input):not(textarea):not(select):not(button) {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
            }
            
            /* HN specific elements in solarized */
            html body table,
            html body center,
            html body #hnmain,
            html body .itemlist,
            html body .fatitem,
            html body .comment-tree,
            html body .comment {
                background-color: var(--bg-color) !important;
                color: var(--text-color) !important;
                border-color: var(--border-color) !important;
            }
            
            /* Links in solarized */
            html body a,
            html body .subtext a,
            html body .sitebit a,
            html body .hnuser {
                color: var(--link-color) !important;
                text-decoration: none !important;
            }
            
            /* Comment backgrounds in solarized */
            html body .comment-tree .comment:nth-child(even) {
                background-color: var(--layer2-bg) !important;
            }
        """

