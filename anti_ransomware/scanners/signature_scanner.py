import hashlib
import os
import re
import pefile
from datetime import datetime

class SignatureScanner:
    def __init__(self):
        # Real ransomware signatures
        self.ransomware_signatures = {
            'wannacry': ['wannacry', 'mssecsvc', 'tasksche'],
            'petya': ['petya', 'notpetya', 'perfc'],
            'locky': ['locky', 'locky.exe'],
            'cerber': ['cerber', 'crypt'],
            'cryptolocker': ['cryptolocker', 'cryptolocker.exe'],
            'teslacrypt': ['teslacrypt', 'teslacrypt.exe']
        }
        
        # High-risk API combinations
        self.suspicious_api_combinations = [
            ['CryptEncrypt', 'CryptDecrypt', 'CreateRemoteThread'],
            ['WriteProcessMemory', 'VirtualAllocEx', 'CreateRemoteThread'],
            ['ShellExecute', 'RegCreateKey', 'RegSetValue']
        ]
    
    def scan_file(self, file_path):
        """Scan file using signature-based detection"""
        try:
            results = {
                "threat_detected": False,
                "threat_description": "",
                "signatures_found": [],
                "file_hash": "",
                "file_size": 0,
                "file_extension": "",
                "scan_time": datetime.now().isoformat(),
                "confidence": "low"
            }
            
            if not os.path.exists(file_path):
                results["error"] = "File does not exist"
                return results
            
            # Get file info
            file_stat = os.stat(file_path)
            results["file_size"] = file_stat.st_size
            results["file_extension"] = os.path.splitext(file_path)[1].lower()
            
            # Calculate file hash
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
                results["file_hash"] = file_hash.hexdigest()
            
            # Check for known ransomware signatures in filename
            filename = os.path.basename(file_path).lower()
            for ransomware, signatures in self.ransomware_signatures.items():
                for sig in signatures:
                    if sig in filename:
                        results["threat_detected"] = True
                        results["threat_description"] = f"Known ransomware signature: {ransomware}"
                        results["signatures_found"].append(f"Ransomware: {ransomware} (signature: {sig})")
                        results["confidence"] = "high"
                        return results
            
            # Analyze PE files
            if results["file_extension"] in ['.exe', '.dll', '.sys']:
                pe_results = self.scan_pe_file(file_path)
                if pe_results.get("threat_detected", False):
                    results["threat_detected"] = True
                    results["threat_description"] = pe_results.get("threat_description", "")
                    results["signatures_found"].extend(pe_results.get("signatures_found", []))
                    results["confidence"] = pe_results.get("confidence", "medium")
            
            return results
            
        except Exception as e:
            return {"error": f"Scan error: {str(e)}", "threat_detected": False}
    
    def scan_pe_file(self, file_path):
        """Scan PE file for suspicious characteristics"""
        results = {
            "threat_detected": False,
            "threat_description": "",
            "signatures_found": [],
            "confidence": "low"
        }
        
        try:
            pe = pefile.PE(file_path)
            
            # Check for known ransomware sections
            for section in pe.sections:
                try:
                    section_name = section.Name.decode('utf-8').rstrip('\x00').lower()
                    # Known ransomware section names
                    if any(ransomware in section_name for ransomware in ['wannacry', 'petya', 'locky', 'cerber']):
                        results["threat_detected"] = True
                        results["threat_description"] = f"Known ransomware section: {section_name}"
                        results["signatures_found"].append(f"Ransomware section: {section_name}")
                        results["confidence"] = "high"
                        return results
                except:
                    pass
            
            # Check API imports
            if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
                imported_apis = []
                for entry in pe.DIRECTORY_ENTRY_IMPORT:
                    for imp in entry.imports:
                        if imp.name:
                            try:
                                api_name = imp.name.decode('utf-8')
                                imported_apis.append(api_name)
                            except:
                                pass
                
                # Check for suspicious API combinations
                for combo in self.suspicious_api_combinations:
                    if all(api in imported_apis for api in combo):
                        results["threat_detected"] = True
                        results["threat_description"] = f"Suspicious API combination: {', '.join(combo)}"
                        results["signatures_found"].append(f"API combination: {', '.join(combo)}")
                        results["confidence"] = "high"
                        break
                
                # Check for ransomware-specific APIs
                ransomware_apis = ['CryptEncrypt', 'CryptDecrypt', 'CreateRemoteThread', 'WriteProcessMemory']
                found_ransomware_apis = [api for api in ransomware_apis if api in imported_apis]
                if len(found_ransomware_apis) >= 2:
                    results["threat_detected"] = True
                    results["threat_description"] = f"Multiple ransomware-related APIs: {', '.join(found_ransomware_apis)}"
                    results["signatures_found"].append(f"Ransomware APIs: {', '.join(found_ransomware_apis)}")
                    results["confidence"] = "medium"
            
        except Exception as e:
            results["error"] = f"PE parsing error: {str(e)}"
        
        return results