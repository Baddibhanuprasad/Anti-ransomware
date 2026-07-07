import os
import sys
import time
import threading
import win32file
import win32con
import win32api
from datetime import datetime
import ctypes
from ctypes import wintypes
import string
import subprocess

class USBMonitor:
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.detected_usb = []
        self.callback = None
        self.drive_letters = []
        self.check_interval = 1  # Check every 1 second for faster detection
        self.last_notification_time = {}
        self.notification_cooldown = 5  # Seconds between notifications for same drive
        
    def start_monitoring(self, callback=None):
        """Start USB monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.callback = callback
        
        # Get initial drive list
        self.drive_letters = self.get_removable_drives()
        print(f"USB monitoring started. Initial drives: {self.drive_letters}")
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop USB monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("USB monitoring stopped")
    
    def get_removable_drives(self):
        """Get list of removable drives using multiple methods"""
        drives = []
        
        try:
            # Method 1: Using win32api
            try:
                bitmask = win32api.GetLogicalDrives()
                for i in range(26):
                    if bitmask & (1 << i):
                        drive_letter = chr(65 + i) + ":\\"
                        drive_type = win32file.GetDriveType(drive_letter)
                        if drive_type == win32con.DRIVE_REMOVABLE:
                            if drive_letter not in drives:
                                drives.append(drive_letter)
            except Exception as e:
                print(f"Method 1 error: {e}")
            
            # Method 2: Using ctypes directly
            try:
                drives_bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for i in range(26):
                    if drives_bitmask & (1 << i):
                        drive_letter = chr(65 + i) + ":\\"
                        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_letter)
                        if drive_type == 2:  # DRIVE_REMOVABLE
                            if drive_letter not in drives:
                                drives.append(drive_letter)
            except Exception as e:
                print(f"Method 2 error: {e}")
            
            # Method 3: Using GetLogicalDriveStrings
            try:
                buffer = ctypes.create_unicode_buffer(256)
                ctypes.windll.kernel32.GetLogicalDriveStringsW(256, buffer)
                for drive in buffer.value.split('\x00'):
                    if drive:
                        drive_path = drive + "\\"
                        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                        if drive_type == 2:  # DRIVE_REMOVABLE
                            if drive_path not in drives:
                                drives.append(drive_path)
            except Exception as e:
                print(f"Method 3 error: {e}")
                
        except Exception as e:
            print(f"Error getting removable drives: {e}")
        
        return drives
    
    def monitor_loop(self):
        """Main monitoring loop with improved detection"""
        print("USB monitor loop started")
        
        while self.monitoring:
            try:
                # Get current drives
                current_drives = self.get_removable_drives()
                
                # Check for new drives
                new_drives = [d for d in current_drives if d not in self.drive_letters]
                
                # Check for removed drives
                removed_drives = [d for d in self.drive_letters if d not in current_drives]
                
                # Handle new drives
                for drive in new_drives:
                    if drive and os.path.exists(drive):
                        print(f"USB detected: {drive}")
                        
                        # Check cooldown
                        current_time = time.time()
                        if drive not in self.last_notification_time or \
                           (current_time - self.last_notification_time.get(drive, 0)) > self.notification_cooldown:
                            
                            self.last_notification_time[drive] = current_time
                            
                            # Add to detected list
                            self.detected_usb.append({
                                "drive": drive,
                                "insert_time": datetime.now().isoformat(),
                                "status": "active"
                            })
                            
                            # Call callback if set (for UI notification)
                            if self.callback:
                                try:
                                    self.callback(drive, "inserted")
                                except Exception as e:
                                    print(f"Callback error: {e}")
                            
                            # Show Windows system notification (balloon tip)
                            self.show_windows_notification(drive)
                
                # Handle removed drives
                for drive in removed_drives:
                    print(f"USB removed: {drive}")
                    for usb in self.detected_usb:
                        if usb["drive"] == drive:
                            usb["status"] = "removed"
                            usb["remove_time"] = datetime.now().isoformat()
                    
                    # Call callback if set
                    if self.callback:
                        try:
                            self.callback(drive, "removed")
                        except Exception as e:
                            print(f"Callback error: {e}")
                
                # Update drive list
                self.drive_letters = current_drives
                
            except Exception as e:
                print(f"USB monitor loop error: {e}")
            
            # Sleep for interval
            time.sleep(self.check_interval)
        
        print("USB monitor loop ended")
    
    def show_windows_notification(self, drive_path):
        """Show Windows system notification"""
        try:
            # Get drive info
            info = self.get_usb_info(drive_path)
            volume_name = info.get('volume_name', 'USB Drive')
            total_space = self.format_size(info.get('total_space', 0))
            
            # Use Windows toast notification (Windows 10/11)
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    "🔌 USB Drive Detected",
                    f"Drive: {drive_path}\nVolume: {volume_name}\nTotal: {total_space}\n\nClick to scan with Anti-Ransomware",
                    duration=10,
                    threaded=True
                )
            except:
                # Fallback to simple message box
                pass
            
            # Also use system tray balloon (Windows 7/8)
            try:
                import ctypes.wintypes
                
                # Windows notification using Shell_NotifyIcon
                class NOTIFYICONDATA(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", ctypes.wintypes.DWORD),
                        ("hWnd", ctypes.wintypes.HWND),
                        ("uID", ctypes.wintypes.UINT),
                        ("uFlags", ctypes.wintypes.UINT),
                        ("uCallbackMessage", ctypes.wintypes.UINT),
                        ("hIcon", ctypes.wintypes.HANDLE),
                        ("szTip", ctypes.c_wchar * 128),
                        ("dwState", ctypes.wintypes.DWORD),
                        ("dwStateMask", ctypes.wintypes.DWORD),
                        ("szInfo", ctypes.c_wchar * 256),
                        ("uTimeout", ctypes.wintypes.UINT),
                        ("szInfoTitle", ctypes.c_wchar * 64),
                        ("dwInfoFlags", ctypes.wintypes.DWORD)
                    ]
                
                # Get a window handle
                hwnd = ctypes.windll.user32.GetDesktopWindow()
                
                # Create notification
                nid = NOTIFYICONDATA()
                nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
                nid.hWnd = hwnd
                nid.uID = 1001
                nid.uFlags = 0x00000010  # NIF_INFO
                nid.szInfo = f"USB Drive {drive_path} detected.\nVolume: {volume_name}"
                nid.szInfoTitle = "🔌 USB Drive Detected"
                nid.uTimeout = 10000  # 10 seconds
                nid.dwInfoFlags = 0x00000001  # NIIF_INFO
                
                # Show notification
                ctypes.windll.shell32.Shell_NotifyIconW(0x00000001, ctypes.byref(nid))  # NIM_ADD
            except:
                pass
                
        except Exception as e:
            print(f"Notification error: {e}")
    
    def get_usb_info(self, drive_path):
        """Get USB drive information"""
        try:
            # Get volume information
            volume_name = ""
            serial_number = ""
            max_component_len = 0
            file_system_flags = 0
            
            try:
                (volume_name, serial_number, max_component_len, 
                 file_system_flags) = win32file.GetVolumeInformation(drive_path)
            except:
                pass
            
            # Get free space using ctypes
            free_space = 0
            total_space = 0
            try:
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                free_bytes_call = ctypes.c_ulonglong(0)
                
                result = ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(drive_path),
                    ctypes.byref(free_bytes),
                    ctypes.byref(total_bytes),
                    ctypes.byref(free_bytes_call)
                )
                
                if result:
                    free_space = free_bytes.value
                    total_space = total_bytes.value
            except:
                pass
            
            return {
                "drive": drive_path,
                "volume_name": volume_name if volume_name else "Unknown",
                "serial_number": str(serial_number) if serial_number else "Unknown",
                "total_space": total_space,
                "free_space": free_space,
                "used_space": total_space - free_space if total_space > 0 else 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_active_usb_drives(self):
        """Get currently active USB drives"""
        active = []
        for d in self.detected_usb:
            if d["status"] == "active" and os.path.exists(d["drive"]):
                active.append(d)
        return active
    
    def format_size(self, size):
        """Format file size"""
        if size == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


class USBScanner:
    """USB Scanner class - moved here to avoid import issues"""
    def __init__(self):
        self.usb_monitor = USBMonitor()
        self.scanning = False
        
    def scan_usb_drive(self, drive_path):
        """Scan USB drive for files and threats"""
        try:
            results = {
                "drive": drive_path,
                "scan_time": datetime.now().isoformat(),
                "total_files": 0,
                "suspicious_files": [],
                "executable_files": [],
                "threat_detected": False,
                "threat_description": ""
            }
            
            if not os.path.exists(drive_path):
                results["error"] = "Drive does not exist"
                return results
            
            # Walk through USB drive
            for root, dirs, files in os.walk(drive_path):
                # Skip system directories
                skip_dirs = ['System Volume Information', '$Recycle.Bin', 'RECYCLER', 'RECYCLED']
                if any(skip in root for skip in skip_dirs):
                    continue
                
                # Limit scanning depth to avoid too many files
                depth = root.replace(drive_path, "").count(os.sep)
                if depth > 5:
                    continue
                
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        results["total_files"] += 1
                        
                        # Limit file count to avoid performance issues
                        if results["total_files"] > 1000:
                            break
                        
                        # Check for executable files
                        executable_extensions = ['.exe', '.dll', '.scr', '.bat', '.cmd', '.vbs', '.js', '.jar', '.app', '.pif', '.com']
                        if any(file.lower().endswith(ext) for ext in executable_extensions):
                            results["executable_files"].append({
                                "path": file_path,
                                "name": file,
                                "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                            })
                        
                        # Check for suspicious files
                        suspicious_extensions = ['.scr', '.vbs', '.js', '.jar', '.app', '.pif', '.com']
                        if any(file.lower().endswith(ext) for ext in suspicious_extensions):
                            results["suspicious_files"].append(file_path)
                    except:
                        continue
                
                if results["total_files"] > 1000:
                    break
            
            # Check for suspicious indicators
            if len(results["executable_files"]) > 5:
                results["threat_detected"] = True
                results["threat_description"] = "Multiple executable files found on USB drive"
            
            if len(results["suspicious_files"]) > 2:
                results["threat_detected"] = True
                if results["threat_description"]:
                    results["threat_description"] += " Suspicious file types detected"
                else:
                    results["threat_description"] = "Suspicious file types detected"
            
            # Check for autorun.inf
            autorun_path = os.path.join(drive_path, "autorun.inf")
            if os.path.exists(autorun_path):
                results["threat_detected"] = True
                if results["threat_description"]:
                    results["threat_description"] += " Autorun.inf detected (potential autorun malware)"
                else:
                    results["threat_description"] = "Autorun.inf detected (potential autorun malware)"
            
            return results
            
        except Exception as e:
            return {"error": f"USB scan error: {str(e)}"}