import os
import re
import psutil
from datetime import datetime

class HeuristicScanner:
    def __init__(self):
        # Real ransomware behavioral patterns
        self.ransomware_behavior = {
            'shadow_copy_deletion': ['vssadmin delete shadows', 'wbadmin delete catalog'],
            'recovery_disable': ['bcdedit /set recoveryenabled no'],
            'encryption': ['cipher /e', '/encrypt'],
            'process_injection': ['CreateRemoteThread', 'WriteProcessMemory']
        }
    
    def scan_file(self, file_path):
        """Perform heuristic/behavioral analysis"""
        try:
            results = {
                "threat_detected": False,
                "threat_description": "",
                "behavioral_indicators": [],
                "scan_time": datetime.now().isoformat(),
                "confidence": "low"
            }
            
            if not os.path.exists(file_path):
                results["error"] = "File does not exist"
                return results
            
            # Only analyze executables
            if not file_path.lower().endswith(('.exe', '.dll', '.sys', '.scr')):
                return results
            
            # Check for behavioral patterns in the file
            behavior_found = self.analyze_file_behavior(file_path)
            
            if behavior_found:
                results["threat_detected"] = True
                results["threat_description"] = "Suspicious behavioral patterns detected"
                results["behavioral_indicators"].extend(behavior_found)
                results["confidence"] = "medium" if len(behavior_found) >= 2 else "low"
            
            return results
            
        except Exception as e:
            return {"error": f"Heuristic scan error: {str(e)}", "threat_detected": False}
    
    def analyze_file_behavior(self, file_path):
        """Analyze file for behavioral patterns"""
        indicators = []
        
        try:
            # Check for ransomware-related strings in file
            with open(file_path, 'rb') as f:
                content = f.read(4096)  # Read first 4KB
                content_str = str(content).lower()
                
                # Check for shadow copy deletion commands
                for pattern in self.ransomware_behavior['shadow_copy_deletion']:
                    if pattern in content_str:
                        indicators.append(f"Shadow copy deletion command: {pattern}")
                
                # Check for recovery disable commands
                for pattern in self.ransomware_behavior['recovery_disable']:
                    if pattern in content_str:
                        indicators.append(f"Recovery disable command: {pattern}")
                
                # Check for encryption commands
                for pattern in self.ransomware_behavior['encryption']:
                    if pattern in content_str:
                        indicators.append(f"Encryption command: {pattern}")
                
                # Check for process injection patterns
                for pattern in self.ransomware_behavior['process_injection']:
                    if pattern in content_str:
                        indicators.append(f"Process injection API: {pattern}")
                
                # Check for Bitcoin/crypto mentions
                crypto_patterns = ['bitcoin', 'btc', 'wallet', 'cryptocurrency']
                for pattern in crypto_patterns:
                    if pattern in content_str:
                        indicators.append(f"Crypto reference: {pattern}")
                        break
                
                # Check for ransom demands
                ransom_patterns = ['ransom', 'decrypt', 'payment', 'recover your files']
                for pattern in ransom_patterns:
                    if pattern in content_str:
                        indicators.append(f"Ransom note phrase: {pattern}")
                        break
        
        except Exception as e:
            print(f"Behavior analysis error: {e}")
        
        return indicators