from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QProgressBar, QTableWidget,
                             QTableWidgetItem, QMessageBox, QGroupBox, QSplitter,
                             QHeaderView, QWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import os
import time

class SandboxScanThread(QThread):
    progress_update = pyqtSignal(int)
    log_update = pyqtSignal(str)
    scan_complete = pyqtSignal(dict)
    
    def __init__(self, file_path, sandbox_manager):
        super().__init__()
        self.file_path = file_path
        self.sandbox_manager = sandbox_manager
        self.results = {}
        
    def run(self):
        try:
            self.log_update.emit(f"🚀 Starting sandbox analysis for: {os.path.basename(self.file_path)}")
            self.progress_update.emit(10)
            
            installed = self.sandbox_manager.is_sandboxie_installed()
            if installed:
                self.log_update.emit(f"✅ Sandboxie-Plus found at: {self.sandbox_manager.sandboxie_path}")
            else:
                self.log_update.emit("⚠️ Sandboxie-Plus not found - using fallback mode")
            
            self.progress_update.emit(30)
            
            result = self.sandbox_manager.scan_with_sandboxie(self.file_path)
            self.progress_update.emit(70)
            
            activity = self.sandbox_manager.get_sandbox_activity()
            self.progress_update.emit(90)
            
            self.results = {
                "result": result,
                "activity": activity,
                "file_path": self.file_path,
                "sandboxie_installed": installed,
                "sandboxie_path": self.sandbox_manager.sandboxie_path
            }
            
            self.progress_update.emit(100)
            self.log_update.emit("✅ Analysis completed")
            
        except Exception as e:
            self.results = {"error": str(e)}
            self.log_update.emit(f"❌ Error: {str(e)}")
        
        self.scan_complete.emit(self.results)

