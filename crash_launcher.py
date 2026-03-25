import traceback
import sys
import os

print(f"DEBUG: Current directory: {os.getcwd()}")
print(f"DEBUG: Python version: {sys.version}")

try:
    import Deimos
    print("DEBUG: Deimos imported successfully.")
except Exception:
    with open("crash_debug.txt", "w") as f:
        f.write(traceback.format_exc())
    print("CRASHED! Check crash_debug.txt")
