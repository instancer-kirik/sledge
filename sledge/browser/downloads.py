from PyQt6.QtCore import QObject, QFileInfo, QStandardPaths
from PyQt6.QtWidgets import QFileDialog
import os

class DownloadManager(QObject):
    """Manages browser downloads"""
    
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.downloads = {}
        
        # Create downloads directory
        self.download_dir = os.path.expanduser('~/.sledge/downloads')
        os.makedirs(self.download_dir, exist_ok=True)
        
    def handle_download(self, download):
        """Handle a new download request"""
        # Get suggested filename
        filename = QFileInfo(download.url().path()).fileName()
        if not filename:
            filename = 'download'
            
        # Get save path from user
        save_path, _ = QFileDialog.getSaveFileName(
            self.browser,
            "Save File",
            os.path.join(self.download_dir, filename)
        )
        
        if save_path:
            # Set download path and start download
            download.setPath(save_path)
            download.accept()
            
            # Store download for tracking
            self.downloads[download] = save_path
            
            # Connect signals
            download.finished.connect(lambda: self._download_finished(download))
            download.downloadProgress.connect(lambda r, t: self._update_progress(download, r, t))
            
    def _download_finished(self, download):
        """Handle download completion"""
        if download in self.downloads:
            save_path = self.downloads[download]
            # Clean up
            del self.downloads[download]
            
    def _update_progress(self, download, received, total):
        """Update download progress"""
        if download in self.downloads:
            progress = (received * 100) / total if total > 0 else 0
            # Could update UI here if needed 