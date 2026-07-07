from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFileDialog, QTextEdit, QLabel, 
                             QProgressBar, QTableWidget, QTableWidgetItem,
                             QTabWidget, QGroupBox, QCheckBox, QSplitter,
                             QListWidget, QMessageBox, QHeaderView, QInputDialog,
                             QMenuBar, QAction, QStatusBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMetaObject, Q_ARG
from PyQt5.QtGui import QFont, QColor, QIcon
import os
import sys
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
        
        # Start USB monitoring with thread-safe callback
        self.usb_monitor.start_monitoring(callback=self.on_usb_detected_thread_safe)
        
        # Add menus
        self.create_menus()
    
    def init_ui(self):
        """Initialize the main UI"""
        self.setWindowTitle("Anti-Ransomware Protection System")
        self.setGeometry(100, 100, 1300, 850)
        
        # Set application icon (optional)
        try:
            self.setWindowIcon(QIcon())
        except:
            pass
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # ========== TOP CONTROLS ==========
        controls_layout = QHBoxLayout()
        
        # File selection
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("border: 1px solid #ccc; padding: 5px; background: #f8f8f8;")
        self.file_label.setMinimumWidth(300)
        controls_layout.addWidget(self.file_label)
        
        self.select_btn = QPushButton("📁 Select File")
        self.select_btn.clicked.connect(self.select_file)
        self.select_btn.setStyleSheet("padding: 5px 15px;")
        controls_layout.addWidget(self.select_btn)
        
        self.scan_btn = QPushButton("🔍 Scan File")
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setEnabled(False)
        self.scan_btn.setStyleSheet("padding: 5px 15px; background: #4CAF50; color: white;")
        controls_layout.addWidget(self.scan_btn)
        
        self.sandbox_btn = QPushButton("🏖️ Open in Sandbox")
        self.sandbox_btn.clicked.connect(lambda: self.open_in_sandbox())
        self.sandbox_btn.setEnabled(False)
        self.sandbox_btn.setStyleSheet("padding: 5px 15px; background: #FF9800; color: white;")
        controls_layout.addWidget(self.sandbox_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop Scan")
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("padding: 5px 15px; background: #f44336; color: white;")
        controls_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(controls_layout)
        
        # ========== SCAN OPTIONS ==========
        options_group = QGroupBox("Scan Options")
        options_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        options_layout = QHBoxLayout()
        
        self.signature_check = QCheckBox("Signature Detection")
        self.signature_check.setChecked(True)
        options_layout.addWidget(self.signature_check)
        
        self.heuristic_check = QCheckBox("Heuristic/Behavioral Detection")
        self.heuristic_check.setChecked(True)
        options_layout.addWidget(self.heuristic_check)
        
        self.entropy_check = QCheckBox("Entropy Analysis")
        self.entropy_check.setChecked(True)
        options_layout.addWidget(self.entropy_check)
        
        self.deception_check = QCheckBox("Deception (Canary Files)")
        self.deception_check.setChecked(True)
        options_layout.addWidget(self.deception_check)
        
        options_layout.addStretch()
        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)
        
        # ========== PROGRESS BAR ==========
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # ========== TAB WIDGET ==========
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                padding: 8px 15px;
                margin: 2px;
            }
            QTabBar::tab:selected {
                background: #4CAF50;
                color: white;
            }
        """)
        
        # ----- Log Tab -----
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        
        log_controls = QHBoxLayout()
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_controls.addWidget(self.clear_log_btn)
        log_controls.addStretch()
        log_layout.addLayout(log_controls)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("background: #1e1e1e; color: #d4d4d4;")
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
        self.details_text.setStyleSheet("background: #1e1e1e; color: #d4d4d4;")
        details_layout.addWidget(self.details_text)
        self.tab_widget.addTab(self.details_tab, "📄 Detailed Analysis")
        
        # ----- USB Tab -----
        self.usb_tab = QWidget()
        usb_layout = QVBoxLayout(self.usb_tab)
        
        # USB controls
        usb_controls = QHBoxLayout()
        
        self.scan_usb_btn = QPushButton("🔍 Scan USB Drive")
        self.scan_usb_btn.clicked.connect(self.scan_usb_drive_menu)
        self.scan_usb_btn.setStyleSheet("padding: 5px 15px;")
        usb_controls.addWidget(self.scan_usb_btn)
        
        self.scan_all_usb_btn = QPushButton("🔍 Scan All USB Drives")
        self.scan_all_usb_btn.clicked.connect(self.scan_all_usb_drives)
        self.scan_all_usb_btn.setStyleSheet("padding: 5px 15px;")
        usb_controls.addWidget(self.scan_all_usb_btn)
        
        self.refresh_usb_btn = QPushButton("🔄 Refresh USB List")
        self.refresh_usb_btn.clicked.connect(self.refresh_usb_list)
        self.refresh_usb_btn.setStyleSheet("padding: 5px 15px;")
        usb_controls.addWidget(self.refresh_usb_btn)
        
        self.test_usb_btn = QPushButton("🧪 Test USB Detection")
        self.test_usb_btn.clicked.connect(self.test_usb_detection)
        self.test_usb_btn.setStyleSheet("padding: 5px 15px; background: #FF9800; color: white;")
        usb_controls.addWidget(self.test_usb_btn)
        
        usb_controls.addStretch()
        usb_layout.addLayout(usb_controls)
        
        # USB list and details
        usb_splitter = QSplitter(Qt.Vertical)
        
        self.usb_list = QListWidget()
        self.usb_list.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background: #4CAF50;
                color: white;
            }
        """)
        usb_splitter.addWidget(self.usb_list)
        
        self.usb_details = QTextEdit()
        self.usb_details.setReadOnly(True)
        self.usb_details.setMaximumHeight(150)
        self.usb_details.setFont(QFont("Consolas", 10))
        usb_splitter.addWidget(self.usb_details)
        
        usb_layout.addWidget(usb_splitter)
        self.tab_widget.addTab(self.usb_tab, "💾 USB Drives")
        
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
            <li>💾 USB drive scanning</li>
            <li>🏖️ Sandbox environment</li>
            <li>📈 Real-time process monitoring</li>
            <li>🧬 Smart behavior analysis</li>
        </ul>
        <br>
        <p><b>Created by:</b> Security Team</p>
        <p><b>License:</b> MIT</p>
        """)
        about_text.setStyleSheet("background: #f5f5f5; padding: 20px;")
        about_layout.addWidget(about_text)
        self.tab_widget.addTab(self.about_tab, "ℹ️ About")
        
        main_layout.addWidget(self.tab_widget)
        
        # ========== STATUS BAR ==========
        self.statusBar().showMessage("✅ Ready")
        self.statusBar().setStyleSheet("QStatusBar { background: #f0f0f0; padding: 5px; }")
        
        # Refresh USB list on startup
        self.refresh_usb_list()
        
        # Log startup message
        self.append_log("=" * 60)
        self.append_log("🛡️ Anti-Ransomware Protection System Started")
        self.append_log("=" * 60)
        self.append_log(f"📂 Working Directory: {os.getcwd()}")
        self.append_log(f"💻 System: {os.name}")
        self.append_log("✅ All scanners initialized successfully")
        self.append_log("✅ USB monitoring started")
        self.append_log("✅ Process monitoring started")
        self.append_log("=" * 60)
        self.append_log("💡 Select a file to scan or insert a USB drive")
    
    def create_menus(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("📁 File")
        
        open_action = QAction("Open File", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.select_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Scan Menu
        scan_menu = menubar.addMenu("🔍 Scan")
        
        scan_file_action = QAction("Scan File", self)
        scan_file_action.setShortcut("Ctrl+S")
        scan_file_action.triggered.connect(self.start_scan)
        scan_menu.addAction(scan_file_action)
        
        scan_menu.addSeparator()
        
        sandbox_action = QAction("Open in Sandbox", self)
        sandbox_action.setShortcut("Ctrl+B")
        sandbox_action.triggered.connect(lambda: self.open_in_sandbox())
        scan_menu.addAction(sandbox_action)
        
        # USB Menu
        usb_menu = menubar.addMenu("💾 USB")
        
        scan_usb_action = QAction("Scan USB Drive", self)
        scan_usb_action.triggered.connect(self.scan_usb_drive_menu)
        usb_menu.addAction(scan_usb_action)
        
        scan_all_usb_action = QAction("Scan All USB Drives", self)
        scan_all_usb_action.triggered.connect(self.scan_all_usb_drives)
        usb_menu.addAction(scan_all_usb_action)
        
        usb_menu.addSeparator()
        
        refresh_usb_action = QAction("Refresh USB List", self)
        refresh_usb_action.triggered.connect(self.refresh_usb_list)
        usb_menu.addAction(refresh_usb_action)
        
        test_usb_action = QAction("Test USB Detection", self)
        test_usb_action.triggered.connect(self.test_usb_detection)
        usb_menu.addAction(test_usb_action)
        
        # Sandbox Menu
        sandbox_menu = menubar.addMenu("🏖️ Sandbox")
        
        open_sandbox_action = QAction("Open in Sandbox", self)
        open_sandbox_action.triggered.connect(lambda: self.open_in_sandbox())
        sandbox_menu.addAction(open_sandbox_action)
        
        sandbox_menu.addSeparator()
        
        status_action = QAction("Sandbox Status", self)
        status_action.triggered.connect(self.show_sandbox_status)
        sandbox_menu.addAction(status_action)
        
        clean_action = QAction("Clean Sandbox", self)
        clean_action.triggered.connect(self.clean_sandbox)
        sandbox_menu.addAction(clean_action)
        
        # Help Menu
        help_menu = menubar.addMenu("❓ Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
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
            self.file_label.setStyleSheet("border: 1px solid #4CAF50; padding: 5px; background: #e8f5e9;")
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
                
                # Different icons based on threat level
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
        
        # Show appropriate warnings
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
    
    # ========== USB OPERATIONS ==========
    
    def on_usb_detected_thread_safe(self, drive, action):
        """Thread-safe USB detection handler"""
        QMetaObject.invokeMethod(self, "on_usb_detected",
                                Qt.QueuedConnection,
                                Q_ARG(str, drive),
                                Q_ARG(str, action))
    
    def on_usb_detected(self, drive, action):
        """Handle USB detection (called from main thread)"""
        if action == "inserted":
            self.append_log(f"🔌 USB drive detected: {drive}")
            self.statusBar().showMessage(f"🔌 USB detected: {drive}")
            self.refresh_usb_list()
            
            # Show USB detection notification
            reply = QMessageBox.question(self, "🔌 USB Detected", 
                                        f"USB drive {drive} detected.\n\nWould you like to scan it with Anti-Ransomware?",
                                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            
            if reply == QMessageBox.Yes:
                self.scan_usb_drive(drive)
            elif reply == QMessageBox.Cancel:
                self.append_log(f"USB scan cancelled for {drive}")
        
        elif action == "removed":
            self.append_log(f"🔌 USB drive removed: {drive}")
            self.statusBar().showMessage(f"🔌 USB removed: {drive}")
            self.refresh_usb_list()
    
    def scan_usb_drive(self, drive_path):
        """Scan USB drive"""
        self.append_log("=" * 60)
        self.append_log(f"💾 Starting USB scan for: {drive_path}")
        self.append_log("=" * 60)
        self.statusBar().showMessage(f"🔄 Scanning USB drive: {drive_path}")
        
        try:
            # Get USB info
            usb_info = self.usb_monitor.get_usb_info(drive_path)
            self.append_log(f"📊 USB Information:")
            self.append_log(f"  📂 Drive: {drive_path}")
            self.append_log(f"  💿 Volume: {usb_info.get('volume_name', 'Unknown')}")
            self.append_log(f"  🔢 Serial: {usb_info.get('serial_number', 'Unknown')}")
            self.append_log(f"  💾 Total Space: {self.format_size(usb_info.get('total_space', 0))}")
            self.append_log(f"  📊 Free Space: {self.format_size(usb_info.get('free_space', 0))}")
            self.append_log(f"  📈 Used Space: {self.format_size(usb_info.get('used_space', 0))}")
            
            # Scan USB drive
            scan_results = self.usb_scanner.scan_usb_drive(drive_path)
            
            # Display results
            self.append_log(f"\n📊 USB Scan Results:")
            self.append_log(f"  📄 Total files: {scan_results.get('total_files', 0)}")
            self.append_log(f"  ⚙️ Executable files: {len(scan_results.get('executable_files', []))}")
            self.append_log(f"  ⚠️ Suspicious files: {len(scan_results.get('suspicious_files', []))}")
            
            # Show executable files
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
                
                # Ask if user wants to open in sandbox
                if scan_results.get("executable_files"):
                    reply = QMessageBox.question(self, "🏖️ Open in Sandbox", 
                                                "Executable files found on USB.\nWould you like to open them in a sandbox?",
                                                QMessageBox.Yes | QMessageBox.No)
                    
                    if reply == QMessageBox.Yes:
                        # Open first executable in sandbox
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
        
        # Let user select which USB to scan
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
                
                # Store drive path with item
                item = self.usb_list.item(self.usb_list.count() - 1)
                item.setData(Qt.UserRole, drive)
            except:
                self.usb_list.addItem(f"💾 {drive}")
        
        # Connect item click event
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
        
        # Get current drives
        drives = self.usb_monitor.get_removable_drives()
        
        if drives:
            self.append_log(f"✅ Found USB drives: {drives}")
            for drive in drives:
                self.append_log(f"  📂 Drive: {drive}")
                info = self.usb_monitor.get_usb_info(drive)
                self.append_log(f"    💿 Volume: {info.get('volume_name', 'Unknown')}")
                self.append_log(f"    💾 Free: {self.format_size(info.get('free_space', 0))}")
            
            # Simulate USB detection for testing
            reply = QMessageBox.question(self, "🧪 USB Test", 
                                        f"Found {len(drives)} USB drive(s).\n\nSimulate USB insertion detection?",
                                        QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes and drives:
                # Simulate detection for first drive
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

    def open_in_sandbox(self, file_path=None):
       """Open file in sandbox"""
       if not file_path:
        # If no file specified, ask user to select one
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Open in Sandbox",
            "",
            "All Files (*.*);;Executable Files (*.exe);;DLL Files (*.dll)"
        )
        if not file_path:
            return
    
    # Check if Sandboxie-Plus is installed
        if not self.sandbox_manager.is_sandboxie_installed():
        # Try to find it again
           self.sandbox_manager.sandboxie_path = self.sandbox_manager.find_sandboxie()
        if not self.sandbox_manager.is_sandboxie_installed():
            reply = QMessageBox.question(self, "⚠️ Sandboxie-Plus Not Found", 
                                        "Sandboxie-Plus is not installed.\n\n"
                                        "Would you like to use the fallback sandbox instead?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
            
            # Use fallback sandbox
            self.sandbox_manager.sandbox_type = "Fallback"
    
    # Open sandbox dialog
        dialog = SandboxDialog(file_path, self.sandbox_manager, self)
        dialog.exec_()
    
    
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
        if self.sandbox_manager.sandbox_dir:
            reply = QMessageBox.question(self, "🧹 Clean Sandbox", 
                                        "This will terminate all sandbox processes and clean up the environment.\nContinue?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.sandbox_manager.clean_sandbox()
                self.append_log("✅ Sandbox cleaned up")
                QMessageBox.information(self, "✅ Sandbox", "Sandbox environment cleaned successfully")
        else:
            QMessageBox.information(self, "🧹 Sandbox", "No sandbox environment to clean")
    
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
                         "<li>💾 USB drive scanning</li>"
                         "<li>🏖️ Sandbox environment</li>"
                         "<li>📈 Real-time process monitoring</li>"
                         "<li>🧬 Smart behavior analysis</li>"
                         "</ul>"
                         "<br>"
                         "<p><b>Created by:</b> Security Team</p>"
                         "<p><b>License:</b> MIT</p>")
    
    # ========== CLOSE EVENT ==========
    
    def closeEvent(self, event):
        """Clean up when closing the application"""
        # Stop USB monitoring
        if hasattr(self, 'usb_monitor'):
            self.usb_monitor.stop_monitoring()
        
        # Stop process monitoring
        if hasattr(self, 'process_monitor'):
            self.process_monitor.stop_monitoring()
        
        # Clean sandbox
        if hasattr(self, 'sandbox_manager'):
            self.sandbox_manager.clean_sandbox()
        
        # Clean deception scanner
        if hasattr(self, 'deception_scanner'):
            self.deception_scanner.cleanup()
        
        self.append_log("👋 Application shutting down...")
        event.accept()