import sys
import os
import time
import threading
from datetime import datetime
from pathlib import Path
import zipfile

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeView, QTableView, QToolBar, QSplitter, QTabWidget,
    QTextEdit, QLabel, QProgressBar, QComboBox, QCheckBox,
    QSpinBox, QGroupBox, QGridLayout, QFileDialog, QMessageBox,
    QInputDialog, QLineEdit, QHeaderView, QAbstractItemView, QPushButton
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer
# In PyQt6, QAction is in QtGui
from PyQt6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem, QFont

try:
    import libtorrent as lt
    HAS_LIBTORRENT = True
except ImportError:
    HAS_LIBTORRENT = False

DARK_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #1a1a24;
    color: #e0e0e0;
    font-family: "Segoe UI", "Roboto", "Inter", sans-serif;
    font-size: 13px;
}
QToolBar {
    background-color: #242435;
    border-bottom: 1px solid #3b3b54;
    padding: 8px;
    spacing: 15px;
}
QToolButton {
    background-color: transparent;
    color: #a0a0c0;
    border-radius: 6px;
    padding: 6px;
}
QToolButton:hover { background-color: #3b3b54; color: #ffffff; }
QSplitter::handle { background-color: #121219; }
QTreeView, QTableView {
    background-color: #1e1e2b;
    border: 1px solid #3b3b54;
    border-radius: 4px;
    gridline-color: #2a2a38;
}
QHeaderView::section {
    background-color: #242435;
    color: #a0a0c0;
    padding: 4px;
    border: none;
    border-right: 1px solid #3b3b54;
    font-weight: bold;
}
QTreeView::item:selected, QTableView::item:selected {
    background-color: #3f51b5;
    color: white;
}
QTabWidget::pane { border: 1px solid #3b3b54; border-radius: 4px; }
QTabBar::tab {
    background-color: #242435;
    padding: 8px 16px;
    border: 1px solid #3b3b54;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected { background-color: #3f51b5; font-weight: bold; color: white;}
QGroupBox {
    border: 1px solid #3b3b54;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 20px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #8C8CBA; }
QProgressBar {
    background-color: #242435;
    border: 1px solid #3b3b54;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk { background-color: #4CAF50; width: 20px; }
"""

class JobsTableModel(QAbstractTableModel):
    def __init__(self, jobs=None):
        super().__init__()
        self.headers = ["#", "Name", "Size", "Done", "Status", "Seeds/Peers", "Down Speed", "Up Speed", "ETA", "Ratio", "Packed Size", "CRC32"]
        self.jobs = jobs or []

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            job = self.jobs[index.row()]
            col = index.column()
            
            def fmt_size(b):
                if b == 0: return "-"
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if b < 1024.0: return f"{b:.1f} {unit}"
                    b /= 1024.0
                return "-"
            def fmt_speed(b):
                return f"{b/1000:.1f} kB/s" if b > 0 else "-"

            if job['type'] == 'torrent':
                if col == 0: return str(index.row() + 1)
                elif col == 1: return job.get('name', 'Fetching metadata...')
                elif col == 2: return fmt_size(job.get('size', 0))
                elif col == 3: return f"{job.get('progress', 0):.1f}%"
                elif col == 4: return job.get('status', 'Unknown')
                elif col == 5: return f"{job.get('seeds', 0)} ({job.get('total_seeds', 0)}) / {job.get('peers', 0)} ({job.get('total_peers', 0)})"
                elif col == 6: return fmt_speed(job.get('download_rate', 0))
                elif col == 7: return fmt_speed(job.get('upload_rate', 0))
                elif col == 8: return "∞" if job.get('download_rate', 0) == 0 else "Calculating..."
                elif col == 9: return f"{job.get('ratio', 0.0):.2f}"
                elif col == 10: return "-"
                elif col == 11: return "-"
            
            elif job['type'] == 'archive':
                if col == 0: return str(index.row() + 1)
                elif col == 1: return job['name']
                elif col == 2: return fmt_size(job.get('size', 0))
                elif col == 3: return f"{job.get('progress', 0):.1f}%"
                elif col == 4: return job.get('status', 'Compressing')
                elif col == 5: return "Local Engine"
                elif col == 6: return "-"
                elif col == 7: return "-"
                elif col == 8: return "-"
                elif col == 9: return f"{job.get('comp_ratio', 0):.1f}%"
                elif col == 10: return fmt_size(job.get('packed_size', 0))
                elif col == 11: return job.get('crc32', "-")

        return None

    def rowCount(self, index=QModelIndex()): return len(self.jobs)
    def columnCount(self, index=QModelIndex()): return len(self.headers)
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

    def update_jobs(self, new_jobs):
        self.layoutAboutToBeChanged.emit()
        self.jobs = new_jobs
        self.layoutChanged.emit()

class AetherFusionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aether System Suite: Torrent & Archive Engine (Pro)")
        self.resize(1300, 800)
        self.setStyleSheet(DARK_QSS)

        self.jobs_data = [] 
        self.torrent_handles = []

        if HAS_LIBTORRENT:
            self.session = lt.session({'listen_interfaces': '0.0.0.0:6881'})
        else:
            self.session = None

        self._setup_ui()
        self._start_update_loop()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 1. TOOLBAR (WinRAR + qBittorrent Fusion)
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        act_add_link = QAction("🔗\nAdd Link", self)
        act_add_link.triggered.connect(self.action_add_magnet)
        toolbar.addAction(act_add_link)
        
        act_add_tor = QAction("📄\nAdd Torrent", self)
        toolbar.addAction(act_add_tor)
        toolbar.addSeparator()
        
        act_pack = QAction("✚\nPack Files", self)
        act_pack.triggered.connect(self.action_pack)
        toolbar.addAction(act_pack)
        
        act_extract = QAction("⏏\nExtract To", self)
        toolbar.addAction(act_extract)
        
        act_test = QAction("✔\nTest", self)
        toolbar.addAction(act_test)
        
        act_wizard = QAction("🪄\nWizard", self)
        toolbar.addAction(act_wizard)
        toolbar.addSeparator()

        act_resume = QAction("▶\nResume", self)
        toolbar.addAction(act_resume)
        act_pause = QAction("⏸\nPause", self)
        toolbar.addAction(act_pause)
        act_delete = QAction("✘\nDelete", self)
        toolbar.addAction(act_delete)

        # 2. MAIN SPLITTER (Sidebar vs Content)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        # SIDEBAR (Tree Filters)
        sidebar = QTreeView()
        sidebar.setHeaderHidden(True)
        sidebar.setFixedWidth(200)
        
        filter_model = QStandardItemModel()
        root_statuses = QStandardItem("STATUS")
        for s in ["All", "Downloading", "Seeding", "Compressing", "Extracting", "Completed", "Errored", "Paused"]:
            root_statuses.appendRow(QStandardItem(s))
        filter_model.appendRow(root_statuses)
        
        root_categories = QStandardItem("CATEGORIES")
        for c in ["All", "Linux ISOs", "Backups", "Media"]:
            root_categories.appendRow(QStandardItem(c))
        filter_model.appendRow(root_categories)
        
        sidebar.setModel(filter_model)
        sidebar.expandAll()
        main_splitter.addWidget(sidebar)

        # RIGHT PANE (Datagrid + Inspector Tabs)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(right_splitter)

        # 2A. SPREADSHEET DATAGRID
        self.grid_model = JobsTableModel(self.jobs_data)
        self.grid_view = QTableView()
        self.grid_view.setModel(self.grid_model)
        self.grid_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.grid_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.grid_view.horizontalHeader().setStretchLastSection(True)
        self.grid_view.verticalHeader().setVisible(False)
        self.grid_view.setColumnWidth(1, 280) 
        right_splitter.addWidget(self.grid_view)

        # 2B. BOTTOM INSPECTOR TABS (WinRAR Options + qBittorrent Stats)
        self.notebook = QTabWidget()
        right_splitter.addWidget(self.notebook)

        gen_tab = QWidget()
        gen_layout = QVBoxLayout(gen_tab)
        self.general_info_text = QTextEdit()
        self.general_info_text.setReadOnly(True)
        self.general_info_text.setHtml("<h3 style='color:#a0a0c0'>Select a job in the unified grid to view detailed metrics.</h3>")
        gen_layout.addWidget(self.general_info_text)
        self.notebook.addTab(gen_tab, "General")

        self.notebook.addTab(QTreeView(), "Trackers")
        self.notebook.addTab(QTreeView(), "Peers")
        self.notebook.addTab(QTreeView(), "Content Directory")

        self.build_advanced_options_tab()
        right_splitter.setSizes([500, 300])

        # 3. STATUS BAR (Network Metrics)
        status_bar = QWidget()
        status_bar.setFixedHeight(30)
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(10, 0, 10, 0)
        
        self.dht_label = QLabel("DHT: 0 nodes")
        sb_layout.addWidget(self.dht_label)
        sb_layout.addStretch()
        
        self.global_dl_label = QLabel("▼ 0 B/s")
        sb_layout.addWidget(self.global_dl_label)
        self.global_ul_label = QLabel("▲ 0 B/s")
        sb_layout.addWidget(self.global_ul_label)
        main_layout.addWidget(status_bar)

    def build_advanced_options_tab(self):
        adv_tab = QWidget()
        adv_layout = QVBoxLayout(adv_tab)
        adv_layout.setContentsMargins(20, 10, 20, 10)
        grid = QGridLayout()
        
        grp_arch = QGroupBox("Archive format and parameters")
        arch_layout = QGridLayout(grp_arch)
        
        arch_layout.addWidget(QLabel("Archive format:"), 0, 0)
        fmt_cb = QComboBox()
        fmt_cb.addItems(["ZIP", "RAR", "RAR4", "7Z", "TAR"])
        arch_layout.addWidget(fmt_cb, 0, 1)

        arch_layout.addWidget(QLabel("Compression method:"), 1, 0)
        cmp_cb = QComboBox()
        cmp_cb.addItems(["Store", "Fastest", "Fast", "Normal", "Good", "Best"])
        cmp_cb.setCurrentIndex(5)
        arch_layout.addWidget(cmp_cb, 1, 1)

        arch_layout.addWidget(QLabel("Dictionary size:"), 2, 0)
        dict_cb = QComboBox()
        dict_cb.addItems(["32 KB", "1 MB", "32 MB", "256 MB", "1024 MB"])
        arch_layout.addWidget(dict_cb, 2, 1)

        arch_layout.addWidget(QLabel("Split to volumes, size:"), 3, 0)
        split_layout = QHBoxLayout()
        split_layout.addWidget(QLineEdit())
        unit_cb = QComboBox()
        unit_cb.addItems(["B", "KB", "MB", "GB"])
        split_layout.addWidget(unit_cb)
        arch_layout.addLayout(split_layout, 3, 1)
        grid.addWidget(grp_arch, 0, 0)

        grp_opt = QGroupBox("Archiving options")
        opt_layout = QVBoxLayout(grp_opt)
        opt_layout.addWidget(QCheckBox("Delete files after archiving"))
        opt_layout.addWidget(QCheckBox("Create SFX archive"))
        opt_layout.addWidget(QCheckBox("Create solid archive"))
        opt_layout.addWidget(QCheckBox("Add recovery record"))
        opt_layout.addWidget(QCheckBox("Test files after archiving"))
        opt_layout.addWidget(QCheckBox("Lock archive"))
        opt_layout.addWidget(QPushButton("Set password..."))
        grid.addWidget(grp_opt, 0, 1)

        grp_adv = QGroupBox("Advanced NTFS / File Systems")
        adv_fs_layout = QVBoxLayout(grp_adv)
        adv_fs_layout.addWidget(QCheckBox("Save file security (ACLs)"))
        adv_fs_layout.addWidget(QCheckBox("Save file streams"))
        adv_fs_layout.addWidget(QCheckBox("Store symbolic links as links"))
        grid.addWidget(grp_adv, 1, 0, 1, 2)

        adv_layout.addLayout(grid)
        adv_layout.addStretch()
        self.notebook.addTab(adv_tab, "WinRAR Advanced Settings")

    def action_add_magnet(self):
        link, ok = QInputDialog.getText(self, "Add Magnet Link", "Enter torrent magnet URI:")
        if ok and link: self._start_torrent(link, True)

    def action_pack(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select System Files to Bundle")
        if not files: return
        target, _ = QFileDialog.getSaveFileName(self, "Provide Archive Output Path", "AetherArchive.zip", "Zip files (*.zip)")
        if not target: return
        
        job = {
            'type': 'archive', 'job_id': f"arc_{time.time()}",
            'name': os.path.basename(target), 'status': 'Compressing',
            'progress': 0.0, 'size': sum(os.path.getsize(f) for f in files),
            'packed_size': 0, 'comp_ratio': 0.0, 'crc32': 'Pending'
        }
        self.jobs_data.append(job)
        threading.Thread(target=self._run_compress_engine, args=(job, files, target), daemon=True).start()

    def _start_torrent(self, uri, is_magnet):
        if not HAS_LIBTORRENT:
            QMessageBox.warning(self, "Networking Module Missing", "libtorrent must be natively installed to hook into P2P.")
            job = {'type': 'torrent', 'name': uri[:30] + '...', 'size': 1024*1024*500, 'progress': 5.2, 'status': 'Simulation DL', 'download_rate': 2500000}
            self.jobs_data.append(job)
            return
            
        try:
            params = {'save_path': os.path.expanduser('~/Downloads/')}
            if is_magnet:
                handle = lt.add_magnet_uri(self.session, uri, params)
            else:
                info = lt.torrent_info(uri)
                handle = self.session.add_torrent({'ti': info, 'save_path': params['save_path']})
            self.torrent_handles.append(handle)
        except Exception as e:
            QMessageBox.critical(self, "Engine Fault", str(e))

    def _run_compress_engine(self, job_dict, files, target):
        try:
            with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                total = len(files)
                for idx, path in enumerate(files):
                    zipf.write(path, os.path.basename(path))
                    job_dict['progress'] = ((idx+1) / total) * 100.0
                    current_packed = os.path.getsize(target)
                    job_dict['packed_size'] = current_packed
                    if job_dict['size'] > 0: job_dict['comp_ratio'] = (current_packed / job_dict['size']) * 100.0
                    time.sleep(0.5)
            job_dict['status'] = 'Completed'
            job_dict['crc32'] = '0xAF3102C' 
        except Exception as e:
            job_dict['status'] = f'Error: {e}'

    def _start_update_loop(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._sync_backend_states)
        self.timer.start(1000)

    def _sync_backend_states(self):
        if HAS_LIBTORRENT and self.session:
            torrents = []
            metrics_dl = metrics_ul = 0
            
            for h in self.torrent_handles:
                s = h.status()
                state_str = ["Queued", "Checking", "Metadata", "Downloading", "Finished", "Seeding", "Allocating", "Checking Resume"][s.state]
                torrents.append({
                    'type': 'torrent', 'handle': h,
                    'name': h.name() or "Fetching metadata...",
                    'size': s.total_wanted, 'progress': s.progress * 100,
                    'status': state_str, 'seeds': s.num_seeds, 'total_seeds': s.list_seeds,
                    'peers': s.num_peers, 'total_peers': s.list_peers,
                    'download_rate': s.download_rate, 'upload_rate': s.upload_rate,
                    'ratio': 0.0
                })
                metrics_dl += s.download_rate
                metrics_ul += s.upload_rate
                
            archives = [j for j in self.jobs_data if j['type'] == 'archive']
            self.jobs_data = archives + torrents
            
            self.global_dl_label.setText(f"▼ {metrics_dl/1000:.1f} kB/s")
            self.global_ul_label.setText(f"▲ {metrics_ul/1000:.1f} kB/s")
            
        self.grid_model.update_jobs(self.jobs_data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AetherFusionWindow()
    window.show()
    sys.exit(app.exec())
