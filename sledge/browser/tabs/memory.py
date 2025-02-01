from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QCheckBox
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from datetime import datetime
import psutil
from .states import TabState

class TabMemoryManager:
    def __init__(self, tab_widget):
        self.tab_widget = tab_widget
        self.states = {}  # Track tab states
        self.memory_timer = QTimer()
        self.memory_timer.timeout.connect(self.check_memory_usage)
        self.memory_timer.start(60000)  # Check every minute
        self.memory_threshold = 75  # Percentage of system memory
        self.last_accessed = {}  # Track when tabs were last accessed
        self.frozen_tabs = set()  # Track frozen tabs
        self.memory_usage_history = []  # Track memory usage over time

    def check_memory_usage(self):
        """Check system memory usage and manage tabs intelligently"""
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        system_memory = psutil.virtual_memory().percent
        
        self.memory_usage_history.append(current_memory)
        if len(self.memory_usage_history) > 10:
            self.memory_usage_history.pop(0)
        
        # Calculate memory trend
        memory_increasing = (len(self.memory_usage_history) > 1 and 
                           self.memory_usage_history[-1] > self.memory_usage_history[0])
        
        if system_memory > self.memory_threshold or memory_increasing:
            self.optimize_memory_usage()

    def optimize_memory_usage(self):
        """Optimize memory usage using various strategies"""
        current_index = self.tab_widget.currentIndex()
        
        for i in range(self.tab_widget.count()):
            if i == current_index:
                continue
                
            tab = self.tab_widget.widget(i)
            if not hasattr(tab, 'page'):
                continue
                
            # Check if tab should be managed - Fixed reference
            group = self.tab_widget.tab_groups.get(i)
            if group and self.tab_widget.groups[group].keep_active:
                continue
            
            # Calculate tab priority
            priority = self.calculate_tab_priority(i)
            
            if priority < 0.3:
                self.hibernate_tab(i)
            elif priority < 0.6:
                self.snooze_tab(i)
            else:
                self.freeze_tab(i)

    def calculate_tab_priority(self, index):
        """Calculate tab priority based on various factors"""
        current_time = datetime.now()
        last_access = self.last_accessed.get(index, datetime.min)
        time_factor = min(1.0, (current_time - last_access).seconds / 3600)
        
        # Check if tab is in view
        visibility_factor = 1.0 if self.tab_widget.tabBar().isTabVisible(index) else 0.5
        
        # Check if tab is in an active group
        group = self.tab_widget.tab_groups.get(index)
        group_factor = 1.0
        if group:
            group_obj = self.tab_widget.groups[group]
            if group_obj.keep_active:
                group_factor = 2.0
        
        return (1.0 - time_factor) * visibility_factor * group_factor

    def freeze_tab(self, index):
        """Freeze tab to reduce memory usage but keep it quickly accessible"""
        if index not in self.frozen_tabs:
            tab = self.tab_widget.widget(index)
            if hasattr(tab, 'page'):
                tab.page().setLifecycleState(
                    QWebEnginePage.LifecycleState.Frozen
                )
                self.frozen_tabs.add(index)
                self.states[index] = TabState.FROZEN
                self.tab_widget.tabBar.update_tab_appearance(index)

    def hibernate_tab(self, index):
        """Hibernate tab by storing its state and freeing memory"""
        tab = self.tab_widget.widget(index)
        if hasattr(tab, 'page'):
            # Store tab data
            url = tab.url().toString()
            title = self.tab_widget.tabText(index)
            scroll_pos = tab.page().scrollPosition()
            
            # Create minimal placeholder
            placeholder = QWidget()
            placeholder.url = lambda: QUrl(url)
            placeholder.stored_data = {
                'url': url,
                'title': title,
                'scroll': scroll_pos
            }
            
            # Replace tab
            self.tab_widget.removeTab(index)
            self.tab_widget.insertTab(index, placeholder, title)
            self.states[index] = TabState.HIBERNATED
            self.tab_widget.tabBar().update_tab_appearance(index)
            
            # Add click handler to wake up tab
            placeholder.mousePressEvent = lambda e: self.wake_tab(index)

    def wake_tab(self, index):
        """Wake up a hibernated or snoozed tab"""
        tab = self.tab_widget.widget(index)
        
        if self.states.get(index) == TabState.HIBERNATED:
            # Restore hibernated tab
            stored_data = getattr(tab, 'stored_data', None)
            if stored_data:
                # Create new web view
                web_view = QWebEngineView()
                web_view.setPage(QWebEnginePage(
                    self.tab_widget.parent().profile, web_view))
                
                # Set dark mode before loading
                self.tab_widget.parent().inject_dark_mode_to_tab(web_view)
                
                # Load URL and restore state
                web_view.setUrl(QUrl(stored_data['url']))
                web_view.loadFinished.connect(
                    lambda ok: self.restore_tab_state(web_view, stored_data) if ok else None
                )
                
                # Replace placeholder with real tab
                self.tab_widget.removeTab(index)
                self.tab_widget.insertTab(index, web_view, stored_data['title'])
                self.states[index] = TabState.ACTIVE
                
                # Make sure the tab is selected after restoration
                self.tab_widget.setCurrentIndex(index)
                
        elif self.states.get(index) in [TabState.SNOOZED, TabState.FROZEN]:
            if hasattr(tab, 'page'):
                tab.page().setLifecycleState(
                    QWebEnginePage.LifecycleState.Active
                )
                self.frozen_tabs.discard(index)
                self.states[index] = TabState.ACTIVE
        
        self.last_accessed[index] = datetime.now()
        self.tab_widget.tabBar().update_tab_appearance(index)

    def restore_tab_state(self, web_view, stored_data):
        """Restore tab state after loading"""
        if 'scroll' in stored_data:
            web_view.page().setScrollPosition(stored_data['scroll'])
        # Add any other state restoration here

    def snooze_tab(self, index):
        """Snooze a tab to reduce memory usage"""
        if self.states.get(index) == TabState.ACTIVE:
            tab = self.tab_widget.widget(index)
            if hasattr(tab, 'url'):
                self.states[index] = TabState.SNOOZED
                tab.page().setLifecycleState(tab.page().LifecycleState.Frozen)
                self.tab_widget.tabBar.update_tab_appearance(index)

