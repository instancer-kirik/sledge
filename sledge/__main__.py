import sys
import os

# Add the parent directory of sledge to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sledge.browser.core import SledgeBrowser, main

def run():
    # Set QT_LOGGING_RULES to disable noisy warnings
    os.environ["QT_LOGGING_RULES"] = "*=false"
    # Set program name for Qt
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
    os.environ["PROGRAM_NAME"] = "sledge"
    
    # Ensure argv[0] is the program name
    if getattr(sys, 'frozen', False):
        program_name = sys.executable
    else:
        program_name = os.path.abspath(sys.argv[0] if sys.argv else __file__)
    
    sys.argv = [program_name]
    
    # If URL is provided as argument, append it
    if len(sys.argv) > 1:
        return main(sys.argv)
    return main([program_name, "about:blank"])

if __name__ == '__main__':
    sys.exit(run()) 