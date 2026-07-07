import os
import hashlib
import pefile
import re
from datetime import datetime
import struct

class SmartScanner:
    def __init__(self):
        # Ransomware behavior patterns
        self.ransomware_behaviors = {
            # File manipulation patterns
            'file_hiding': {
                'weight': 20,
                'patterns': [
                    'hidden', 'hide', 'lock', 'unlock', 'toggle_desktop',
                    'os.listdir', 'os.rename', 'shutil.move'
                ]
            },
            'wallpaper_changes': {
                'weight': 15,
                'patterns': [
                    'set_wallpaper', 'change_wallpaper', 'desktop_wallpaper',
                    'SPI_SETDESKWALLPAPER', 'SystemParametersInfo'
                ]
            },
            'registry_modification': {
                'weight': 15,
                'patterns': [
                    'winreg', 'SetValue', 'CreateKey', 'RegSetValue',
                    'HKEY_CURRENT_USER', 'HKEY_LOCAL_MACHINE'
                ]
            },
            'password_protection': {
                'weight': 10,
                'patterns': [
                    'password', 'unlock', 'authentication', 'verify_password',
                    'check_password', 'enter password'
                ]
            },
            # Encryption indicators
            'encryption': {
                'weight': 25,
                'patterns': [
                    'encrypt', 'decrypt', 'crypt', '.encrypted', '.locked',
                    'encryption_key', 'decryption_key', 'AES', 'RSA'
                ]
            },
            # System manipulation
            'system_control': {
                'weight': 15,
                'patterns': [
                    'ctypes.windll', 'user32', 'kernel32', 'SetWindowLong',
                    'overrideredirect', 'topmost', 'system_menu'
                ]
            }
        }
        
        # Legitimate software patterns (to avoid false positives)
        self.legitimate_patterns = {
            'browser': {
                'patterns': ['chrome', 'firefox', 'opera', 'edge', 'browser'],
                'exceptions': ['lock', 'screen', 'password', 'wallpaper']
            },
            'media_player': {
                'patterns': ['vlc', 'videolan', 'media', 'player', 'codec'],
                'exceptions': ['lock', 'screen', 'password', 'wallpaper']
            },
            'office': {
                'patterns': ['word', 'excel', 'powerpoint', 'outlook', 'office'],
                'exceptions': ['lock', 'screen', 'password']
            }
        }
    
    def scan_file(self, file_path):
        """Behavior-based ransomware detection"""
        try:
            results = {
                "threat_detected": False,
                "threat_level": "clean",
                "threat_description": "",
                "confidence": "low",
                "threat_score": 0,
                "detections": [],
                "scan_time": datetime.now().isoformat(),
                "file_classification": ""
            }
            
            if not os.path.exists(file_path):
                results["error"] = "File does not exist"
                return results
            
            filename = os.path.basename(file_path).lower()
            
            # 1. Check if it's legitimate software (Chrome, Opera, VLC)
            if self.is_legitimate_software(filename):
                results["threat_detected"] = False
                results["threat_level"] = "clean"
                results["threat_description"] = f"Legitimate software: {filename}"
                results["confidence"] = "high"
                results["threat_score"] = 0
                results["file_classification"] = "legitimate"
                return results
            
            # 2. Check if it's a known browser/media player
            if self.is_browser_or_media_player(filename):
                results["threat_detected"] = False
                results["threat_level"] = "clean"
                results["threat_description"] = f"Legitimate browser/media player: {filename}"
                results["confidence"] = "high"
                results["threat_score"] = 0
                results["file_classification"] = "legitimate"
                return results
            
            # 3. Analyze the file (only for PE files)
            if file_path.lower().endswith(('.exe', '.dll', '.sys')):
                behavior_score = self.analyze_behavior(file_path)
                
                if behavior_score >= 50:
                    results["threat_detected"] = True
                    results["threat_level"] = "critical"
                    results["threat_description"] = "CRITICAL: Ransomware-like behavior detected"
                    results["confidence"] = "high"
                    results["threat_score"] = behavior_score
                    results["file_classification"] = "ransomware"
                elif behavior_score >= 30:
                    results["threat_detected"] = True
                    results["threat_level"] = "high"
                    results["threat_description"] = "HIGH: Suspicious ransomware behavior"
                    results["confidence"] = "medium"
                    results["threat_score"] = behavior_score
                    results["file_classification"] = "suspicious"
                elif behavior_score >= 15:
                    results["threat_detected"] = True
                    results["threat_level"] = "medium"
                    results["threat_description"] = "MEDIUM: Potential malicious behavior"
                    results["confidence"] = "low"
                    results["threat_score"] = behavior_score
                    results["file_classification"] = "potentially_malicious"
                else:
                    results["threat_detected"] = False
                    results["threat_level"] = "clean"
                    results["threat_description"] = "No malicious behavior detected"
                    results["confidence"] = "medium"
                    results["file_classification"] = "clean"
            
            return results
            
        except Exception as e:
            return {"error": f"Smart scan error: {str(e)}", "threat_detected": False}
    
    def is_legitimate_software(self, filename):
        """Check if file is legitimate software"""
        # Exact matches for legitimate executables
        legitimate_exact = [
            'vlc.exe', 'videolan.exe', 'chrome.exe', 'firefox.exe', 
            'opera.exe', 'msedge.exe', 'winword.exe', 'excel.exe',
            'powerpnt.exe', 'outlook.exe', 'acrobat.exe', 'reader.exe'
        ]
        
        if filename in legitimate_exact:
            return True
        
        # Check if it's from a legitimate publisher
        legitimate_publishers = ['google', 'mozilla', 'videolan', 'microsoft', 'adobe']
        for publisher in legitimate_publishers:
            if publisher in filename:
                return True
        
        return False
    
    def is_browser_or_media_player(self, filename):
        """Check if file is a browser or media player"""
        browsers = ['chrome', 'firefox', 'opera', 'edge', 'brave', 'safari']
        media_players = ['vlc', 'videolan', 'media', 'player', 'mpc', 'wmplayer']
        
        for browser in browsers:
            if browser in filename and not any(term in filename for term in ['lock', 'screen', 'password']):
                return True
        
        for player in media_players:
            if player in filename and not any(term in filename for term in ['lock', 'screen', 'password']):
                return True
        
        return False
    
    def analyze_behavior(self, file_path):
        """Analyze file for ransomware behavior patterns"""
        score = 0
        detections = []
        
        try:
            # Read file content (up to 2MB)
            with open(file_path, 'rb') as f:
                content = f.read(1024 * 1024 * 2)  # 2MB
                content_str = str(content).lower()
                
                # Check each behavior pattern
                for behavior, data in self.ransomware_behaviors.items():
                    weight = data['weight']
                    patterns = data['patterns']
                    
                    found_patterns = []
                    for pattern in patterns:
                        if pattern.lower() in content_str:
                            found_patterns.append(pattern)
                    
                    if found_patterns:
                        score += weight
                        detections.append(f"{behavior}: {', '.join(found_patterns[:2])}")
                
                # Special detection: Lock screen applications
                # Check for specific lock screen patterns
                lock_screen_patterns = [
                    'overrideredirect', 'topmost', 'system_menu',
                    'unlock', 'password', 'enter password',
                    'drag window', 'prevent close'
                ]
                
                lock_count = 0
                for pattern in lock_screen_patterns:
                    if pattern in content_str:
                        lock_count += 1
                
                if lock_count >= 3:
                    score += 20
                    detections.append(f"Lock screen application detected ({lock_count} patterns)")
                
                # Check for desktop manipulation
                desktop_patterns = ['desktop', 'DESKTOP_PATH', 'toggle_desktop', 'os.rename']
                desktop_count = 0
                for pattern in desktop_patterns:
                    if pattern in content_str:
                        desktop_count += 1
                
                if desktop_count >= 2:
                    score += 15
                    detections.append("Desktop file manipulation detected")
                
                # Check for wallpaper manipulation
                if 'wallpaper' in content_str or 'SPI_SETDESKWALLPAPER' in content_str:
                    score += 15
                    detections.append("Wallpaper manipulation detected")
                
                # Check for registry operations
                if 'winreg' in content_str or 'CreateKey' in content_str:
                    score += 10
                    detections.append("Registry operations detected")
                
                # Check for system control
                if 'ctypes.windll' in content_str or 'user32' in content_str:
                    score += 5
                    detections.append("Windows API usage detected")
                
                # Special check: Is it trying to prevent closing?
                if 'prevent_close' in content_str or 'WM_DELETE_WINDOW' in content_str:
                    score += 10
                    detections.append("Anti-close mechanisms detected")
                
        except Exception as e:
            print(f"Behavior analysis error: {e}")
        
        # Store detections for later use
        self.last_detections = detections
        
        return score
    
    def get_ransomware_detections(self, file_path):
        """Get specific ransomware detections"""
        detections = []
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1024 * 1024)
                content_str = str(content).lower()
                
                # Check for specific malicious patterns
                malicious_patterns = {
                    'File locking': ['lock', 'unlock', 'toggle_desktop', 'os.rename'],
                    'Wallpaper change': ['wallpaper', 'SPI_SETDESKWALLPAPER'],
                    'Password protection': ['password', 'unlock', 'authentication'],
                    'System manipulation': ['topmost', 'overrideredirect', 'system_menu'],
                    'Anti-close': ['prevent_close', 'WM_DELETE_WINDOW'],
                    'Registry modification': ['winreg', 'CreateKey', 'SetValue'],
                    'Desktop manipulation': ['DESKTOP_PATH', 'os.listdir']
                }
                
                for category, patterns in malicious_patterns.items():
                    for pattern in patterns:
                        if pattern in content_str:
                            detections.append(f"{category}: {pattern}")
                            break
                            
        except:
            pass
        
        return detections