from sledge.browser.core import main
import sys

if __name__ == "__main__":
    print("Starting Sledge Browser...")
    print(f"Python path: {sys.path}")
    main()
    print("After main() call")  # This will help us see if main() is executing 