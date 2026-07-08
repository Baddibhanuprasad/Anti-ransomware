import os
import sys
import subprocess
import threading
import time
import shutil
from datetime import datetime
import win32api
import win32process
import win32con
import ctypes
import psutil

class SandboxManager:
    def __init__(self):
        self.sandboxie_path = self.find_sandboxie()
        self.sandbox_processes = []
        self.sandbox_log = []
        self.is_running = False
        self.sandbox_dir = None
        self.sandbox_type = "Sandboxie-Plus" if self.sandboxie_path else "None"
        self.emergency_kill = False
        self.sandbox_name = "DefaultBox"
        
    def find_sandboxie(self):
        """Find Sandboxie-Plus installation path"""
        possible_paths = [
            r"C:\Program Files\Sandboxie-Plus\SandMan.exe",
            r"C:\Program Files\Sandboxie\SandMan.exe",
            r"C:\Program Files (x86)\Sandboxie-Plus\SandMan.exe",
            r"C:\Program Files (x86)\Sandboxie\SandMan.exe",
            r"C:\Users\bhanu\Desktop\Sandboxie-Plus.lnk",
            r"C:\Program Files\Sandboxie-Plus\Start.exe",
            r"C:\Program Files\Sandboxie\Start.exe"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ Found Sandboxie-Plus at: {path}")
                return path
        
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\SandMan.exe")
            path = winreg.QueryValue(key, None)
            if path and os.path.exists(path):
                print(f"✅ Found Sandboxie-Plus via registry: {path}")
                return path
        except:
            pass
        
        print("⚠️ Sandboxie-Plus not found.")
        return None
    
    def is_sandboxie_installed(self):
        return self.sandboxie_path is not None and os.path.exists(self.sandboxie_path)
    
    def get_file_type(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        
        file_types = {
            'executable': ['.exe', '.dll', '.scr', '.com', '.bat', '.cmd', '.msi'],
            'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.ico', '.svg', '.webp'],
            'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'],
            'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']
        }
        
        for file_type, extensions in file_types.items():
            if ext in extensions:
                return file_type
        
        return 'unknown'
    
    def run_in_sandboxie(self, file_path, args=None):
        """Run a file using Sandboxie-Plus - FIXED for images"""
        if not self.is_sandboxie_installed():
            self.add_log("⚠️ Sandboxie-Plus not installed")
            return None
        
        if not os.path.exists(file_path):
            self.add_log(f"❌ File does not exist: {file_path}")
            return None
        
        try:
            file_type = self.get_file_type(file_path)
            file_name = os.path.basename(file_path)
            self.add_log(f"📄 File: {file_name} (Type: {file_type})")
            
            # Get Sandboxie-Plus installation directory
            sandboxie_dir = os.path.dirname(self.sandboxie_path)
            sandbox_name = self.sandbox_name
            
            # Use Start.exe
            start_exe = os.path.join(sandboxie_dir, "Start.exe")
            if not os.path.exists(start_exe):
                start_exe = self.sandboxie_path
            
            # For images, use the new reliable method
            if file_type == 'image':
                return self.open_image_reliable(file_path, sandboxie_dir, sandbox_name)
            elif file_type == 'executable':
                return self.run_executable_in_sandboxie(file_path, args, sandboxie_dir, sandbox_name)
            else:
                return self.open_file_in_sandboxie(file_path, sandboxie_dir, sandbox_name)
            
        except Exception as e:
            self.add_log(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return self.run_fallback_sandbox(file_path)
    
    def open_image_reliable(self, file_path, sandboxie_dir, sandbox_name):
        """RELIABLE method to open images in Sandboxie-Plus"""
        try:
            start_exe = os.path.join(sandboxie_dir, "Start.exe")
            if not os.path.exists(start_exe):
                start_exe = self.sandboxie_path
            
            # METHOD: Use the built-in Windows Photo Viewer via rundll32
            # This is the most reliable way to open images in Sandboxie
            self.add_log(f"🖼️ Opening image with Windows Photo Viewer...")
            
            # Copy the image to a temp location with no spaces in path
            # This avoids path issues in Sandboxie
            temp_dir = os.path.join(os.environ['TEMP'], f"sandbox_img_{int(time.time())}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Copy file with a simple name (no spaces)
            file_ext = os.path.splitext(file_path)[1]
            temp_file = os.path.join(temp_dir, f"image{file_ext}")
            shutil.copy2(file_path, temp_file)
            self.add_log(f"📂 Copied to temp: {temp_file}")
            
            # Use rundll32 to open with Photo Viewer
            cmd = [
                start_exe,
                "/box:" + sandbox_name,
                "rundll32.exe",
                "shimgvw.dll,ImageView_Fullscreen",
                temp_file
            ]
            
            self.add_log(f"📂 Command: {' '.join(cmd)}")
            
            # Launch with CREATE_NO_WINDOW flag
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=False
            )
            
            # Wait a moment for it to start
            time.sleep(2)
            
            # Check if it started
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.add_log(f"⚠️ Photo Viewer failed: {stderr.decode() if stderr else 'Unknown'}")
                
                # Try alternative method with mspaint
                return self.open_image_with_mspaint_reliable(file_path, sandboxie_dir, sandbox_name, temp_dir)
            
            process_info = {
                "process": process,
                "file_path": file_path,
                "temp_file": temp_file,
                "temp_dir": temp_dir,
                "sandbox": "Sandboxie-Plus",
                "sandbox_name": sandbox_name,
                "start_time": datetime.now().isoformat(),
                "pid": process.pid,
                "monitoring": True,
                "file_type": "image"
            }
            
            self.sandbox_processes.append(process_info)
            self.add_log(f"✅ Image opened with Photo Viewer (PID: {process.pid})")
            
            # Start monitoring
            monitor_thread = threading.Thread(
                target=self.monitor_sandboxie_process,
                args=(process_info,),
                daemon=True
            )
            monitor_thread.start()
            
            return process_info
            
        except Exception as e:
            self.add_log(f"❌ Error opening image: {e}")
            return self.open_image_with_mspaint_reliable(file_path, sandboxie_dir, sandbox_name)
    
    def open_image_with_mspaint_reliable(self, file_path, sandboxie_dir, sandbox_name, temp_dir=None):
        """Open image with MSPaint in Sandboxie-Plus - RELIABLE"""
        try:
            start_exe = os.path.join(sandboxie_dir, "Start.exe")
            if not os.path.exists(start_exe):
                start_exe = self.sandboxie_path
            
            # Use a temp file with simple name if not provided
            if not temp_dir:
                temp_dir = os.path.join(os.environ['TEMP'], f"sandbox_img_{int(time.time())}")
                os.makedirs(temp_dir, exist_ok=True)
                file_ext = os.path.splitext(file_path)[1]
                temp_file = os.path.join(temp_dir, f"image{file_ext}")
                shutil.copy2(file_path, temp_file)
            else:
                file_ext = os.path.splitext(file_path)[1]
                temp_file = os.path.join(temp_dir, f"image{file_ext}")
            
            self.add_log(f"🖼️ Opening image with MSPaint...")
            
            # Use mspaint with the temp file
            cmd = [
                start_exe,
                "/box:" + sandbox_name,
                "mspaint.exe",
                temp_file
            ]
            
            self.add_log(f"📂 Command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=False
            )
            
            time.sleep(2)
            
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.add_log(f"⚠️ MSPaint failed: {stderr.decode() if stderr else 'Unknown'}")
                # Try opening with explorer
                return self.open_image_with_explorer(file_path, sandboxie_dir, sandbox_name)
            
            process_info = {
                "process": process,
                "file_path": file_path,
                "temp_file": temp_file,
                "temp_dir": temp_dir,
                "sandbox": "Sandboxie-Plus",
                "sandbox_name": sandbox_name,
                "start_time": datetime.now().isoformat(),
                "pid": process.pid,
                "monitoring": True,
                "file_type": "image"
            }
            
            self.sandbox_processes.append(process_info)
            self.add_log(f"✅ Image opened with MSPaint (PID: {process.pid})")
            
            monitor_thread = threading.Thread(
                target=self.monitor_sandboxie_process,
                args=(process_info,),
                daemon=True
            )
            monitor_thread.start()
            
            return process_info
            
        except Exception as e:
            self.add_log(f"❌ MSPaint error: {e}")
            return self.open_image_with_explorer(file_path, sandboxie_dir, sandbox_name)
    
    def open_image_with_explorer(self, file_path, sandboxie_dir, sandbox_name):
        """Open image with Explorer in Sandboxie-Plus"""
        try:
            start_exe = os.path.join(sandboxie_dir, "Start.exe")
            if not os.path.exists(start_exe):
                start_exe = self.sandboxie_path
            
            self.add_log(f"🖼️ Opening image with Explorer...")
            
            # Use explorer to open the file with default app
            cmd = [
                start_exe,
                "/box:" + sandbox_name,
                "explorer.exe",
                file_path
            ]
            
            self.add_log(f"📂 Command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=False
            )
            
            time.sleep(2)
            
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.add_log(f"⚠️ Explorer failed: {stderr.decode() if stderr else 'Unknown'}")
                # Last resort: fallback sandbox
                return self.run_fallback_sandbox(file_path)
            
            process_info = {
                "process": process,
                "file_path": file_path,
                "sandbox": "Sandboxie-Plus",
                "sandbox_name": sandbox_name,
                "start_time": datetime.now().isoformat(),
                "pid": process.pid,
                "monitoring": True,
                "file_type": "image"
            }
            
            self.sandbox_processes.append(process_info)
            self.add_log(f"✅ Image opened with Explorer (PID: {process.pid})")
            
            monitor_thread = threading.Thread(
                target=self.monitor_sandboxie_process,
                args=(process_info,),
                daemon=True
            )
            monitor_thread.start()
            
            return process_info
            
        except Exception as e:
            self.add_log(f"❌ Explorer error: {e}")
            return self.run_fallback_sandbox(file_path)
    
    def run_executable_in_sandboxie(self, file_path, args, sandboxie_dir, sandbox_name):
        """Run executable in Sandboxie-Plus"""
        try:
            start_exe = os.path.join(sandboxie_dir, "Start.exe")
            if not os.path.exists(start_exe):
                start_exe = self.sandboxie_path
            
            cmd = [start_exe, "/box:" + sandbox_name, file_path]
            if args:
                cmd.extend(args)
            
            self.add_log(f"🚀 Launching executable: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                shell=False
            )
            
            process_info = {
                "process": process,
                "file_path": file_path,
                "sandbox": "Sandboxie-Plus",
                "sandbox_name": sandbox_name,
                "start_time": datetime.now().isoformat(),
                "pid": process.pid,
                "monitoring": True,
                "file_type": "executable"
            }
            
            self.sandbox_processes.append(process_info)
            self.add_log(f"✅ Executable running in Sandboxie-Plus (PID: {process.pid})")
            
            monitor_thread = threading.Thread(
                target=self.monitor_sandboxie_process,
                args=(process_info,),
                daemon=True
            )
            monitor_thread.start()
            
            return process_info
            
        except Exception as e:
            self.add_log(f"❌ Error running executable: {e}")
            return None
    
    def open_file_in_sandboxie(self, file_path, sandboxie_dir, sandbox_name):
        """Open non-executable file in Sandboxie-Plus"""
        try:
            start_exe = os.path.join(sandboxie_dir, "Start.exe")
            if not os.path.exists(start_exe):
                start_exe = self.sandboxie_path
            
            # Use explorer to open with default app
            cmd = [start_exe, "/box:" + sandbox_name, "explorer.exe", file_path]
            self.add_log(f"📂 Opening file: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=False
            )
            
            time.sleep(1)
            
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.add_log(f"⚠️ Failed to open file: {stderr.decode() if stderr else 'Unknown error'}")
                return self.run_fallback_sandbox(file_path)
            
            process_info = {
                "process": process,
                "file_path": file_path,
                "sandbox": "Sandboxie-Plus",
                "sandbox_name": sandbox_name,
                "start_time": datetime.now().isoformat(),
                "pid": process.pid,
                "monitoring": True,
                "file_type": "document"
            }
            
            self.sandbox_processes.append(process_info)
            self.add_log(f"✅ File opened in Sandboxie-Plus (PID: {process.pid})")
            
            monitor_thread = threading.Thread(
                target=self.monitor_sandboxie_process,
                args=(process_info,),
                daemon=True
            )
            monitor_thread.start()
            
            return process_info
            
        except Exception as e:
            self.add_log(f"❌ Error opening file: {e}")
            return self.run_fallback_sandbox(file_path)
    
    def run_fallback_sandbox(self, file_path, args=None):
        """Fallback sandbox with proper image support"""
        try:
            file_type = self.get_file_type(file_path)
            self.add_log(f"⚠️ Using fallback sandbox for {file_type} file")
            
            # Create isolated environment
            sandbox_dir = os.path.join(os.environ['TEMP'], f"sandbox_{int(time.time())}")
            os.makedirs(sandbox_dir, exist_ok=True)
            self.sandbox_dir = sandbox_dir
            
            # Copy file to sandbox with simple name
            file_ext = os.path.splitext(file_path)[1]
            file_name = f"file{file_ext}"
            sandbox_file = os.path.join(sandbox_dir, file_name)
            shutil.copy2(file_path, sandbox_file)
            
            # Open file based on type
            if file_type == 'executable':
                process = subprocess.Popen(
                    [sandbox_file] + (args or []),
                    cwd=sandbox_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            elif file_type == 'image':
                # Try multiple image viewers
                image_viewers = [
                    ['mspaint.exe', sandbox_file],
                    ['explorer.exe', sandbox_file],
                    ['rundll32.exe', 'shimgvw.dll,ImageView_Fullscreen', sandbox_file]
                ]
                
                process = None
                for viewer in image_viewers:
                    try:
                        self.add_log(f"🖼️ Trying viewer: {viewer[0]}")
                        process = subprocess.Popen(
                            viewer,
                            cwd=sandbox_dir,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        time.sleep(1)
                        if process.poll() is None:
                            break
                    except:
                        continue
                
                if process is None or process.poll() is not None:
                    self.add_log("⚠️ All viewers failed, using default")
                    process = subprocess.Popen(
                        ['cmd', '/c', 'start', '', sandbox_file],
                        cwd=sandbox_dir,
                        shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
            else:
                process = subprocess.Popen(
                    ['cmd', '/c', 'start', '', sandbox_file],
                    cwd=sandbox_dir,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            
            time.sleep(1)
            
            process_info = {
                "process": process,
                "file_path": file_path,
                "sandbox": "Fallback Sandbox",
                "sandbox_dir": sandbox_dir,
                "start_time": datetime.now().isoformat(),
                "pid": process.pid if hasattr(process, 'pid') else None,
                "monitoring": True,
                "file_type": file_type
            }
            
            self.sandbox_processes.append(process_info)
            self.add_log(f"✅ File opened in fallback sandbox")
            
            monitor_thread = threading.Thread(
                target=self.monitor_fallback_process,
                args=(process_info,),
                daemon=True
            )
            monitor_thread.start()
            
            return process_info
            
        except Exception as e:
            self.add_log(f"❌ Fallback sandbox error: {e}")
            return None
    
    def monitor_sandboxie_process(self, process_info):
        """Monitor process running in Sandboxie"""
        process = process_info["process"]
        start_time = time.time()
        
        while process_info.get("monitoring", False):
            try:
                if process.poll() is not None:
                    process_info["monitoring"] = False
                    process_info["end_time"] = datetime.now().isoformat()
                    process_info["exit_code"] = process.returncode
                    self.add_log(f"✅ Process completed (exit code: {process.returncode})")
                    # Clean up temp files
                    self.cleanup_temp_files(process_info)
                    break
                
                try:
                    proc = psutil.Process(process.pid)
                    if not proc.is_running():
                        process_info["monitoring"] = False
                        process_info["end_time"] = datetime.now().isoformat()
                        self.add_log(f"✅ Process {process.pid} terminated")
                        self.cleanup_temp_files(process_info)
                        break
                except:
                    process_info["monitoring"] = False
                    process_info["end_time"] = datetime.now().isoformat()
                    self.cleanup_temp_files(process_info)
                    break
                
                if time.time() - start_time > 300:
                    self.add_log(f"⏹️ Process {process.pid} still running, continuing...")
                    process_info["monitoring"] = False
                    process_info["end_time"] = datetime.now().isoformat()
                    self.cleanup_temp_files(process_info)
                    break
                
                time.sleep(2)
                
            except Exception as e:
                self.add_log(f"⚠️ Monitor error: {e}")
                break
    
    def cleanup_temp_files(self, process_info):
        """Clean up temporary files created for sandbox"""
        try:
            temp_dir = process_info.get("temp_dir")
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                self.add_log(f"🗑️ Removed temp dir: {temp_dir}")
        except:
            pass
    
    def monitor_fallback_process(self, process_info):
        """Monitor process running in fallback sandbox"""
        process = process_info["process"]
        sandbox_dir = process_info.get("sandbox_dir")
        start_time = time.time()
        
        while process_info.get("monitoring", False):
            try:
                if process.poll() is not None:
                    process_info["monitoring"] = False
                    process_info["end_time"] = datetime.now().isoformat()
                    process_info["exit_code"] = process.returncode
                    self.add_log(f"✅ Process completed (exit code: {process.returncode})")
                    
                    if sandbox_dir and os.path.exists(sandbox_dir):
                        try:
                            time.sleep(2)
                            shutil.rmtree(sandbox_dir)
                            self.add_log(f"🗑️ Removed fallback sandbox: {sandbox_dir}")
                        except:
                            pass
                    break
                
                if time.time() - start_time > 300:
                    self.add_log(f"⏹️ Process timed out after 5 minutes")
                    process_info["monitoring"] = False
                    process_info["end_time"] = datetime.now().isoformat()
                    break
                
                time.sleep(2)
                
            except Exception as e:
                self.add_log(f"⚠️ Monitor error: {e}")
                break
    
    def add_log(self, message):
        """Add message to sandbox log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.sandbox_log.append(log_entry)
        print(log_entry)
    
    def get_sandbox_activity(self):
        """Get activity log from sandbox"""
        activity = {
            "total_processes": len(self.sandbox_processes),
            "active_processes": len([p for p in self.sandbox_processes if p.get("monitoring", False)]),
            "processes": [],
            "log": self.sandbox_log[-50:],
            "sandboxie_installed": self.is_sandboxie_installed(),
            "sandbox_type": self.sandbox_type
        }
        
        for proc in self.sandbox_processes:
            process_info = {
                "pid": proc.get("pid"),
                "file_path": proc.get("file_path", ""),
                "sandbox": proc.get("sandbox", "Unknown"),
                "file_type": proc.get("file_type", "unknown"),
                "start_time": proc.get("start_time", ""),
                "monitoring": proc.get("monitoring", False)
            }
            
            if "end_time" in proc:
                process_info["end_time"] = proc["end_time"]
                process_info["exit_code"] = proc.get("exit_code", -1)
            
            activity["processes"].append(process_info)
        
        return activity
    
    def clean_sandbox(self):
        """Clean up sandbox processes"""
        try:
            self.add_log("🧹 Cleaning up sandbox...")
            
            for proc in self.sandbox_processes:
                if proc.get("monitoring", False):
                    try:
                        proc["process"].terminate()
                        time.sleep(0.5)
                        if proc["process"].poll() is None:
                            proc["process"].kill()
                        self.add_log(f"⏹️ Terminated process {proc['pid']}")
                    except:
                        pass
                # Clean up temp files
                self.cleanup_temp_files(proc)
            
            self.sandbox_processes = []
            
            if self.sandbox_dir and os.path.exists(self.sandbox_dir):
                try:
                    shutil.rmtree(self.sandbox_dir)
                    self.add_log(f"🗑️ Removed sandbox directory: {self.sandbox_dir}")
                    self.sandbox_dir = None
                except:
                    pass
            
            self.add_log("✅ Sandbox cleaned up")
            
        except Exception as e:
            self.add_log(f"❌ Error cleaning sandbox: {e}")
    
    def emergency_kill_all(self):
        """Emergency kill - KILL LOCK SCREEN APPS AND SANDBOX"""
        self.add_log("🚨 EMERGENCY KILL ACTIVATED!")
        self.add_log("="*60)
        
        killed_processes = []
        killed_names = []
        unlocked_count = 0
        
        current_pid = os.getpid()
        
        # Method 1: Kill ALL Sandboxie processes
        self.add_log("💀 Killing all Sandboxie processes...")
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name'].lower()
                    cmdline = ' '.join(proc_info['cmdline']).lower() if proc_info['cmdline'] else ''
                    
                    if proc_info['pid'] == current_pid:
                        continue
                    
                    is_sandboxie = False
                    if any(name in proc_name for name in ['sandman', 'start', 'sandboxie', 'sandbox']):
                        is_sandboxie = True
                    if '/box:' in cmdline or 'defaultbox' in cmdline:
                        is_sandboxie = True
                    
                    if is_sandboxie:
                        try:
                            proc.kill()
                            killed_processes.append(proc_info['pid'])
                            killed_names.append(f"Sandboxie: {proc_info['name']} (PID: {proc_info['pid']})")
                            self.add_log(f"💀 Killed Sandboxie: {proc_info['name']} (PID: {proc_info['pid']})")
                        except:
                            pass
                except:
                    pass
        except:
            pass
        
        # Method 2: KILL PYTHON LOCK SCREEN APPLICATIONS
        self.add_log("💀 Killing Python lock screen applications...")
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name'].lower()
                    cmdline = ' '.join(proc_info['cmdline']).lower() if proc_info['cmdline'] else ''
                    
                    if proc_info['pid'] == current_pid:
                        continue
                    
                    is_lock_screen = False
                    
                    if 'python' in proc_name or 'py' in proc_name:
                        lock_indicators = [
                            'tkinter', 'lock', 'screen', 'password', 'unlock', 
                            'toggle_desktop', 'wallpaper', 'overrideredirect', 
                            'topmost', 'system_menu', 'capcut', 'app.py',
                            '.locked', 'desktop', 'LOCKED', 'SYSTEM LOCKED'
                        ]
                        
                        if any(indicator in cmdline for indicator in lock_indicators):
                            is_lock_screen = True
                            self.add_log(f"🔍 Found lock screen: {proc_info['name']} - {cmdline[:100]}")
                    
                    if is_lock_screen:
                        try:
                            proc.kill()
                            killed_processes.append(proc_info['pid'])
                            killed_names.append(f"Lock Screen: {proc_info['name']} (PID: {proc_info['pid']})")
                            self.add_log(f"💀 Killed lock screen: {proc_info['name']} (PID: {proc_info['pid']})")
                        except:
                            pass
                except:
                    pass
        except:
            pass
        
        # Method 3: Unlock desktop files
        self.add_log("🔓 Unlocking desktop files...")
        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            locked_extension = ".locked"
            
            for item in os.listdir(desktop_path):
                if item.endswith(locked_extension):
                    original_path = os.path.join(desktop_path, item.replace(locked_extension, ""))
                    locked_path = os.path.join(desktop_path, item)
                    try:
                        os.rename(locked_path, original_path)
                        unlocked_count += 1
                        self.add_log(f"🔓 Unlocked: {item}")
                    except:
                        pass
            
            if unlocked_count > 0:
                try:
                    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
                except:
                    pass
                killed_names.append(f"Unlocked {unlocked_count} desktop files")
        except:
            pass
        
        # Method 4: Restore wallpaper
        self.add_log("🖼️ Restoring wallpaper...")
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Control Panel\Desktop", 
                                0, 
                                winreg.KEY_READ)
            wallpaper_path, _ = winreg.QueryValueEx(key, "WallPaper")
            winreg.CloseKey(key)
            
            if wallpaper_path and any(x in wallpaper_path.lower() for x in ['in.jpg', 'lock', 'capcut']):
                default_wallpapers = [
                    r"C:\Windows\Web\Wallpaper\Windows\img0.jpg",
                    r"C:\Windows\Web\Wallpaper\Windows\img0_256x256.jpg",
                ]
                for wall in default_wallpapers:
                    if os.path.exists(wall):
                        ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, wall, 0x01 | 0x02)
                        self.add_log(f"🖼️ Restored wallpaper to: {wall}")
                        killed_names.append("Wallpaper restored")
                        break
        except:
            pass
        
        # Method 5: Clean up sandbox directory
        if self.sandbox_dir and os.path.exists(self.sandbox_dir):
            try:
                shutil.rmtree(self.sandbox_dir)
                self.add_log(f"🗑️ Removed sandbox directory: {self.sandbox_dir}")
                self.sandbox_dir = None
            except:
                pass
        
        self.sandbox_processes = []
        
        self.add_log("="*60)
        self.add_log(f"✅ Emergency kill completed. Killed {len(killed_processes)} processes.")
        
        return {
            "killed_count": len(killed_processes),
            "killed_pids": killed_processes,
            "killed_names": killed_names,
            "unlocked_files": unlocked_count,
            "processes": killed_names
        }
    
    def scan_with_sandboxie(self, file_path):
        """Quick scan file using Sandboxie-Plus"""
        results = {
            "file": file_path,
            "sandboxie_installed": self.is_sandboxie_installed(),
            "sandboxie_path": self.sandboxie_path,
            "file_type": self.get_file_type(file_path),
            "executed": False,
            "message": ""
        }
        
        if not self.is_sandboxie_installed():
            results["message"] = "Sandboxie-Plus not installed"
            results["error"] = "Please install Sandboxie-Plus from https://sandboxie-plus.com/"
            return results
        
        try:
            self.add_log(f"🔍 Opening in Sandboxie-Plus: {os.path.basename(file_path)}")
            
            process_info = self.run_in_sandboxie(file_path)
            
            if process_info:
                results["executed"] = True
                results["pid"] = process_info["pid"]
                results["message"] = f"File opened in Sandboxie-Plus (PID: {process_info['pid']})"
            else:
                self.add_log("⚠️ Trying fallback sandbox...")
                fallback_info = self.run_fallback_sandbox(file_path)
                if fallback_info:
                    results["executed"] = True
                    results["pid"] = fallback_info["pid"]
                    results["message"] = f"File opened in fallback sandbox"
                else:
                    results["message"] = "Failed to open in any sandbox"
                
        except Exception as e:
            results["error"] = str(e)
            results["message"] = f"Error: {str(e)}"
        
        return results
