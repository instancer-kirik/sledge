from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolBar, 
                              QComboBox, QSlider, QProgressBar, QLabel, QSplitter)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from .video_player import VideoPlayer
import re

class VideoTab(QWidget):
    """A tab specifically designed for video playback"""
    
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self._url = url if isinstance(url, QUrl) else QUrl(url)
        self.tab_widget = parent
        self.browser = parent.parent() if parent else None
        self.direct_video_url = None
        
        # Create layout first
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Create web view with proper parent
        self.web_view = QWebEngineView(self)
        self.layout.addWidget(self.web_view)
        
        # Initialize UI after web view
        self.init_ui()
        
        # Setup cleanup
        self.destroyed.connect(self._cleanup)
        
    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # Remove spacing between elements
        
        # Create splitter for webpage and video player
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter {
                background: #1a1a1a;
            }
            QSplitter::handle {
                background: #2e3440;
                width: 2px;
            }
        """)
        layout.addWidget(self.splitter)
        
        # Left side: Original webpage
        self.webpage_container = QWidget()
        self.webpage_container.setStyleSheet("background: #1a1a1a;")
        webpage_layout = QVBoxLayout(self.webpage_container)
        webpage_layout.setContentsMargins(0, 0, 0, 0)
        webpage_layout.setSpacing(0)
        
        # Create web view for the original page
        if self.browser and hasattr(self.browser, 'profile'):
            self.web_view.setPage(QWebEnginePage(self.browser.profile, self.web_view))
        webpage_layout.addWidget(self.web_view)
        
        # Right side: Video player
        self.player_container = QWidget()
        self.player_container.setStyleSheet("""
            QWidget {
                background: #1a1a1a;
                color: #d8dee9;
            }
            QLabel {
                color: #d8dee9;
                padding: 4px;
            }
            QProgressBar {
                background: #2e3440;
                border: none;
                height: 2px;
            }
            QProgressBar::chunk {
                background: #88c0d0;
            }
            QToolBar {
                background: #2e3440;
                border: none;
                padding: 4px;
            }
            QComboBox {
                background: #3b4252;
                color: #d8dee9;
                border: none;
                padding: 4px;
                min-width: 100px;
            }
            QComboBox:hover {
                background: #434c5e;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down.png);
            }
            QSlider {
                background: transparent;
            }
            QSlider::groove:horizontal {
                background: #2e3440;
                height: 4px;
            }
            QSlider::handle:horizontal {
                background: #88c0d0;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)
        player_layout = QVBoxLayout(self.player_container)
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(0)
        
        # Add status label
        self.status_label = QLabel("Loading video...")
        player_layout.addWidget(self.status_label)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        player_layout.addWidget(self.progress_bar)
        
        # Add control toolbar
        toolbar = QToolBar()
        player_layout.addWidget(toolbar)
        
        # Add quality selector
        self.quality_selector = QComboBox()
        self.quality_selector.addItems(['Auto', '1080p', '720p', '480p', '360p'])
        self.quality_selector.currentTextChanged.connect(self.change_quality)
        toolbar.addWidget(self.quality_selector)
        
        # Add volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(self.change_volume)
        toolbar.addWidget(self.volume_slider)
        
        # Add video player
        self.player = VideoPlayer(self)
        player_layout.addWidget(self.player)
        
        # Add containers to splitter
        self.splitter.addWidget(self.webpage_container)
        self.splitter.addWidget(self.player_container)
        
        # Set initial splitter sizes (50/50)
        self.splitter.setSizes([500, 500])
        
        # Load the webpage
        if any(domain in self._url.toString().lower() for domain in ['wcostream', 'wcofun', 'wco.tv']):
            # For WCO domains, we need to handle the page specially
            self.web_view.loadFinished.connect(self._check_for_video)
            self.web_view.loadProgress.connect(self.progress_bar.setValue)
            self.web_view.setUrl(self._url)
            self.status_label.setText("Loading webpage...")
            
            # Inject CSS to fix WCO page styling
            js = """
            var style = document.createElement('style');
            style.textContent = `
                body { background: #1a1a1a !important; color: #d8dee9 !important; }
                .video-js { background: #000 !important; }
                #video-content, #video-player { background: #000 !important; }
                .server-list a, .server-item { 
                    background: #2e3440 !important; 
                    color: #d8dee9 !important;
                    border: none !important;
                }
                .server-list a:hover, .server-item:hover {
                    background: #3b4252 !important;
                }
                .server-list a.active, .server-item.active {
                    background: #4c566a !important;
                    color: #88c0d0 !important;
                }
            `;
            document.head.appendChild(style);
            """
            self.web_view.page().runJavaScript(js)
        else:
            # Direct video URL
            self.webpage_container.hide()  # Hide webpage view for direct video URLs
            self.player.load_video(self._url.toString())
        
    def _check_for_video(self, success):
        """Check for video URL after page load"""
        if success and self.browser:
            # First try getting video URL from interceptor
            interceptor = getattr(self.browser, 'request_interceptor', None)
            if interceptor:
                video_url = interceptor.get_video_url()
                if video_url:
                    print(f"🎥 [VIDEO TAB] Found video URL from interceptor: {video_url}")
                    self.direct_video_url = video_url
                    self.status_label.setText("Video URL found, loading player...")
                    self.player.load_video(video_url)
                    return

            # If no URL found through interceptor, try handling WCO page structure
            js = """
            (function() {
                function findVideoSources() {
                    // Log what we're checking
                    console.log('🔍 Searching for video sources...');
                    
                    // Check for video elements
                    let videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        console.log('📹 Found video elements:', videos.length);
                        for (let video of videos) {
                            if (video.src) {
                                console.log('🎥 Found video source:', video.src);
                                return video.src;
                            }
                            // Check source elements
                            let sources = video.getElementsByTagName('source');
                            if (sources.length > 0) {
                                console.log('🎥 Found source elements:', sources.length);
                                return sources[0].src;
                            }
                        }
                    }
                    
                    // Check for iframes
                    let iframes = document.querySelectorAll('iframe');
                    console.log('🖼️ Found iframes:', iframes.length);
                    for (let iframe of iframes) {
                        if (iframe.src && (
                            iframe.src.includes('embed') || 
                            iframe.src.includes('video') ||
                            iframe.src.includes('player')
                        )) {
                            console.log('🎥 Found video iframe:', iframe.src);
                            return iframe.src;
                        }
                    }
                    
                    // Check for video containers
                    let containers = document.querySelectorAll('#video-content, #video-player, .video-player');
                    console.log('📦 Found video containers:', containers.length);
                    if (containers.length > 0) {
                        return 'found_container';
                    }
                    
                    // Check for server selection
                    let servers = document.querySelectorAll('.server-list a, .server-item');
                    console.log('🖥️ Found server options:', servers.length);
                    if (servers.length > 0) {
                        // Click first available server if not already selected
                        let activeServer = document.querySelector('.server-list a.active, .server-item.active');
                        if (!activeServer && servers[0]) {
                            console.log('🖱️ Clicking first server option');
                            servers[0].click();
                        }
                        
                        // Try to find and click play button
                        let playButton = document.querySelector('.play-video, .play-button, button[data-play]');
                        if (playButton) {
                            console.log('▶️ Clicking play button');
                            playButton.click();
                            return 'waiting_for_video';
                        }
                    }
                    
                    console.log('❌ No video sources found');
                    return null;
                }
                
                // Run the search
                return findVideoSources();
            })();
            """
            self.web_view.page().runJavaScript(js, self._handle_video_found)
        else:
            self.status_label.setText("Error loading video page")
            
    def _handle_video_found(self, result):
        """Handle found video URL or status"""
      
        if not result:
            self.status_label.setText("Could not find video - please select a server and click play")
            # Keep checking for video periodically
            QTimer.singleShot(2000, lambda: self._check_for_video(True))
            return
        print(f"🎥 [VIDEO TAB] JavaScript search result: {result}")
           
        if result == 'waiting_for_video':
            # Server/play button clicked, wait a bit and check again for video
            print("🎥 [VIDEO TAB] Waiting for video after clicking play...")
            self.status_label.setText("Waiting for video to load...")
            QTimer.singleShot(2000, lambda: self._check_for_video(True))
            return
            
        if result == 'found_container':
            # Found video container, wait for video to be inserted
            print("🎥 [VIDEO TAB] Found container, waiting for video...")
            self.status_label.setText("Waiting for video player...")
            QTimer.singleShot(1000, lambda: self._check_for_video(True))
            return
            
        # Got a URL - check if it's an embed page
        if 'embed' in result and 'video-js.php' in result:
            print(f"🎥 [VIDEO TAB] Found embed page, extracting video URL...")
            self.status_label.setText("Loading embed page...")
            
            # Extract video ID and file from the URL
            video_id = None
            video_file = None
            quality = "1080p"
            
            if "?" in result:
                params = result.split("?")[1].split("&")
                for param in params:
                    if "pid=" in param:
                        video_id = param.split("=")[1]
                    elif "file=" in param:
                        video_file = param.split("=")[1]
                    elif "fullhd=" in param and param.split("=")[1] == "1":
                        quality = "1080p"
            
            if video_id and video_file:
                # If it's an FLV file, construct CDN URL directly
                if '.flv' in video_file:
                    cdn_url = f"https://cdn.watchanimesub.net/getvid?evid={video_id}&quality={quality}"
                    print(f"🎥 [VIDEO TAB] Constructed CDN URL: {cdn_url}")
                    self.direct_video_url = cdn_url
                    self.status_label.setText("Video URL found, loading player...")
                    self.player.load_video(cdn_url)
                    return
            
            # Create a temporary web view to load the embed page
            temp_view = QWebEngineView()
            temp_view.setUrl(QUrl(result))
            
            # Extract video URL from embed page
            js = """
            (function() {
                return new Promise((resolve) => {
                    function findVideoUrl() {
                        // Log what we're checking
                        console.log('🔍 Searching for video URL in embed page...');
                        
                        // First check URL parameters
                        const params = new URLSearchParams(window.location.search);
                        const file = params.get('file');
                        const pid = params.get('pid');
                        if (file && pid) {
                            console.log('📁 Found file and pid parameters:', { file, pid });
                            // If it's an FLV file, construct CDN URL
                            if (file.includes('.flv')) {
                                const quality = params.get('fullhd') === '1' ? '1080p' : '720p';
                                const cdn_url = `https://cdn.watchanimesub.net/getvid?evid=${pid}&quality=${quality}`;
                                console.log('🎥 Constructed CDN URL:', cdn_url);
                                return resolve(cdn_url);
                            }
                        }
                        
                        // Wait for video element to be fully loaded
                        let attempts = 0;
                        function checkVideo() {
                            attempts++;
                            
                            // Check for VideoJS player first
                            if (window.videojs) {
                                const players = document.getElementsByClassName('video-js');
                                for (const player of players) {
                                    if (player.player) {
                                        const sources = player.player.currentSources();
                                        if (sources && sources.length > 0) {
                                            console.log('🎥 Found VideoJS sources:', sources);
                                            return resolve(sources[0].src);
                                        }
                                    }
                                }
                            }
                            
                            // Check for video elements
                            const videos = document.querySelectorAll('video');
                            for (const video of videos) {
                                // Check data-setup attribute
                                if (video.getAttribute('data-setup')) {
                                    try {
                                        const setup = JSON.parse(video.getAttribute('data-setup'));
                                        if (setup.sources && setup.sources.length > 0) {
                                            console.log('🎥 Found source in data-setup:', setup.sources[0].src);
                                            return resolve(setup.sources[0].src);
                                        }
                                    } catch (e) {
                                        console.log('Error parsing data-setup:', e);
                                    }
                                }
                                
                                // Check source elements
                                const sources = video.getElementsByTagName('source');
                                if (sources.length > 0) {
                                    console.log('🎥 Found source elements:', sources[0].src);
                                    return resolve(sources[0].src);
                                }
                                
                                // Check src attribute
                                if (video.src) {
                                    console.log('🎥 Found video source:', video.src);
                                    return resolve(video.src);
                                }
                            }
                            
                            // Check for video URL in page source
                            const scripts = document.getElementsByTagName('script');
                            for (const script of scripts) {
                                const text = script.textContent;
                                if (text) {
                                    // Look for common video URL patterns
                                    const matches = text.match(/['"]?(https?:\/\/[^'"]*\.(?:mp4|m3u8|webm|flv)(?:[^'"]*))['"]?/i);
                                    if (matches) {
                                        console.log('🎥 Found video URL in script:', matches[1]);
                                        return resolve(matches[1]);
                                    }
                                }
                            }
                            
                            // If we have file and pid but no video found, construct CDN URL as fallback
                            if (file && pid && attempts >= 10) {
                                const quality = params.get('fullhd') === '1' ? '1080p' : '720p';
                                const cdn_url = `https://cdn.watchanimesub.net/getvid?evid=${pid}&quality=${quality}`;
                                console.log('🎥 Using fallback CDN URL:', cdn_url);
                                return resolve(cdn_url);
                            }
                            
                            // Try again if not found and not exceeded max attempts
                            if (attempts < 10) {
                                setTimeout(checkVideo, 1000);
                            } else {
                                console.log('❌ Timeout waiting for video URL');
                                resolve(null);
                            }
                        }
                        
                        // Start checking
                        checkVideo();
                    }
                    
                    // Wait for page to be ready
                    if (document.readyState === 'complete') {
                        findVideoUrl();
                    } else {
                        window.addEventListener('load', findVideoUrl);
                    }
                });
            })();
            """
            
            def handle_embed_result(video_url):
                print(f"🎥 [VIDEO TAB] Extracted video URL from embed: {video_url}")
                if video_url:
                    self.direct_video_url = video_url
                    self.status_label.setText("Video URL found, loading player...")
                    self.player.load_video(video_url)
                else:
                    self.status_label.setText("Could not find video URL in embed page")
                    # Keep checking periodically
                    QTimer.singleShot(2000, lambda: self._check_for_video(True))
                temp_view.deleteLater()
            
            # Run the extraction after page loads
            temp_view.loadFinished.connect(lambda ok: 
                temp_view.page().runJavaScript(js, handle_embed_result) if ok else 
                handle_embed_result(None)
            )
            return
            
        # Got a direct video URL
        print(f"🎥 [VIDEO TAB] Found direct video URL: {result}")
        self.direct_video_url = result
        self.status_label.setText("Video URL found, loading player...")
        self.player.load_video(result)
        
    def change_quality(self, quality):
        """Change video quality"""
        if not self.direct_video_url:
            return
            
        if quality != 'Auto':
            # Extract the numeric value from the quality string
            height = int(quality.replace('p', ''))
            # Modify URL to request specific quality
            if '?' in self.direct_video_url:
                base_url = self.direct_video_url.split('?')[0]
                params = self.direct_video_url.split('?')[1]
                # Update or add quality parameter
                if 'quality=' in params:
                    params = re.sub(r'quality=[^&]*', f'quality={quality}', params)
                else:
                    params += f'&quality={quality}'
                new_url = f"{base_url}?{params}"
            else:
                new_url = f"{self.direct_video_url}?quality={quality}"
            # Reload video with new quality
            self.player.load_video(new_url)
        
    def change_volume(self, value):
        """Change video volume"""
        volume = value / 100.0
        self.player.set_volume(volume)
        
    def url(self):
        """Return the current URL for compatibility with tab widget"""
        return self._url 

    def _cleanup(self):
        """Handle proper cleanup of resources"""
        if hasattr(self, 'web_view') and self.web_view:
            self.web_view.stop()
            if self.web_view.page():
                self.web_view.page().deleteLater()
            self.web_view.deleteLater()
            self.web_view = None
            
    def closeEvent(self, event):
        """Handle cleanup when tab is closed"""
        self._cleanup()
        super().closeEvent(event) 