class SandboxDialog(QDialog):
    def __init__(self, file_path, sandbox_manager, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.sandbox_manager = sandbox_manager
        self.scan_thread = None
        self.setWindowTitle("🏖️ Sandbox Environment - File Analysis")
        self.setGeometry(200, 200, 1000, 750)
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.start_scan()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        header_label = QLabel("🏖️ Sandbox Analysis")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(header_label)
        
        file_label = QLabel(f"📄 File: {os.path.basename(self.file_path)}")
        file_label.setFont(QFont("Arial", 12))
        file_label.setStyleSheet("color: #2196F3;")
        header_layout.addWidget(file_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        status_group = QGroupBox("📊 Status")
        status_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("⏳ Initializing...")
        self.status_label.setFont(QFont("Arial", 11))
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
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
        """)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        splitter = QSplitter(Qt.Vertical)
        splitter.setSizes([400, 300])
        
        log_group = QGroupBox("📋 Sandbox Log")
        log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        log_layout = QVBoxLayout()
        
        log_controls = QHBoxLayout()
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.clear_log_btn.setStyleSheet("padding: 5px 15px;")
        log_controls.addWidget(self.clear_log_btn)
        log_controls.addStretch()
        log_layout.addLayout(log_controls)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            background: #1e1e1e; 
            color: #d4d4d4;
            border: 1px solid #333;
            border-radius: 3px;
        """)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        splitter.addWidget(log_group)
        
        results_group = QGroupBox("📊 Results")
        results_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        results_layout = QVBoxLayout()
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Item", "Value"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QTableWidget::item:selected {
                background: #2196F3;
                color: white;
            }
        """)
        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        splitter.addWidget(results_group)
        
        layout.addWidget(splitter)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.open_btn = QPushButton("▶️ Open in Sandboxie-Plus")
        self.open_btn.clicked.connect(self.open_in_sandboxie)
        self.open_btn.setEnabled(False)
        self.open_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 25px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #4CAF50, stop:1 #66BB6A);
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #43A047, stop:1 #4CAF50);
            }
            QPushButton:disabled {
                background: #9E9E9E;
                color: #BDBDBD;
            }
        """)
        button_layout.addWidget(self.open_btn)
        
        self.fallback_btn = QPushButton("🔄 Open in Fallback Sandbox")
        self.fallback_btn.clicked.connect(self.open_in_fallback)
        self.fallback_btn.setEnabled(False)
        self.fallback_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 25px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #FF9800, stop:1 #FFA726);
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #F57C00, stop:1 #FF9800);
            }
            QPushButton:disabled {
                background: #9E9E9E;
                color: #BDBDBD;
            }
        """)
        button_layout.addWidget(self.fallback_btn)
        
        self.clean_btn = QPushButton("🧹 Clean Sandbox")
        self.clean_btn.clicked.connect(self.clean_sandbox)
        self.clean_btn.setEnabled(False)
        self.clean_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 25px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #f44336, stop:1 #ef5350);
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #d32f2f, stop:1 #f44336);
            }
            QPushButton:disabled {
                background: #9E9E9E;
                color: #BDBDBD;
            }
        """)
        button_layout.addWidget(self.clean_btn)
        
        self.emergency_btn = QPushButton("🚨 Emergency Kill")
        self.emergency_btn.clicked.connect(self.emergency_kill)
        self.emergency_btn.setEnabled(False)
        self.emergency_btn.setToolTip("KILL ALL - Sandbox + Lock Screen + Unlock Desktop")
        self.emergency_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 25px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #f44336, stop:1 #d32f2f);
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #c62828, stop:1 #d32f2f);
            }
            QPushButton:disabled {
                background: #9E9E9E;
                color: #BDBDBD;
            }
        """)
        button_layout.addWidget(self.emergency_btn)
        
        button_layout.addStretch()
        
        self.exit_btn = QPushButton("❌ Close")
        self.exit_btn.clicked.connect(self.close_dialog)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 25px;
                background: #9E9E9E;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #757575;
            }
        """)
        button_layout.addWidget(self.exit_btn)
        
        layout.addLayout(button_layout)
    
    def start_scan(self):
        self.scan_thread = SandboxScanThread(self.file_path, self.sandbox_manager)
        self.scan_thread.progress_update.connect(self.update_progress)
        self.scan_thread.log_update.connect(self.append_log)
        self.scan_thread.scan_complete.connect(self.scan_completed)
        self.scan_thread.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        if value < 30:
            self.status_label.setText("⏳ Checking Sandboxie-Plus...")
        elif value < 60:
            self.status_label.setText("🔍 Analyzing file...")
        elif value < 90:
            self.status_label.setText("📊 Preparing results...")
        else:
            self.status_label.setText("✅ Analysis complete")
    
    def append_log(self, message):
        self.log_text.append(message)
    
    def clear_log(self):
        self.log_text.clear()
        self.append_log("📋 Log cleared")
    
    def scan_completed(self, results):
        self.progress_bar.setValue(100)
        
        if "error" in results:
            self.status_label.setText(f"❌ Error: {results['error']}")
            self.open_btn.setEnabled(False)
            self.fallback_btn.setEnabled(True)
            self.clean_btn.setEnabled(True)
            self.emergency_btn.setEnabled(True)
            return
        
        file_type = results.get("result", {}).get("file_type", "unknown")
        file_type_icons = {
            'executable': '⚙️',
            'document': '📄',
            'image': '🖼️',
            'video': '🎬',
            'audio': '🎵',
            'archive': '📦',
            'unknown': '❓'
        }
        file_type_icon = file_type_icons.get(file_type, '📄')
        
        self.results_table.setRowCount(0)
        
        rows = [
            ("File", os.path.basename(results.get("file_path", "Unknown"))),
            ("File Type", f"{file_type_icon} {file_type}"),
            ("Sandboxie-Plus", "✅ Installed" if results.get("sandboxie_installed") else "❌ Not Installed"),
            ("Sandboxie Path", results.get("sandboxie_path", "Not found")),
            ("Executed", "✅ Yes" if results.get("result", {}).get("executed") else "❌ No"),
            ("Status", results.get("result", {}).get("message", "Unknown")),
            ("Processes", str(len(results.get("activity", {}).get("processes", [])))),
            ("Active Processes", str(len([p for p in results.get("activity", {}).get("processes", []) if p.get("monitoring", False)])))
        ]
        
        for row, (item, value) in enumerate(rows):
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(item))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(value)))
            
            if "❌" in str(value) or "Failed" in str(value) or "Error" in str(value):
                for col in range(2):
                    self.results_table.item(row, col).setBackground(QColor(255, 200, 200))
            elif "✅" in str(value) or "Yes" in str(value):
                for col in range(2):
                    self.results_table.item(row, col).setBackground(QColor(200, 255, 200))
            elif "⚠️" in str(value) or "Warning" in str(value):
                for col in range(2):
                    self.results_table.item(row, col).setBackground(QColor(255, 255, 200))
        
        if results.get("result", {}).get("executed", False):
            self.status_label.setText("✅ File opened successfully in sandbox")
            self.open_btn.setEnabled(True)
            self.fallback_btn.setEnabled(True)
            self.clean_btn.setEnabled(True)
            self.emergency_btn.setEnabled(True)
        elif results.get("sandboxie_installed"):
            self.status_label.setText("⚠️ Sandboxie-Plus available but failed to open")
            self.open_btn.setEnabled(True)
            self.fallback_btn.setEnabled(True)
            self.clean_btn.setEnabled(True)
            self.emergency_btn.setEnabled(True)
        else:
            self.status_label.setText("⚠️ Sandboxie-Plus not found - Use fallback mode")
            self.open_btn.setEnabled(False)
            self.fallback_btn.setEnabled(True)
            self.clean_btn.setEnabled(True)
            self.emergency_btn.setEnabled(True)
        
        self.append_log("\n" + "="*60)
        self.append_log("📋 Sandbox Details")
        self.append_log("="*60)
        
        if results.get("sandboxie_installed"):
            self.append_log(f"✅ Sandboxie-Plus: {results.get('sandboxie_path', 'Unknown')}")
            self.append_log(f"📂 File Type: {file_type}")
            self.append_log("💡 Click 'Open in Sandboxie-Plus' to run the file")
            self.append_log("💡 Click 'Open in Fallback Sandbox' for built-in sandbox")
            self.append_log("🚨 Click 'Emergency Kill' if sandbox gets locked")
        else:
            self.append_log("❌ Sandboxie-Plus not installed")
            self.append_log("💡 Download from: https://sandboxie-plus.com/")
            self.append_log("💡 Click 'Open in Fallback Sandbox' for built-in sandbox")
            self.append_log("🚨 Click 'Emergency Kill' if sandbox gets locked")
        
        self.append_log("="*60)
    
    def open_in_sandboxie(self):
        try:
            self.append_log("▶️ Opening in Sandboxie-Plus...")
            self.open_btn.setEnabled(False)
            self.fallback_btn.setEnabled(False)
            
            result = self.sandbox_manager.run_in_sandboxie(self.file_path)
            
            if result:
                self.append_log(f"✅ File opened in Sandboxie-Plus (PID: {result['pid']})")
                QMessageBox.information(self, "🏖️ Sandbox", 
                                      f"File opened in Sandboxie-Plus!\n\n"
                                      f"Process ID: {result['pid']}\n"
                                      f"Sandbox: DefaultBox\n\n"
                                      f"The file is running in an isolated environment.")
            else:
                self.append_log("❌ Failed to open in Sandboxie-Plus")
                QMessageBox.warning(self, "❌ Error", "Failed to open file in Sandboxie-Plus")
            
            self.open_btn.setEnabled(True)
            self.fallback_btn.setEnabled(True)
            
        except Exception as e:
            self.append_log(f"❌ Error: {str(e)}")
            QMessageBox.critical(self, "❌ Error", f"Error opening in Sandboxie-Plus: {str(e)}")
            self.open_btn.setEnabled(True)
            self.fallback_btn.setEnabled(True)
    
    def open_in_fallback(self):
        try:
            self.append_log("▶️ Opening in Fallback Sandbox...")
            self.open_btn.setEnabled(False)
            self.fallback_btn.setEnabled(False)
            
            result = self.sandbox_manager.run_fallback_sandbox(self.file_path)
            
            if result:
                self.append_log(f"✅ File opened in Fallback Sandbox")
                QMessageBox.information(self, "🏖️ Fallback Sandbox", 
                                      f"File opened in Fallback Sandbox!\n\n"
                                      f"The file is running in an isolated environment.")
            else:
                self.append_log("❌ Failed to open in Fallback Sandbox")
                QMessageBox.critical(self, "❌ Error", "Failed to open file in fallback sandbox")
            
            self.open_btn.setEnabled(True)
            self.fallback_btn.setEnabled(True)
            
        except Exception as e:
            self.append_log(f"❌ Error: {str(e)}")
            QMessageBox.critical(self, "❌ Error", f"Error opening in fallback sandbox: {str(e)}")
            self.open_btn.setEnabled(True)
            self.fallback_btn.setEnabled(True)
    
    def emergency_kill(self):
        """Emergency kill - KILL LOCK SCREEN AND SANDBOX"""
        reply = QMessageBox.question(self, "🚨 EMERGENCY KILL", 
                                    "This will FORCEFULLY TERMINATE:\n\n"
                                    "1. 🔒 Lock Screen Application (app.py)\n"
                                    "2. 🏖️ Sandbox Environment (Sandboxie-Plus)\n"
                                    "3. 🔓 Unlock Desktop Files (.locked)\n"
                                    "4. 🖼️ Restore Wallpaper\n\n"
                                    "⚠️ WARNING: All sandbox data will be LOST!\n"
                                    "✅ Your other applications will NOT be affected.\n\n"
                                    "Continue?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.append_log("="*60)
            self.append_log("🚨 EMERGENCY KILL INITIATED!")
            self.append_log("="*60)
            self.emergency_btn.setEnabled(False)
            self.open_btn.setEnabled(False)
            self.fallback_btn.setEnabled(False)
            self.clean_btn.setEnabled(False)
            
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
                    
                    # Still try to clean up
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
                
                self.emergency_btn.setEnabled(True)
                self.open_btn.setEnabled(True)
                self.fallback_btn.setEnabled(True)
                self.clean_btn.setEnabled(True)
                
                self.append_log("✅ System is back to normal")
                
            except Exception as e:
                self.append_log(f"❌ Emergency kill error: {str(e)}")
                QMessageBox.critical(self, "❌ Emergency Kill Error", 
                                   f"Error during emergency kill: {str(e)}\n\n"
                                   "Please try closing the application manually.")
                self.emergency_btn.setEnabled(True)
                self.open_btn.setEnabled(True)
                self.fallback_btn.setEnabled(True)
                self.clean_btn.setEnabled(True)
    
    def clean_sandbox(self):
        try:
            reply = QMessageBox.question(self, "🧹 Clean Sandbox", 
                                        "This will terminate all sandbox processes and clean up.\n\nContinue?",
                                        QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.append_log("🧹 Cleaning sandbox...")
                self.clean_btn.setEnabled(False)
                self.sandbox_manager.clean_sandbox()
                self.append_log("✅ Sandbox cleaned")
                QMessageBox.information(self, "✅ Sandbox", "Sandbox cleaned successfully")
                self.clean_btn.setEnabled(True)
            
        except Exception as e:
            self.append_log(f"❌ Error: {str(e)}")
            QMessageBox.critical(self, "❌ Error", f"Error cleaning sandbox: {str(e)}")
            self.clean_btn.setEnabled(True)
    
    def close_dialog(self):
        active = [p for p in self.sandbox_manager.sandbox_processes if p.get("monitoring", False)]
        
        if active:
            reply = QMessageBox.question(self, "⚠️ Active Processes", 
                                        f"Sandbox has {len(active)} active process(es).\n\nClose them before exiting?",
                                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            
            if reply == QMessageBox.Cancel:
                return
            elif reply == QMessageBox.Yes:
                self.sandbox_manager.clean_sandbox()
                time.sleep(0.5)
        
        self.accept()
    
    def closeEvent(self, event):
        active = [p for p in self.sandbox_manager.sandbox_processes if p.get("monitoring", False)]
        
        if active:
            reply = QMessageBox.question(self, "⚠️ Active Processes", 
                                        f"Sandbox has {len(active)} active process(es).\n\nClose them before exiting?",
                                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            
            if reply == QMessageBox.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.Yes:
                self.sandbox_manager.clean_sandbox()
                time.sleep(0.5)
        
        event.accept()