"""
GestureMaster Launcher
Simple launcher with all features
"""
import sys
import os

# Set working directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Set encoding
os.environ["PYTHONIOENCODING"] = "utf-8"

print("=" * 50)
print("  GestureMaster - Gesture Control Master")
print("=" * 50)

# Check dependencies
print("\nChecking dependencies...")

try:
    import cv2
    print(f"  OpenCV: {cv2.__version__}")
except ImportError:
    print("  ERROR: opencv-python not installed")
    print("  Run: pip install opencv-python")
    input("Press Enter to exit...")
    sys.exit(1)

try:
    import mediapipe as mp
    print(f"  MediaPipe: {mp.__version__}")
    if not hasattr(mp, 'solutions'):
        print("  ERROR: MediaPipe version incompatible!")
        print("  Run: pip install mediapipe==0.10.14")
        input("Press Enter to exit...")
        sys.exit(1)
except ImportError:
    print("  ERROR: mediapipe not installed")
    print("  Run: pip install mediapipe==0.10.14")
    input("Press Enter to exit...")
    sys.exit(1)

try:
    from PyQt6.QtWidgets import QApplication
    print("  PyQt6: OK")
except ImportError:
    print("  ERROR: PyQt6 not installed")
    print("  Run: pip install PyQt6")
    input("Press Enter to exit...")
    sys.exit(1)

try:
    import numpy as np
    print(f"  NumPy: {np.__version__}")
except ImportError:
    print("  ERROR: numpy not installed")
    print("  Run: pip install numpy")
    input("Press Enter to exit...")
    sys.exit(1)

try:
    from pynput.mouse import Controller
    print("  pynput: OK (mouse control available)")
except ImportError:
    print("  WARNING: pynput not installed (mouse control disabled)")
    print("  Run: pip install pynput")

print("\nAll dependencies OK!")
print("\nStarting GestureMaster...")

# Run main app
try:
    from main import GestureMasterApp
    app = GestureMasterApp()
    exit_code = app.run()
    app.cleanup()
    sys.exit(exit_code)
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
    input("\nPress Enter to exit...")
    sys.exit(1)