class TabMemoryIndicator(QWidget):
    """Widget showing memory usage and tab states"""
    def __init__(self, tab_widget, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.setFixedHeight(30)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        
        # Memory usage indicator
        self.memory_label = QLabel()
        layout.addWidget(self.memory_label)
        
        # Tab state counts
        self.state_label = QLabel()
        layout.addWidget(self.state_label)
        
        # Auto-manage toggle
        self.auto_manage = QCheckBox("Auto-manage memory")
        self.auto_manage.setChecked(True)
        self.auto_manage.toggled.connect(self.toggle_auto_manage)
        layout.addWidget(self.auto_manage)
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_indicators)
        self.update_timer.start(1000)  # Update every second
        
    def update_indicators(self):
        """Update memory usage and tab state indicators"""
        memory = psutil.Process().memory_info().rss / 1024 / 1024
        system_memory = psutil.virtual_memory().percent
        
        self.memory_label.setText(
            f"Memory: {memory:.1f}MB ({system_memory}% system)"
        )
        
        # Count tab states - Fixed reference
        states = self.tab_widget.memory_manager.states
        counts = {
            "Active": sum(1 for s in states.values() if s == TabState.ACTIVE),
            "Snoozed": sum(1 for s in states.values() if s == TabState.SNOOZED),
            "Frozen": sum(1 for s in states.values() if s == TabState.FROZEN),
            "Hibernated": sum(1 for s in states.values() if s == TabState.HIBERNATED)
        }
        
        self.state_label.setText(
            " | ".join(f"{k}: {v}" for k, v in counts.items())
        )
        
        # Update color based on memory pressure
        if system_memory > 85:
            self.setStyleSheet("background-color: #662222")
        elif system_memory > 75:
            self.setStyleSheet("background-color: #666622")
        else:
            self.setStyleSheet("")
            
    def toggle_auto_manage(self):
        """Toggle automatic memory management"""
        if self.auto_manage:
            self.auto_manage = False
            self.memory_timer.stop()
            print("Memory management disabled")
        else:
            self.auto_manage = True
            self.memory_timer.start()
            print("Memory management enabled")
            
        # Update UI
        if hasattr(self.tab_widget, '_tab_bar'):
            self.tab_widget._tab_bar.update_tab_appearance()
