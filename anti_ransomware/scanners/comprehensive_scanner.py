import os
from datetime import datetime
from scanners.smart_scanner import SmartScanner
from scanners.whitelist_manager import WhitelistManager

class ComprehensiveScanner:
    def __init__(self):
        self.smart_scanner = SmartScanner()
        self.whitelist_manager = WhitelistManager()
        self.threat_score = 0
        self.detections = []
    
    def analyze(self, file_path, scanner_results):
        """Comprehensive analysis"""
        results = {
            "threat_detected": False,
            "threat_level": "clean",
            "threat_description": "",
            "confidence": "high",
            "threat_score": 0,
            "detections_found": [],
            "recommendation": "",
            "scan_time": datetime.now().isoformat()
        }
        
        filename = os.path.basename(file_path).lower()
        
        # 1. Check if it's legitimate software (Chrome, Opera, VLC)
        if self.is_legitimate_software(filename):
            results["threat_detected"] = False
            results["threat_level"] = "clean"
            results["threat_description"] = "Legitimate software"
            results["confidence"] = "high"
            results["threat_score"] = 0
            results["recommendation"] = "✅ This is legitimate software"
            results["file_classification"] = "legitimate"
            return results
        
        # 2. Check whitelist
        if self.whitelist_manager.is_whitelisted(file_path):
            results["threat_detected"] = False
            results["threat_level"] = "clean"
            results["threat_description"] = "File is whitelisted"
            results["confidence"] = "high"
            results["threat_score"] = 0
            results["recommendation"] = "✅ File is known to be safe"
            return results
        
        # 3. Run smart scan
        smart_results = self.smart_scanner.scan_file(file_path)
        
        # 4. Check if it's a lock screen application (should be detected as threat)
        if self.is_lock_screen_application(file_path):
            # Override detection to show as threat
            smart_results["threat_detected"] = True
            smart_results["threat_level"] = "critical"
            smart_results["threat_score"] = max(smart_results.get("threat_score", 0), 65)
            smart_results["threat_description"] = "CRITICAL: Lock screen/ransomware mimic application"
            smart_results["confidence"] = "high"
            if "Lock screen application" not in str(smart_results.get("detections", [])):
                if "detections" not in smart_results:
                    smart_results["detections"] = []
                smart_results["detections"].append("Lock screen application (mimics ransomware behavior)")
        
        # 5. Apply results
        if smart_results.get("threat_detected", False):
            results["threat_detected"] = True
            results["threat_score"] = smart_results.get("threat_score", 0)
            results["detections_found"] = smart_results.get("detections", [])
            results["threat_level"] = smart_results.get("threat_level", "low")
            results["confidence"] = smart_results.get("confidence", "low")
            results["threat_description"] = smart_results.get("threat_description", "")
            results["file_classification"] = smart_results.get("file_classification", "malicious")
            
            # Determine recommendation
            if results["threat_score"] >= 50:
                results["recommendation"] = "🚨 CRITICAL: Ransomware/Lock screen detected! Quarantine immediately!"
            elif results["threat_score"] >= 30:
                results["recommendation"] = "⚠️ HIGH RISK: Suspicious behavior detected. Review carefully."
            elif results["threat_score"] >= 15:
                results["recommendation"] = "⚡ MEDIUM RISK: Potential malicious behavior. Monitor this file."
            else:
                results["recommendation"] = "🔍 LOW RISK: Minor suspicious indicators."
        else:
            results["threat_detected"] = False
            results["threat_level"] = "clean"
            results["threat_description"] = "No threats detected"
            results["confidence"] = "high"
            results["recommendation"] = "✅ File appears clean"
        
        return results
    
    def is_legitimate_software(self, filename):
        """Check if file is legitimate software"""
        # Exact matches for legitimate executables
        legitimate_exact = [
            'vlc.exe', 'videolan.exe', 'chrome.exe', 'firefox.exe', 
            'opera.exe', 'msedge.exe', 'winword.exe', 'excel.exe',
            'powerpnt.exe', 'outlook.exe', 'acrobat.exe', 'reader.exe',
            'devenv.exe', 'code.exe', 'python.exe', 'java.exe'
        ]
        
        if filename in legitimate_exact:
            return True
        
        # Check for legitimate prefixes
        legitimate_prefixes = ['google', 'mozilla', 'videolan', 'microsoft', 'adobe']
        for prefix in legitimate_prefixes:
            if filename.startswith(prefix):
                return True
        
        # Check for browsers and media players
        browsers = ['chrome', 'firefox', 'opera', 'edge', 'brave']
        media_players = ['vlc', 'videolan', 'media player', 'wmplayer']
        
        for browser in browsers:
            if browser in filename and 'lock' not in filename and 'screen' not in filename:
                return True
        
        for player in media_players:
            if player in filename and 'lock' not in filename and 'screen' not in filename:
                return True
        
        return False
    
    def is_lock_screen_application(self, file_path):
        """Check if file is a lock screen application"""
        try:
            # Check filename
            filename = os.path.basename(file_path).lower()
            lock_keywords = ['lock', 'screen', 'unlock', 'password', 'login']
            
            if any(keyword in filename for keyword in lock_keywords):
                return True
            
            # Check file content for lock screen patterns
            with open(file_path, 'rb') as f:
                content = f.read(1024 * 1024)  # Read 1MB
                content_str = str(content).lower()
                
                lock_patterns = [
                    'overrideredirect', 'topmost', 'system_menu',
                    'password', 'unlock', 'enter password',
                    'drag window', 'prevent close', 'WM_DELETE_WINDOW',
                    'toggle_desktop', 'DESKTOP_PATH', 'set_wallpaper'
                ]
                
                pattern_count = 0
                for pattern in lock_patterns:
                    if pattern in content_str:
                        pattern_count += 1
                
                # If it has multiple lock screen patterns, it's a lock screen app
                if pattern_count >= 3:
                    return True
                
        except:
            pass
        
        return False