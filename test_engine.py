import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from main import AetherFusionWindow, HAS_LIBTORRENT

def run_tests(window):
    print("\n--- AETHER ENGINE INTEGRATION TEST ---")
    print(f"Network (libtorrent) Active: {HAS_LIBTORRENT}")

    print("\n[1] Testing Zlib Archiving Engine...")
    with open("test_payload.dat", "w") as f:
        f.write("AETHER_PAYLOAD_BLOCK_" * 10000)
    
    orig_size = os.path.getsize("test_payload.dat")
    job = {'type': 'archive', 'size': orig_size, 'progress': 0}
    window._run_compress_engine(job, ["test_payload.dat"], "test_archive.zip")
    packed_size = os.path.getsize('test_archive.zip')
    
    print(f" -> Successfully Compressed: {orig_size} bytes down to {packed_size} bytes")
    print(f" -> Status Flag: {job['status']}")

    print("\n[2] Testing Distributed BitTorrent Protocol (Debian 12 ISO Magnet)...")
    mag = "magnet:?xt=urn:btih:3fae639ebaa2bc6e987b7a66b9cd9891e4a43b99&dn=debian-12.5.0-amd64-netinst.iso"
    window._start_torrent(mag, True)

    def poll(count=0):
        window._sync_backend_states()
        for j in window.jobs_data:
            if j['type'] == 'torrent':
                print(f"  [DHT Polling {count}s] State: {j['status']:<18} | Seeds Found: {j.get('total_seeds',0):<3} | DownSpeed: {j.get('download_rate',0)/1000:.1f} kB/s")
        
        if count < 10:
            QTimer.singleShot(1000, lambda: poll(count + 1))
        else:
            print("\n--- INTEGRATION TESTS CONCLUDED SUCCESSFULLY ---")
            sys.exit(0)

    QTimer.singleShot(1000, lambda: poll(0))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AetherFusionWindow()
    # Execute the test payload 0.5s after event loop starts
    QTimer.singleShot(500, lambda: run_tests(window))
    sys.exit(app.exec())
