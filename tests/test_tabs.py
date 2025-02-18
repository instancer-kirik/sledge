import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QUrl, QEvent
from PyQt6.QtGui import QKeyEvent, QMouseButton
from sledge.browser.tabs.widgets import TabWidget, TabBar

@pytest.fixture
def app():
    """Create QApplication instance"""
    return QApplication([])

@pytest.fixture
def tab_widget(app):
    """Create TabWidget instance"""
    widget = TabWidget()
    # Initialize required attributes
    widget.groups = {}
    widget.tab_groups = {}
    widget.group_representatives = {}
    return widget

def test_tab_groups(tab_widget):
    """Test basic tab group creation and management"""
    # Add some tabs
    for i in range(3):
        tab_widget.add_new_tab(QUrl(f"http://example{i+1}.com"))
    
    # Create a group
    tab_widget.create_group("test_group", [0, 1])
    
    # Test group creation
    assert tab_widget.tab_groups[0] == "test_group"
    assert tab_widget.tab_groups[1] == "test_group"
    assert 2 not in tab_widget.tab_groups
    
    # Test group representative
    assert tab_widget.group_representatives["test_group"] == 0

def test_group_preview(tab_widget, qtbot):
    """Test group preview functionality"""
    # Add some tabs
    for i in range(3):
        tab_widget.add_new_tab(QUrl(f"http://example{i+1}.com"))
    
    # Create a group
    tab_widget.create_group("test_group", [0, 1])
    
    # Show the widget (needed for geometry calculations)
    tab_widget.show()
    
    # Select the group representative tab
    tab_widget.tabBar().setCurrentIndex(0)
    
    # Press down arrow
    qtbot.keyClick(tab_widget.tabBar(), Qt.Key.Key_Down)
    
    # Check that preview is shown
    assert hasattr(tab_widget, 'preview_container')
    assert tab_widget.preview_container.isVisible()
    assert tab_widget.group_preview.count() == 2  # Should show both tabs in group
    
    # Click an item in the preview
    qtbot.mouseClick(
        tab_widget.group_preview.viewport(),
        Qt.MouseButton.LeftButton,
        pos=tab_widget.group_preview.visualItemRect(tab_widget.group_preview.item(1)).center()
    )
    
    # Check that the correct tab was selected
    assert tab_widget.currentIndex() == 1
    assert not tab_widget.preview_container.isVisible()  # Preview should be hidden 