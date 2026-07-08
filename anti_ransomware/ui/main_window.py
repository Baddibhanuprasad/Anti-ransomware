from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFileDialog, QTextEdit, QLabel, 
                             QProgressBar, QTableWidget, QTableWidgetItem,
                             QTabWidget, QGroupBox, QCheckBox, QSplitter,
                             QListWidget, QMessageBox, QHeaderView, QInputDialog,
                             QMenuBar, QAction, QStatusBar, QDialog, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMetaObject, Q_ARG, QTimer
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QPalette
import os
import sys
import time
import subprocess
from scanners.signature_scanner import SignatureScanner
from scanners.heuristic_scanner import HeuristicScanner
from scanners.entropy_analyzer import EntropyAnalyzer
from scanners.deception_scanner import DeceptionScanner
from scanners.process_monitor import ProcessMonitor
from scanners.smart_scanner import SmartScanner
from scanners.comprehensive_scanner import ComprehensiveScanner
from scanners.usb_monitor import USBMonitor, USBScanner
from sandbox.sandbox_manager import SandboxManager
from ui.sandbox_dialog import SandboxDialog

class USBNotificationDialog(QDialog):
    """Big, prominent USB detection notification dialog"""
    def __init__(self, drive_path, volume_name, total_space, parent=None):
        super().__init__(parent)
        self.drive_path = drive_path
        self.volume_name = volume_name
        self.total_space = total_space
        self.result = "cancel"
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #1a237e, stop:0.5 #0d47a1, stop:1 #1a237e);
                border: 3px solid #4CAF50;
                border-radius: 15px;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                padding: 15px 30px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                border: none;
            }
            QPushButton#sandbox_btn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #4CAF50, stop:1 #2E7D32);
                color: white;
                font-size: 18px;
            }
            QPushButton#sandbox_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #66BB6A, stop:1 #388E3C);
            }
            QPushButton#open_btn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #2196F3, stop:1 #1565C0);
                color: white;
                font-size: 16px;
            }
            QPushButton#open_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #42A5F5, stop:1 #1976D2);
            }
            QPushButton#cancel_btn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #f44336, stop:1 #c62828);
                color: white;
                font-size: 14px;
            }
            QPushButton#cancel_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #ef5350, stop:1 #d32f2f);
            }
        """)
        
        self.setFixedSize(600, 450)
        self.center_on_screen()
        self.init_ui()
        
        # Auto-close timer (60 seconds)
        QTimer.singleShot(60000, self.close)
    
    def center_on_screen(self):
        """Center the dialog on screen"""
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header with icon
        header_layout = QHBoxLayout()
        
        # USB Icon (using emoji for simplicity)
        icon_label = QLabel("🔌")
        icon_label.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("USB DRIVE DETECTED!")
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #4CAF50;
            text-shadow: 0 0 10px rgba(76, 175, 80, 0.5);
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(255,255,255,0.3); max-height: 2px;")
        layout.addWidget(line)
        
        # Drive Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)
        
        drive_label = QLabel(f"📂 Drive: {self.drive_path}")
        drive_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        info_layout.addWidget(drive_label)
        
        volume_label = QLabel(f"💿 Volume: {self.volume_name}")
        volume_label.setStyleSheet("font-size: 18px;")
        info_layout.addWidget(volume_label)
        
        space_label = QLabel(f"💾 Total Space: {self.total_space}")
        space_label.setStyleSheet("font-size: 18px;")
        info_layout.addWidget(space_label)
        
        # Security warning
        warning_label = QLabel("⚠️ USB drives can contain malware and ransomware!")
        warning_label.setStyleSheet("""
            font-size: 16px;
            color: #FFC107;
            background-color: rgba(255, 193, 7, 0.2);
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #FFC107;
        """)
        warning_label.setWordWrap(True)
        info_layout.addWidget(warning_label)
        
        layout.addLayout(info_layout)
        
        # Add spacer
        layout.addStretch()
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.sandbox_btn = QPushButton("🏖️ Open in Sandbox (Secure)")
        self.sandbox_btn.setObjectName("sandbox_btn")
        self.sandbox_btn.clicked.connect(self.on_sandbox)
        button_layout.addWidget(self.sandbox_btn)
        
        self.open_btn = QPushButton("📂 Open Normally")
        self.open_btn.setObjectName("open_btn")
        self.open_btn.clicked.connect(self.on_open)
        button_layout.addWidget(self.open_btn)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.on_cancel)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Info text
        info_text = QLabel("🔒 Sandbox opens USB in isolated environment • Protects your system")
        info_text.setStyleSheet("""
            font-size: 12px;
            color: rgba(255,255,255,0.7);
            text-align: center;
        """)
        info_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_text)
    
    def on_sandbox(self):
        self.result = "sandbox"
        self.accept()
    
    def on_open(self):
        self.result = "open"
        self.accept()
    
    def on_cancel(self):
        self.result = "cancel"
        self.reject()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.on_cancel()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.on_sandbox()

class ScanThread(QThread):
    progress_update = pyqtSignal(int)
    log_update = pyqtSignal(str)
    scan_complete = pyqtSignal(dict)
    
    def __init__(self, file_path, scan_methods):
        super().__init__()
        self.file_path = file_path
        self.scan_methods = scan_methods
        self.results = {}
        
    def run(self):
        total_steps = len(self.scan_methods) + 2
        current_step = 0
        
        # 1. Run smart scanner
        self.log_update.emit("Running intelligent behavior analysis...")
        try:
            smart_scanner = SmartScanner()
            smart_results = smart_scanner.scan_file(self.file_path)
            self.results["Smart Behavior Scanner"] = smart_results
        except Exception as e:
            self.results["Smart Behavior Scanner"] = {"error": str(e)}
        current_step += 1
        self.progress_update.emit(int((current_step / total_steps) * 100))
        self.log_update.emit("Intelligent behavior analysis completed")
        
        # 2. Run other scanners
        for method in self.scan_methods:
            method_name = method.__class__.__name__
            self.log_update.emit(f"Starting {method_name}...")
            
            try:
                if method_name == "SignatureScanner":
                    result = method.scan_file(self.file_path)
                elif method_name == "HeuristicScanner":
                    result = method.scan_file(self.file_path)
                elif method_name == "EntropyAnalyzer":
                    result = method.analyze_file(self.file_path)
                elif method_name == "DeceptionScanner":
                    result = method.scan_with_canary(self.file_path)
                else:
                    result = {"error": "Unknown scanner"}
            except Exception as e:
                result = {"error": f"Scan error: {str(e)}"}
            
            self.results[method_name] = result
            current_step += 1
            progress = int((current_step / total_steps) * 100)
            self.progress_update.emit(progress)
            self.log_update.emit(f"Completed {method_name}")
        
        # 3. Run comprehensive analysis
        self.log_update.emit("Running comprehensive analysis...")
        try:
            comprehensive = ComprehensiveScanner()
            comprehensive_result = comprehensive.analyze(self.file_path, self.results)
            self.results["Comprehensive Analysis"] = comprehensive_result
        except Exception as e:
            self.results["Comprehensive Analysis"] = {"error": str(e)}
        self.progress_update.emit(100)
        self.log_update.emit("Comprehensive analysis completed")
        
        self.scan_complete.emit(self.results)

class AntiRansomwareUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_path = None
        self.scan_thread = None
        
        # Initialize scanners
        self.signature_scanner = SignatureScanner()
        self.heuristic_scanner = HeuristicScanner()
        self.entropy_analyzer = EntropyAnalyzer()
        self.deception_scanner = DeceptionScanner()
        self.process_monitor = ProcessMonitor()
        
        # Initialize USB monitor and scanner
        self.usb_monitor = USBMonitor()
        self.usb_scanner = USBScanner()
        
        # Initialize Sandbox manager
        self.sandbox_manager = SandboxManager()
        
        # Initialize UI
        self.init_ui()
        
        # Start process monitor
        self.process_monitor.start_monitoring()
        
        # Start USB monitoring with direct callback
        self.usb_monitor.start_monitoring(callback=self.on_usb_detected)
        
        # Add menus
        self.create_menus()
        
        # Log startup
        self.log_startup()
    
    def init_ui(self):
        """Initialize the main UI"""
        self.setWindowTitle("🛡️ Anti-Ransomware Protection System")
        self.setGeometry(100, 100, 1300, 850)
        self.setMinimumSize(1000, 700)
        
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
            QPushButton:pressed {
                opacity: 0.6;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #4CAF50;
                color: white;
            }
            QTabBar::tab:hover {
                background: #e0e0e0;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                alternate-background-color: #f9f9f9;
            }
            QTableWidget::item:selected {
                background: #4CAF50;
                color: white;
            }
            QHeaderView::section {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border: none;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background: #4CAF50;
                color: white;
            }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                  stop:0 #4CAF50, stop:1 #8BC34A);
                border-radius: 5px;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QStatusBar {
                background: #f0f0f0;
                padding: 5px;
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # ========== TOP CONTROLS ==========
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        # File selection
        self.file_label = QLabel("📂 No file selected")
        self.file_label.setStyleSheet("border: 1px solid #ccc; padding: 8px; background: #f8f8f8; border-radius: 4px;")
        self.file_label.setMinimumWidth(350)
        controls_layout.addWidget(self.file_label)
        
        self.select_btn = QPushButton("📁 Select File")
        self.select_btn.clicked.connect(self.select_file)
        self.select_btn.setStyleSheet("background: #2196F3; color: white;")
        controls_layout.addWidget(self.select_btn)
        
        self.scan_btn = QPushButton("🔍 Scan File")
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setEnabled(False)
        self.scan_btn.setStyleSheet("background: #4CAF50; color: white;")
        controls_layout.addWidget(self.scan_btn)
        
        self.sandbox_btn = QPushButton("🏖️ Open in Sandbox")
        self.sandbox_btn.clicked.connect(lambda: self.open_in_sandbox())
        self.sandbox_btn.setEnabled(False)
        self.sandbox_btn.setStyleSheet("background: #FF9800; color: white;")
        controls_layout.addWidget(self.sandbox_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop Scan")
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background: #f44336; color: white;")
        controls_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(controls_layout)
        
        # ========== SCAN OPTIONS ==========
        options_group = QGroupBox("🔧 Scan Options")
        options_layout = QHBoxLayout()
        
        self.signature_check = QCheckBox("🔍 Signature Detection")
        self.signature_check.setChecked(True)
        options_layout.addWidget(self.signature_check)
        
        self.heuristic_check = QCheckBox("🧠 Heuristic/Behavioral")
        self.heuristic_check.setChecked(True)
        options_layout.addWidget(self.heuristic_check)
        
        self.entropy_check = QCheckBox("📊 Entropy Analysis")
        self.entropy_check.setChecked(True)
        options_layout.addWidget(self.entropy_check)
        
        self.deception_check = QCheckBox("🪤 Deception (Canary Files)")
        self.deception_check.setChecked(True)
        options_layout.addWidget(self.deception_check)
        
        options_layout.addStretch()
        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)
        
        # ========== PROGRESS BAR ==========
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)
        
        # ========== TAB WIDGET ==========
        self.tab_widget = QTabWidget()
        
        # ----- Log Tab -----
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        
        log_controls = QHBoxLayout()
        self.clear_log_btn = QPushButton("🗑️ Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.clear_log_btn.setStyleSheet("background: #9E9E9E; color: white;")
        log_controls.addWidget(self.clear_log_btn)
        log_controls.addStretch()
        log_layout.addLayout(log_controls)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("background: #1e1e1e; color: #d4d4d4; border-radius: 4px;")
        log_layout.addWidget(self.log_text)
        self.tab_widget.addTab(self.log_tab, "📋 Scan Log")
        
        # ----- Results Tab -----
        self.results_tab = QWidget()
        results_layout = QVBoxLayout(self.results_tab)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Detection Method", "Status", "Details"])
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.results_table.setAlternatingRowColors(True)
        results_layout.addWidget(self.results_table)
        self.tab_widget.addTab(self.results_tab, "📊 Scan Results")
        
        # ----- Detailed Results Tab -----
        self.details_tab = QWidget()
        details_layout = QVBoxLayout(self.details_tab)
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", 10))
        self.details_text.setStyleSheet("background: #1e1e1e; color: #d4d4d4; border-radius: 4px;")
        details_layout.addWidget(self.details_text)
        self.tab_widget.addTab(self.details_tab, "📄 Detailed Analysis")
        
        # ----- USB Tab -----
        self.usb_tab = QWidget()
        usb_layout = QVBoxLayout(self.usb_tab)
        
        # USB controls
        usb_controls = QHBoxLayout()
        
        self.scan_usb_btn = QPushButton("🔍 Scan USB Drive")
        self.scan_usb_btn.clicked.connect(self.scan_usb_drive_menu)
        self.scan_usb_btn.setStyleSheet("background: #2196F3; color: white;")
        usb_controls.addWidget(self.scan_usb_btn)
        
        self.scan_all_usb_btn = QPushButton("🔍 Scan All USB Drives")
        self.scan_all_usb_btn.clicked.connect(self.scan_all_usb_drives)
        self.scan_all_usb_btn.setStyleSheet("background: #2196F3; color: white;")
        usb_controls.addWidget(self.scan_all_usb_btn)
        
        self.refresh_usb_btn = QPushButton("🔄 Refresh USB List")
        self.refresh_usb_btn.clicked.connect(self.refresh_usb_list)
        self.refresh_usb_btn.setStyleSheet("background: #9E9E9E; color: white;")
        usb_controls.addWidget(self.refresh_usb_btn)
        
        self.test_usb_btn = QPushButton("🧪 Test USB Detection")
        self.test_usb_btn.clicked.connect(self.test_usb_detection)
        self.test_usb_btn.setStyleSheet("background: #FF9800; color: white;")
        usb_controls.addWidget(self.test_usb_btn)
        
        usb_controls.addStretch()
        usb_layout.addLayout(usb_controls)
        
        # USB list and details
        usb_splitter = QSplitter(Qt.Vertical)
        
        self.usb_list = QListWidget()
        usb_splitter.addWidget(self.usb_list)
        
        self.usb_details = QTextEdit()
        self.usb_details.setReadOnly(True)
        self.usb_details.setMaximumHeight(150)
        self.usb_details.setFont(QFont("Consolas", 10))
        usb_splitter.addWidget(self.usb_details)
        
        usb_layout.addWidget(usb_splitter)
        self.tab_widget.addTab(self.usb_tab, "💾 USB Drives")
        
        # ----- Sandbox Tab -----
        self.sandbox_tab = QWidget()
        sandbox_layout = QVBoxLayout(self.sandbox_tab)
        
        sandbox_info_group = QGroupBox("🏖️ Sandbox Status")
        sandbox_info_layout = QVBoxLayout()
        
        self.sandbox_status_label = QLabel("⏳ Checking Sandboxie-Plus...")
        self.sandbox_status_label.setFont(QFont("Arial", 11))
        sandbox_info_layout.addWidget(self.sandbox_status_label)
        
        self.sandbox_path_label = QLabel("Path: Not found")
        sandbox_info_layout.addWidget(self.sandbox_path_label)
        
        self.sandbox_processes_label = QLabel("Processes: 0")
        sandbox_info_layout.addWidget(self.sandbox_processes_label)
        
        sandbox_info_group.setLayout(sandbox_info_layout)
        sandbox_layout.addWidget(sandbox_info_group)
        
        # Sandbox controls
        sandbox_controls = QHBoxLayout()
        
        self.open_sandbox_btn = QPushButton("🏖️ Open in Sandbox")
        self.open_sandbox_btn.clicked.connect(lambda: self.open_in_sandbox())
        self.open_sandbox_btn.setStyleSheet("background: #4CAF50; color: white;")
        sandbox_controls.addWidget(self.open_sandbox_btn)
        
        self.clean_sandbox_btn = QPushButton("🧹 Clean Sandbox")
        self.clean_sandbox_btn.clicked.connect(self.clean_sandbox)
        self.clean_sandbox_btn.setStyleSheet("background: #f44336; color: white;")
        sandbox_controls.addWidget(self.clean_sandbox_btn)
        
        self.emergency_kill_btn = QPushButton("🚨 Emergency Kill")
        self.emergency_kill_btn.clicked.connect(self.emergency_kill)
        self.emergency_kill_btn.setStyleSheet("background: #d32f2f; color: white; font-weight: bold;")
        sandbox_controls.addWidget(self.emergency_kill_btn)
        
        sandbox_controls.addStretch()
        sandbox_layout.addLayout(sandbox_controls)
        
        # Sandbox log
        sandbox_log_group = QGroupBox("📋 Sandbox Log")
        sandbox_log_layout = QVBoxLayout()
        self.sandbox_log_text = QTextEdit()
        self.sandbox_log_text.setReadOnly(True)
        self.sandbox_log_text.setFont(QFont("Consolas", 10))
        self.sandbox_log_text.setStyleSheet("background: #1e1e1e; color: #d4d4d4; border-radius: 4px;")
        sandbox_log_layout.addWidget(self.sandbox_log_text)
        sandbox_log_group.setLayout(sandbox_log_layout)
        sandbox_layout.addWidget(sandbox_log_group)
        
        self.tab_widget.addTab(self.sandbox_tab, "🏖️ Sandbox")
        
        # ----- About Tab -----
        self.about_tab = QWidget()
        about_layout = QVBoxLayout(self.about_tab)
        
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <h1>🛡️ Anti-Ransomware Protection System</h1>
        <p><b>Version:</b> 2.0</p>
        <p><b>Description:</b> Advanced anti-ransomware solution with multiple detection layers</p>
        <br>
        <h2>Features:</h2>
        <ul>
            <li>🔍 Signature-based detection</li>
            <li>🧠 Heuristic/Behavioral analysis</li>
            <li>📊 Entropy analysis</li>
            <li>🪤 Deception techniques (Canary files)</li>
            <li>💾 USB drive scanning with auto-detection</li>
            <li>🏖️ Sandbox environment (Sandboxie-Plus integration)</li>
            <li>📈 Real-time process monitoring</li>
            <li>🧬 Smart behavior analysis</li>
            <li>🚨 Emergency Kill - Kill lock screen & sandbox</li>
            <li>🔓 Auto USB detection with big notification</li>
        </ul>
        <br>
        <p><b>Created by:</b> Security Team</p>
        <p><b>License:</b> MIT</p>
        """)
        about_text.setStyleSheet("background: #f5f5f5; padding: 20px; border-radius: 4px;")
        about_layout.addWidget(about_text)
        self.tab_widget.addTab(self.about_tab, "ℹ️ About")
        
        main_layout.addWidget(self.tab_widget)
        
        # ========== STATUS BAR ==========
        self.statusBar().showMessage("✅ Ready")
        
        # Refresh USB list and sandbox status on startup
        self.refresh_usb_list()
        self.update_sandbox_status()
    
    def create_menus(self):
        """Create menu bar"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #f5f5f5;
                border-bottom: 1px solid #ddd;
            }
            QMenuBar::item {
                padding: 5px 10px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
                color: white;
            }
        """)
        
        # File Menu
        file_menu = menubar.addMenu("📁 File")
        
        open_action = QAction("📂 Open File", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.select_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("❌ Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Scan Menu
        scan_menu = menubar.addMenu("🔍 Scan")
        
        scan_file_action = QAction("🔍 Scan File", self)
        scan_file_action.setShortcut("Ctrl+S")
        scan_file_action.triggered.connect(self.start_scan)
        scan_menu.addAction(scan_file_action)
        
        scan_menu.addSeparator()
        
        sandbox_action = QAction("🏖️ Open in Sandbox", self)
        sandbox_action.setShortcut("Ctrl+B")
        sandbox_action.triggered.connect(lambda: self.open_in_sandbox())
        scan_menu.addAction(sandbox_action)
        
        # USB Menu
        usb_menu = menubar.addMenu("💾 USB")
        
        scan_usb_action = QAction("🔍 Scan USB Drive", self)
        scan_usb_action.triggered.connect(self.scan_usb_drive_menu)
        usb_menu.addAction(scan_usb_action)
        
        scan_all_usb_action = QAction("🔍 Scan All USB Drives", self)
        scan_all_usb_action.triggered.connect(self.scan_all_usb_drives)
        usb_menu.addAction(scan_all_usb_action)
        
        usb_menu.addSeparator()
        
        refresh_usb_action = QAction("🔄 Refresh USB List", self)
        refresh_usb_action.triggered.connect(self.refresh_usb_list)
        usb_menu.addAction(refresh_usb_action)
        
        test_usb_action = QAction("🧪 Test USB Detection", self)
        test_usb_action.triggered.connect(self.test_usb_detection)
        usb_menu.addAction(test_usb_action)
        
        # Sandbox Menu
        sandbox_menu = menubar.addMenu("🏖️ Sandbox")
        
        open_sandbox_action = QAction("🏖️ Open in Sandbox", self)
        open_sandbox_action.triggered.connect(lambda: self.open_in_sandbox())
        sandbox_menu.addAction(open_sandbox_action)
        
        sandbox_menu.addSeparator()
        
        status_action = QAction("📊 Sandbox Status", self)
        status_action.triggered.connect(self.show_sandbox_status)
        sandbox_menu.addAction(status_action)
        
        clean_action = QAction("🧹 Clean Sandbox", self)
        clean_action.triggered.connect(self.clean_sandbox)
        sandbox_menu.addAction(clean_action)
        
        emergency_action = QAction("🚨 Emergency Kill", self)
        emergency_action.triggered.connect(self.emergency_kill)
        emergency_action.setShortcut("Ctrl+K")
        sandbox_menu.addAction(emergency_action)
        
        # Help Menu
        help_menu = menubar.addMenu("❓ Help")
        
        about_action = QAction("ℹ️ About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def log_startup(self):
        """Log startup message"""
        self.append_log("=" * 70)
        self.append_log("🛡️ Anti-Ransomware Protection System Started")
        self.append_log("=" * 70)
        self.append_log(f"📂 Working Directory: {os.getcwd()}")
        self.append_log(f"💻 System: {os.name}")
        self.append_log("✅ All scanners initialized successfully")
        
        if self.sandbox_manager.is_sandboxie_installed():
            self.append_log(f"✅ Sandboxie-Plus found at: {self.sandbox_manager.sandboxie_path}")
        else:
            self.append_log("⚠️ Sandboxie-Plus not found - using fallback mode")
        
        self.append_log("✅ USB monitoring started")
        self.append_log("✅ Process monitoring started")
        self.append_log("=" * 70)
        self.append_log("💡 Select a file to scan or insert a USB drive")
        self.append_log("=" * 70)
    
    # ========== FILE OPERATIONS ==========
    
    def select_file(self):
        """Select a file to scan"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select File to Scan",
            "",
            "All Files (*.*);;Executable Files (*.exe);;DLL Files (*.dll);;Script Files (*.py;*.js;*.vbs)"
        )
        if file_path:
            self.file_path = file_path
            self.file_label.setText(f"📄 Selected: {os.path.basename(file_path)}")
            self.file_label.setStyleSheet("border: 1px solid #4CAF50; padding: 8px; background: #e8f5e9; border-radius: 4px;")
            self.scan_btn.setEnabled(True)
            self.sandbox_btn.setEnabled(True)
            self.append_log(f"📂 File selected: {file_path}")
            self.statusBar().showMessage(f"File selected: {os.path.basename(file_path)}")
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.clear()
        self.append_log("📋 Log cleared")
    
    # ========== SCAN OPERATIONS ==========
    
    def start_scan(self):
        """Start scanning the selected file"""
        if not self.file_path:
            return
        
        self.scan_btn.setEnabled(False)
        self.sandbox_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        self.details_text.clear()
        
        # Collect active scanners
        scanners = []
        if self.signature_check.isChecked():
            scanners.append(self.signature_scanner)
        if self.heuristic_check.isChecked():
            scanners.append(self.heuristic_scanner)
        if self.entropy_check.isChecked():
            scanners.append(self.entropy_analyzer)
        if self.deception_check.isChecked():
            scanners.append(self.deception_scanner)
        
        if not scanners:
            QMessageBox.warning(self, "Warning", "Please select at least one scan method")
            self.scan_btn.setEnabled(True)
            self.sandbox_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        
        # Start scan thread
        self.scan_thread = ScanThread(self.file_path, scanners)
        self.scan_thread.progress_update.connect(self.update_progress)
        self.scan_thread.log_update.connect(self.append_log)
        self.scan_thread.scan_complete.connect(self.handle_scan_complete)
        self.scan_thread.start()
        
        self.statusBar().showMessage("🔄 Scanning in progress...")
        self.append_log("=" * 60)
        self.append_log(f"🔍 Starting scan for: {os.path.basename(self.file_path)}")
        self.append_log("=" * 60)
    
    def stop_scan(self):
        """Stop the ongoing scan"""
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.terminate()
            self.scan_thread.wait()
            self.scan_btn.setEnabled(True)
            self.sandbox_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.statusBar().showMessage("⏹️ Scan stopped by user")
            self.append_log("⏹️ Scan stopped by user")
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)
    
    def append_log(self, message):
        """Thread-safe log append"""
        QMetaObject.invokeMethod(self.log_text, "append", 
                                Qt.QueuedConnection,
                                Q_ARG(str, message))
    
    def handle_scan_complete(self, results):
        """Handle scan completion"""
        self.scan_btn.setEnabled(True)
        self.sandbox_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        
        # Populate results table
        row = 0
        for method, result in results.items():
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(method))
            
            if "error" in result:
                self.results_table.setItem(row, 1, QTableWidgetItem("❌ Error"))
                self.results_table.setItem(row, 2, QTableWidgetItem(result["error"]))
                for col in range(3):
                    self.results_table.item(row, col).setBackground(QColor(255, 200, 200))
            elif result.get("whitelisted", False):
                self.results_table.setItem(row, 1, QTableWidgetItem("🛡️ Whitelisted"))
                self.results_table.setItem(row, 2, QTableWidgetItem("File is whitelisted (known legitimate)"))
                for col in range(3):
                    self.results_table.item(row, col).setBackground(QColor(200, 255, 200))
            elif result.get("threat_detected", False):
                threat_level = result.get("threat_level", "Unknown")
                confidence = result.get("confidence", "low")
                classification = result.get("file_classification", "")
                
                if threat_level == "critical":
                    status_text = "🚨 CRITICAL THREAT"
                    color = QColor(255, 100, 100)
                elif threat_level == "high":
                    status_text = "⚠️ High Risk Threat"
                    color = QColor(255, 150, 100)
                elif threat_level == "medium":
                    status_text = "⚡ Medium Risk Threat"
                    color = QColor(255, 200, 100)
                else:
                    status_text = "⚠️ Potential Threat"
                    color = QColor(255, 220, 150)
                
                self.results_table.setItem(row, 1, QTableWidgetItem(status_text))
                details = result.get("threat_description", "Unknown threat")
                if classification:
                    details += f" [Class: {classification}]"
                if confidence:
                    details += f" (Confidence: {confidence})"
                self.results_table.setItem(row, 2, QTableWidgetItem(details))
                
                for col in range(3):
                    self.results_table.item(row, col).setBackground(color)
            else:
                self.results_table.setItem(row, 1, QTableWidgetItem("✅ Clean"))
                self.results_table.setItem(row, 2, QTableWidgetItem("No threats found"))
                for col in range(3):
                    self.results_table.item(row, col).setBackground(QColor(200, 255, 200))
            
            row += 1
        
        # Display detailed results
        self.details_text.clear()
        for method, result in results.items():
            self.details_text.append(f"=== {method} ===")
            if isinstance(result, dict):
                for key, value in result.items():
                    if key not in ['detections', 'signatures_found', 'behavioral_indicators', 'canary_status']:
                        self.details_text.append(f"{key}: {value}")
                    else:
                        if value:
                            self.details_text.append(f"{key}:")
                            if isinstance(value, list):
                                for item in value[:10]:
                                    if isinstance(item, dict):
                                        self.details_text.append(f"  - {item.get('name', item)}")
                                    else:
                                        self.details_text.append(f"  - {item}")
                                if len(value) > 10:
                                    self.details_text.append(f"  ... and {len(value) - 10} more")
                            else:
                                self.details_text.append(f"  - {value}")
            self.details_text.append("")
        
        self.statusBar().showMessage("✅ Scan completed")
        self.append_log("✅ Scan completed successfully")
        
        # Check for critical threats
        critical_threats = []
        high_threats = []
        medium_threats = []
        
        for method, result in results.items():
            if result.get("threat_detected", False):
                threat_level = result.get("threat_level", "unknown")
                if threat_level == "critical":
                    critical_threats.append(result.get("threat_description", ""))
                elif threat_level == "high":
                    high_threats.append(result.get("threat_description", ""))
                elif threat_level == "medium":
                    medium_threats.append(result.get("threat_description", ""))
        
        if critical_threats:
            QMessageBox.critical(self, "🚨 CRITICAL THREAT DETECTED", 
                               "Critical threat detected!\n\n" + "\n".join(critical_threats[:3]) + 
                               "\n\nThis file exhibits ransomware-like behavior.\nPlease quarantine this file immediately.")
        elif high_threats:
            QMessageBox.warning(self, "⚠️ High Risk Threat Detected", 
                              "High-risk threat detected!\n\n" + "\n".join(high_threats[:3]) + 
                              "\n\nPlease review this file carefully.")
        elif medium_threats:
            QMessageBox.warning(self, "⚡ Medium Risk Detected", 
                              "Suspicious behavior detected!\n\n" + "\n".join(medium_threats[:3]) + 
                              "\n\nMonitor this file for suspicious activity.")
    
    # ========== USB OPERATIONS WITH BIG NOTIFICATION ==========
    
    def on_usb_detected(self, drive, action):
        """Handle USB detection with BIG notification"""
        try:
            if action == "inserted":
                self.append_log(f"🔌 USB drive detected: {drive}")
                self.statusBar().showMessage(f"🔌 USB detected: {drive}")
                self.refresh_usb_list()
                
                # Get USB info
                usb_info = self.usb_monitor.get_usb_info(drive)
                volume_name = usb_info.get('volume_name', 'USB Drive')
                total_space = self.format_size(usb_info.get('total_space', 0))
                
                # Show BIG notification dialog
                self.show_big_usb_notification(drive, volume_name, total_space)
                
            elif action == "removed":
                self.append_log(f"🔌 USB drive removed: {drive}")
                self.statusBar().showMessage(f"🔌 USB removed: {drive}")
                self.refresh_usb_list()
                
        except Exception as e:
            print(f"USB detection handler error: {e}")
    
    def show_big_usb_notification(self, drive_path, volume_name, total_space):
        """Show BIG prominent USB notification dialog"""
        try:
            # Create and show the big notification dialog
            dialog = USBNotificationDialog(drive_path, volume_name, total_space, self)
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                if dialog.result == "sandbox":
                    self.open_usb_in_sandbox(drive_path)
                elif dialog.result == "open":
                    self.append_log(f"📂 Opening USB in Explorer: {drive_path}")
                    try:
                        os.startfile(drive_path)
                    except:
                        subprocess.Popen(['explorer.exe', drive_path])
                else:
                    self.append_log(f"USB action cancelled for {drive_path}")
            else:
                self.append_log(f"USB action cancelled for {drive_path}")
                
        except Exception as e:
            self.append_log(f"Notification error: {str(e)}")
            # Fallback to simple notification
            self.show_simple_usb_notification(drive_path)
    
    def show_simple_usb_notification(self, drive_path):
        """Simple fallback notification"""
        try:
            import ctypes
            message = f"🔌 USB Drive Detected\n\nDrive: {drive_path}\n\nWould you like to open this USB in Sandbox for security?"
            
            result = ctypes.windll.user32.MessageBoxW(
                0,
                message,
                "USB Drive Detected - Anti-Ransomware",
                0x00000004 | 0x00000040
            )
            
            if result == 6:  # IDYES
                self.open_usb_in_sandbox(drive_path)
            elif result == 7:  # IDNO
                try:
                    os.startfile(drive_path)
                except:
                    subprocess.Popen(['explorer.exe', drive_path])
        except:
            pass
    
    def open_usb_in_sandbox(self, drive_path):
        """Open USB drive in Sandbox"""
        try:
            self.append_log(f"🏖️ Opening USB in Sandbox: {drive_path}")
            self.statusBar().showMessage(f"🏖️ Opening USB in Sandbox: {drive_path}")
            
            if not self.sandbox_manager.is_sandboxie_installed():
                self.append_log("⚠️ Sandboxie-Plus not installed, using fallback")
                self.open_usb_in_fallback_sandbox(drive_path)
                return
            
            sandboxie_dir = os.path.dirname(self.sandbox_manager.sandboxie_path)
            start_exe = os.path.join(sandboxie_dir, "Start.exe")
            
            if os.path.exists(start_exe):
                cmd = [start_exe, "/box:DefaultBox", "explorer.exe", drive_path]
                self.append_log(f"📂 Command: {' '.join(cmd)}")
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
                self.append_log(f"✅ USB opened in Sandboxie-Plus")
                
                QMessageBox.information(self, "✅ USB in Sandbox", 
                                      f"USB drive {drive_path} is now open in Sandboxie-Plus!\n\n"
                                      f"All files will be opened in isolated environment.\n\n"
                                      f"💡 The window will have a yellow border (Sandboxie indicator).")
            else:
                self.append_log("⚠️ Sandboxie-Plus Start.exe not found")
                self.open_usb_in_fallback_sandbox(drive_path)
            
        except Exception as e:
            self.append_log(f"❌ Error opening USB in sandbox: {str(e)}")
            QMessageBox.critical(self, "❌ Error", f"Error opening USB in sandbox: {str(e)}")
    
    def open_usb_in_fallback_sandbox(self, drive_path):
        """Open USB in fallback sandbox"""
        try:
            sandbox_dir = os.path.join(os.environ['TEMP'], f"usb_sandbox_{int(time.time())}")
            os.makedirs(sandbox_dir, exist_ok=True)
            
            shortcut_path = os.path.join(sandbox_dir, "USB_Drive.lnk")
            
            ps_command = f'''
            $WScriptShell = New-Object -ComObject WScript.Shell
            $Shortcut = $WScriptShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{drive_path}"
            $Shortcut.Save()
            '''
            subprocess.Popen(['powershell.exe', '-Command', ps_command], shell=True)
            
            subprocess.Popen(['explorer.exe', sandbox_dir])
            
            self.append_log(f"✅ USB opened in fallback sandbox: {sandbox_dir}")
            QMessageBox.information(self, "✅ USB in Fallback Sandbox", 
                                  f"USB drive {drive_path} is now open in fallback sandbox!\n\n"
                                  f"📂 Sandbox: {sandbox_dir}\n\n"
                                  f"Click on 'USB_Drive.lnk' to access the USB.\n\n"
                                  f"⚠️ All files are opened in isolated environment.")
            
        except Exception as e:
            self.append_log(f"❌ Fallback sandbox error: {str(e)}")
            QMessageBox.critical(self, "❌ Error", f"Error opening USB in fallback sandbox: {str(e)}")
    
    def scan_usb_drive(self, drive_path):
        """Scan USB drive"""
        self.append_log("=" * 60)
        self.append_log(f"💾 Starting USB scan for: {drive_path}")
        self.append_log("=" * 60)
        self.statusBar().showMessage(f"🔄 Scanning USB drive: {drive_path}")
        
        try:
            usb_info = self.usb_monitor.get_usb_info(drive_path)
            self.append_log(f"📊 USB Information:")
            self.append_log(f"  📂 Drive: {drive_path}")
            self.append_log(f"  💿 Volume: {usb_info.get('volume_name', 'Unknown')}")
            self.append_log(f"  🔢 Serial: {usb_info.get('serial_number', 'Unknown')}")
            self.append_log(f"  💾 Total Space: {self.format_size(usb_info.get('total_space', 0))}")
            self.append_log(f"  📊 Free Space: {self.format_size(usb_info.get('free_space', 0))}")
            self.append_log(f"  📈 Used Space: {self.format_size(usb_info.get('used_space', 0))}")
            
            scan_results = self.usb_scanner.scan_usb_drive(drive_path)
            
            self.append_log(f"\n📊 USB Scan Results:")
            self.append_log(f"  📄 Total files: {scan_results.get('total_files', 0)}")
            self.append_log(f"  ⚙️ Executable files: {len(scan_results.get('executable_files', []))}")
            self.append_log(f"  ⚠️ Suspicious files: {len(scan_results.get('suspicious_files', []))}")
            
            if scan_results.get('executable_files'):
                self.append_log("\n  ⚙️ Executable files found:")
                for exe in scan_results['executable_files'][:10]:
                    self.append_log(f"    - {exe['name']} ({self.format_size(exe['size'])})")
                if len(scan_results['executable_files']) > 10:
                    self.append_log(f"    ... and {len(scan_results['executable_files']) - 10} more")
            
            if scan_results.get("threat_detected", False):
                self.append_log(f"\n⚠️ THREAT DETECTED: {scan_results.get('threat_description', '')}")
                QMessageBox.warning(self, "⚠️ USB Threat Detected", 
                                  f"Potential threat detected on USB drive!\n\n{scan_results.get('threat_description', '')}")
                
                if scan_results.get("executable_files"):
                    reply = QMessageBox.question(self, "🏖️ Open in Sandbox", 
                                                "Executable files found on USB.\nWould you like to open them in a sandbox?",
                                                QMessageBox.Yes | QMessageBox.No)
                    
                    if reply == QMessageBox.Yes:
                        exec_file = scan_results["executable_files"][0]
                        self.open_in_sandbox(exec_file["path"])
            else:
                self.append_log(f"\n✅ USB scan completed - No threats detected")
                QMessageBox.information(self, "✅ USB Scan Complete", 
                                      f"USB scan completed!\n\nNo threats detected on {drive_path}")
            
            self.statusBar().showMessage("✅ USB scan completed")
            self.append_log("=" * 60)
            
        except Exception as e:
            self.append_log(f"❌ Error scanning USB: {str(e)}")
            QMessageBox.critical(self, "❌ USB Scan Error", f"Error scanning USB: {str(e)}")
    
    def scan_usb_drive_menu(self):
        """Scan USB drive from menu"""
        drives = self.usb_monitor.get_removable_drives()
        
        if not drives:
            QMessageBox.information(self, "💾 USB", "No USB drives found")
            return
        
        drive, ok = QInputDialog.getItem(self, "Select USB Drive", "Choose USB drive:", drives, 0, False)
        
        if ok and drive:
            self.scan_usb_drive(drive)
    
    def scan_all_usb_drives(self):
        """Scan all USB drives"""
        drives = self.usb_monitor.get_removable_drives()
        
        if not drives:
            QMessageBox.information(self, "💾 USB", "No USB drives found")
            return
        
        for drive in drives:
            self.scan_usb_drive(drive)
    
    def refresh_usb_list(self):
        """Refresh USB drive list"""
        self.usb_list.clear()
        self.usb_details.clear()
        
        drives = self.usb_monitor.get_removable_drives()
        
        if not drives:
            self.usb_list.addItem("📭 No USB drives detected")
            return
        
        for drive in drives:
            try:
                info = self.usb_monitor.get_usb_info(drive)
                volume = info.get('volume_name', 'Unknown')
                free = self.format_size(info.get('free_space', 0))
                total = self.format_size(info.get('total_space', 0))
                item_text = f"💾 {drive} - {volume} (Free: {free} / {total})"
                self.usb_list.addItem(item_text)
                
                item = self.usb_list.item(self.usb_list.count() - 1)
                item.setData(Qt.UserRole, drive)
            except:
                self.usb_list.addItem(f"💾 {drive}")
        
        self.usb_list.itemClicked.connect(self.show_usb_details_from_item)
        self.append_log(f"🔄 USB list refreshed - {len(drives)} drive(s) found")
    
    def show_usb_details_from_item(self, item):
        """Show USB drive details from list item"""
        drive = item.data(Qt.UserRole)
        if drive:
            self.show_usb_details(drive)
    
    def show_usb_details(self, drive_path):
        """Show USB drive details"""
        info = self.usb_monitor.get_usb_info(drive_path)
        details = f"📊 USB Drive Details\n"
        details += "=" * 40 + "\n"
        details += f"📂 Drive: {drive_path}\n"
        details += f"💿 Volume: {info.get('volume_name', 'Unknown')}\n"
        details += f"🔢 Serial: {info.get('serial_number', 'Unknown')}\n"
        details += f"💾 Total: {self.format_size(info.get('total_space', 0))}\n"
        details += f"📊 Free: {self.format_size(info.get('free_space', 0))}\n"
        details += f"📈 Used: {self.format_size(info.get('used_space', 0))}\n"
        details += f"📊 Usage: {int((info.get('used_space', 0) / info.get('total_space', 1)) * 100)}%"
        self.usb_details.setText(details)
    
    def test_usb_detection(self):
        """Test USB detection manually"""
        self.append_log("🧪 Testing USB detection...")
        self.statusBar().showMessage("🧪 Testing USB detection...")
        
        drives = self.usb_monitor.get_removable_drives()
        
        if drives:
            self.append_log(f"✅ Found USB drives: {drives}")
            for drive in drives:
                self.append_log(f"  📂 Drive: {drive}")
                info = self.usb_monitor.get_usb_info(drive)
                self.append_log(f"    💿 Volume: {info.get('volume_name', 'Unknown')}")
                self.append_log(f"    💾 Free: {self.format_size(info.get('free_space', 0))}")
            
            reply = QMessageBox.question(self, "🧪 USB Test", 
                                        f"Found {len(drives)} USB drive(s).\n\nSimulate USB insertion detection?",
                                        QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes and drives:
                self.on_usb_detected(drives[0], "inserted")
            
            self.refresh_usb_list()
        else:
            self.append_log("❌ No USB drives found")
            QMessageBox.information(self, "🧪 USB Test", 
                                  "No USB drives detected.\n\nPlease insert a USB drive and try again.")
        
        self.statusBar().showMessage("✅ USB test completed")
    
    def format_size(self, size):
        """Format file size"""
        if size == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    # ========== SANDBOX OPERATIONS ==========
    
    def update_sandbox_status(self):
        """Update sandbox status in UI"""
        if self.sandbox_manager.is_sandboxie_installed():
            self.sandbox_status_label.setText("✅ Sandboxie-Plus is installed")
            self.sandbox_status_label.setStyleSheet("color: #4CAF50;")
            self.sandbox_path_label.setText(f"📂 Path: {self.sandbox_manager.sandboxie_path}")
        else:
            self.sandbox_status_label.setText("⚠️ Sandboxie-Plus not installed - Using fallback")
            self.sandbox_status_label.setStyleSheet("color: #FF9800;")
            self.sandbox_path_label.setText("📂 Path: Not found")
        
        active = len([p for p in self.sandbox_manager.sandbox_processes if p.get("monitoring", False)])
        total = len(self.sandbox_manager.sandbox_processes)
        self.sandbox_processes_label.setText(f"🔄 Processes: {active} active / {total} total")
        
        self.sandbox_log_text.clear()
        for log in self.sandbox_manager.sandbox_log[-20:]:
            self.sandbox_log_text.append(log)
    
    def open_in_sandbox(self, file_path=None):
        """Open file in sandbox"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select File to Open in Sandbox",
                "",
                "All Files (*.*);;Executable Files (*.exe);;DLL Files (*.dll)"
            )
            if not file_path:
                return
        
        if not self.sandbox_manager.is_sandboxie_installed():
            reply = QMessageBox.question(self, "⚠️ Sandboxie-Plus Not Found", 
                                        "Sandboxie-Plus is not installed.\n\n"
                                        "Would you like to use the fallback sandbox instead?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
        
        dialog = SandboxDialog(file_path, self.sandbox_manager, self)
        dialog.exec_()
        
        self.update_sandbox_status()
    
    def show_sandbox_status(self):
        """Show sandbox status"""
        if self.sandbox_manager.sandbox_dir:
            status = f"🏖️ Sandbox Status\n"
            status += "=" * 40 + "\n"
            status += f"📂 Location: {self.sandbox_manager.sandbox_dir}\n"
            status += f"🔄 Running Processes: {len([p for p in self.sandbox_manager.sandbox_processes if p.get('monitoring', False)])}\n"
            status += f"📊 Total Processes: {len(self.sandbox_manager.sandbox_processes)}\n\n"
            
            if self.sandbox_manager.sandbox_processes:
                status += "📋 Process List:\n"
                for proc in self.sandbox_manager.sandbox_processes:
                    status += f"\n  🔄 PID: {proc['pid']}\n"
                    status += f"  📄 File: {os.path.basename(proc['file_path'])}\n"
                    status += f"  ⏰ Started: {proc.get('start_time', 'Unknown')}\n"
                    status += f"  📊 Status: {'🔄 Running' if proc.get('monitoring') else '✅ Stopped'}\n"
                    if "end_time" in proc:
                        status += f"  ⏹️ Ended: {proc['end_time']}\n"
            
            QMessageBox.information(self, "🏖️ Sandbox Status", status)
        else:
            QMessageBox.information(self, "🏖️ Sandbox Status", "No sandbox environment is currently active")
    
    def clean_sandbox(self):
        """Clean sandbox environment"""
        if self.sandbox_manager.sandbox_dir or self.sandbox_manager.sandbox_processes:
            reply = QMessageBox.question(self, "🧹 Clean Sandbox", 
                                        "This will terminate all sandbox processes and clean up the environment.\nContinue?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.sandbox_manager.clean_sandbox()
                self.append_log("✅ Sandbox cleaned up")
                self.update_sandbox_status()
                QMessageBox.information(self, "✅ Sandbox", "Sandbox environment cleaned successfully")
        else:
            QMessageBox.information(self, "🧹 Sandbox", "No sandbox environment to clean")
    
    def emergency_kill(self):
        """Emergency kill all sandbox and lock screen processes"""
        reply = QMessageBox.question(self, "🚨 EMERGENCY KILL", 
                                    "This will FORCEFULLY TERMINATE:\n\n"
                                    "1. 🔒 Lock Screen Applications (app.py)\n"
                                    "2. 🏖️ Sandbox Environment (Sandboxie-Plus)\n"
                                    "3. 🔓 Unlock Desktop Files (.locked)\n"
                                    "4. 🖼️ Restore Wallpaper\n\n"
                                    "⚠️ WARNING: All sandbox data will be LOST!\n"
                                    "✅ Your other applications will NOT be affected.\n\n"
                                    "Continue?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.append_log("=" * 60)
            self.append_log("🚨 EMERGENCY KILL INITIATED!")
            self.append_log("=" * 60)
            
            try:
                result = self.sandbox_manager.emergency_kill_all()
                
                if result and result.get("killed_count", 0) > 0:
                    killed_count = result.get("killed_count", 0)
                    killed_names = result.get("killed_names", [])
                    unlocked_files = result.get("unlocked_files", 0)
                    
                    self.append_log(f"✅ Emergency kill completed. Killed {killed_count} processes.")
                    
                    kill_details = ""
                    if killed_names:
                        kill_details = "\n".join([f"• {name}" for name in killed_names[:20]])
                        if len(killed_names) > 20:
                            kill_details += f"\n... and {len(killed_names) - 20} more"
                    
                    if unlocked_files > 0:
                        if kill_details:
                            kill_details += f"\n• Unlocked {unlocked_files} desktop files"
                        else:
                            kill_details = f"• Unlocked {unlocked_files} desktop files"
                    
                    QMessageBox.information(self, "✅ Emergency Kill Complete", 
                                          f"Emergency kill completed successfully!\n\n"
                                          f"✅ Killed {killed_count} processes.\n"
                                          f"✅ Desktop files unlocked.\n"
                                          f"✅ Wallpaper restored.\n"
                                          f"✅ Sandbox environment terminated.\n"
                                          f"✅ System is back to normal.\n\n"
                                          f"💀 Terminated:\n{kill_details if kill_details else 'All processes terminated'}")
                else:
                    self.append_log("⚠️ No processes were killed")
                    
                    try:
                        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                        locked_extension = ".locked"
                        unlocked_count = 0
                        for item in os.listdir(desktop_path):
                            if item.endswith(locked_extension):
                                original_path = os.path.join(desktop_path, item.replace(locked_extension, ""))
                                locked_path = os.path.join(desktop_path, item)
                                try:
                                    os.rename(locked_path, original_path)
                                    unlocked_count += 1
                                except:
                                    pass
                        
                        if unlocked_count > 0:
                            self.append_log(f"🔓 Unlocked {unlocked_count} desktop files")
                    except:
                        pass
                    
                    QMessageBox.warning(self, "⚠️ No Processes", 
                                      "No lock screen or sandbox processes were found.\n\n"
                                      "Desktop files have been unlocked and wallpaper restored.")
                
                self.update_sandbox_status()
                
            except Exception as e:
                self.append_log(f"❌ Emergency kill error: {str(e)}")
                QMessageBox.critical(self, "❌ Emergency Kill Error", 
                                   f"Error during emergency kill: {str(e)}\n\n"
                                   "Please try closing the application manually.")
    
    # ========== ABOUT ==========
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About Anti-Ransomware Protection System",
                         "<h1>🛡️ Anti-Ransomware Protection System</h1>"
                         "<p><b>Version:</b> 2.0</p>"
                         "<p><b>Description:</b> Advanced anti-ransomware solution with multiple detection layers</p>"
                         "<br>"
                         "<h2>Features:</h2>"
                         "<ul>"
                         "<li>🔍 Signature-based detection</li>"
                         "<li>🧠 Heuristic/Behavioral analysis</li>"
                         "<li>📊 Entropy analysis</li>"
                         "<li>🪤 Deception techniques (Canary files)</li>"
                         "<li>💾 USB drive scanning with auto-detection</li>"
                         "<li>🏖️ Sandbox environment (Sandboxie-Plus integration)</li>"
                         "<li>📈 Real-time process monitoring</li>"
                         "<li>🧬 Smart behavior analysis</li>"
                         "<li>🚨 Emergency Kill - Kill lock screen & sandbox</li>"
                         "<li>🔓 Auto USB detection with BIG notification</li>"
                         "</ul>"
                         "<br>"
                         "<p><b>Created by:</b> Security Team</p>"
                         "<p><b>License:</b> MIT</p>")
    
    # ========== CLOSE EVENT ==========
    
    def closeEvent(self, event):
        """Clean up when closing the application"""
        self.append_log("👋 Application shutting down...")
        
        if hasattr(self, 'usb_monitor'):
            self.usb_monitor.stop_monitoring()
        
        if hasattr(self, 'process_monitor'):
            self.process_monitor.stop_monitoring()
        
        if hasattr(self, 'sandbox_manager'):
            self.sandbox_manager.clean_sandbox()
        
        if hasattr(self, 'deception_scanner'):
            self.deception_scanner.cleanup()
        
        event.accept()
