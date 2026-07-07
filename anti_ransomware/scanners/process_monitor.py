import psutil
import threading
import time
from datetime import datetime
import os

class ProcessMonitor:
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.suspicious_processes = []
        self.process_log = []
        self.whitelist = self.load_whitelist()
        self.blacklist = self.load_blacklist()
    
    def load_whitelist(self):
        """Load whitelisted processes"""
        return [
            "svchost.exe", "services.exe", "lsass.exe", "winlogon.exe",
            "explorer.exe", "taskmgr.exe", "regedit.exe", "cmd.exe",
            "powershell.exe", "notepad.exe", "calc.exe", "mspaint.exe",
            "chrome.exe", "firefox.exe", "edge.exe", "outlook.exe",
            "winword.exe", "excel.exe", "powerpnt.exe", "msaccess.exe",
            "python.exe", "pycharm.exe", "vscode.exe", "code.exe"
        ]
    
    def load_blacklist(self):
        """Load blacklisted processes (ransomware indicators) - more specific"""
        return [
            "wannacry.exe", "petya.exe", "locky.exe", "cerber.exe",
            "cryptolocker.exe", "teslacrypt.exe", "cryptowall.exe",
            "dodownload.exe", "httpt.exe", "mssecsvc.exe", "tasksche.exe",
            "decrypt.exe", "ransom.exe"
        ]
    
    def start_monitoring(self):
        """Start process monitoring in background"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop process monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
    
    def monitor_loop(self):
        """Main monitoring loop"""
        known_processes = set()
        
        while self.monitoring:
            try:
                current_processes = set()
                
                for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                    try:
                        proc_info = proc.info
                        pid = proc_info['pid']
                        name = proc_info['name'] if proc_info['name'] else ''
                        cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
                        create_time = proc_info['create_time'] if proc_info['create_time'] else 0
                        
                        current_processes.add(pid)
                        
                        # Only check new processes
                        if pid not in known_processes:
                            self.handle_new_process(pid, name, cmdline, create_time)
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Check for terminated processes
                terminated = known_processes - current_processes
                for pid in terminated:
                    self.handle_terminated_process(pid)
                
                known_processes = current_processes
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(2)  # Check every 2 seconds to reduce overhead
    
    def handle_new_process(self, pid, name, cmdline, create_time):
        """Handle new process creation"""
        # Skip if whitelisted
        if name.lower() in [p.lower() for p in self.whitelist]:
            return
        
        timestamp = datetime.now().isoformat()
        
        process_info = {
            "pid": pid,
            "name": name,
            "cmdline": cmdline,
            "create_time": timestamp,
            "suspicious": False,
            "reason": ""
        }
        
        # Check against blacklist - exact match only
        if name.lower() in [p.lower() for p in self.blacklist]:
            process_info["suspicious"] = True
            process_info["reason"] = "Process name in blacklist"
            self.suspicious_processes.append(process_info)
            self.process_log.append(process_info)
            self.alert_suspicious_process(process_info)
            return
        
        # Check command line for ransomware-specific commands
        suspicious_cmd_patterns = [
            "vssadmin delete shadows",
            "wbadmin delete catalog",
            "bcdedit /set recoveryenabled no"
        ]
        
        for pattern in suspicious_cmd_patterns:
            if pattern.lower() in cmdline.lower():
                process_info["suspicious"] = True
                process_info["reason"] = f"Suspicious command: {pattern}"
                self.suspicious_processes.append(process_info)
                self.process_log.append(process_info)
                self.alert_suspicious_process(process_info)
                break
        
        # Check for processes with extremely high resource usage (ransomware indicator)
        try:
            proc = psutil.Process(pid)
            cpu_percent = proc.cpu_percent(interval=0.1)
            memory_info = proc.memory_info()
            
            # Only flag if VERY high and process is not whitelisted
            if cpu_percent > 90 and memory_info.rss > 200 * 1024 * 1024:
                process_info["suspicious"] = True
                process_info["reason"] = f"Extremely high resource usage: CPU {cpu_percent}%, Memory {memory_info.rss / (1024*1024):.1f}MB"
                self.suspicious_processes.append(process_info)
                self.process_log.append(process_info)
                self.alert_suspicious_process(process_info)
        except:
            pass
        
        # Log all processes for debugging
        self.process_log.append(process_info)
    
    def handle_terminated_process(self, pid):
        """Handle process termination"""
        self.suspicious_processes = [p for p in self.suspicious_processes if p["pid"] != pid]
    
    def alert_suspicious_process(self, process_info):
        """Alert about suspicious process"""
        print(f"⚠️ SUSPICIOUS PROCESS: {process_info['name']} (PID: {process_info['pid']})")
        print(f"   Reason: {process_info['reason']}")
        print(f"   Command: {process_info['cmdline'][:200]}...")
    
    def get_suspicious_processes(self):
        """Get list of suspicious processes"""
        return self.suspicious_processes
    
    def get_process_log(self):
        """Get process log"""
        return self.process_log
    
    def scan_file_for_process(self, file_path):
        """Check if file is associated with any suspicious process"""
        try:
            if not os.path.exists(file_path):
                return {"error": "File does not exist"}
            
            filename = os.path.basename(file_path).lower()
            
            suspicious_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'open_files']):
                try:
                    proc_info = proc.info
                    if proc_info['open_files']:
                        for file in proc_info['open_files']:
                            if file_path in file.path:
                                suspicious_processes.append({
                                    "pid": proc_info['pid'],
                                    "name": proc_info['name'],
                                    "cmdline": proc_info['cmdline'],
                                    "file": file.path
                                })
                except:
                    pass
            
            return {
                "suspicious_processes": suspicious_processes,
                "count": len(suspicious_processes)
            }
            
        except Exception as e:
            return {"error": f"Process scan error: {str(e)}"}