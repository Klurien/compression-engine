import sys
import traceback
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

try:
    import main
except Exception as e:
    print("Error importing main.py:")
    traceback.print_exc()
    sys.exit(1)

def run_interaction_tests(window):
    print("[TEST] Window loaded. Executing UI actions...")
    try:
        # Simulate clicking buttons or methods
        window._start_torrent("magnet:?xt=urn:btih:3fae639ebaa2bc6e987b7a66b9cd9891e4a43b99", True)
        print("[TEST] Torrent simulation added.")
        
        job_dict = {'type': 'archive', 'size': 100}
        window._run_compress_engine(job_dict, [], "test.zip")
        print("[TEST] Archive simulation added.")
        
        print("[TEST] Syncing backend states...")
        window._sync_backend_states()
        print("[TEST] Sync complete.")
        
    except Exception as e:
        print("[ERROR] Exception during interaction:")
        traceback.print_exc()
    
    QTimer.singleShot(1000, QApplication.quit)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        window = main.AetherFusionWindow()
        QTimer.singleShot(500, lambda: run_interaction_tests(window))
        app.exec()
        print("[TEST] Execution completed smoothly.")
    except Exception as e:
        print("[ERROR] Exception during instantiation:")
        traceback.print_exc()
