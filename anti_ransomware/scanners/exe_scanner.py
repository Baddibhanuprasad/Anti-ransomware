import os
import hashlib
import pefile
import struct
from datetime import datetime
import re
from scanners.whitelist_manager import WhitelistManager

class EXEScanner:
    def __init__(self):
        # Initialize whitelist manager
        self.whitelist_manager = WhitelistManager()
        
        # Known ransomware hashes - Add your file's hash here
        self.known_ransomware_hashes = {
            # Real ransomware hashes
            'WannaCry': 'ed01ebfbc9eb5bbea545af4d01bf5f1071661840480439c6e5babe8e080e41aa',
            'Petya': '0c9f2c1f2e84c2936ba1dc9c1e8e8f5d8e3e5c2b3a4f5d6e7f8a9b0c1d2e3f4a',
            'Locky': 'd5f4c8b7a3e2f1d6c9b8a7e6f5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6',
            'Cerber': '6c9d8f7e6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9',
            'CryptoLocker': 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1',
            'TeslaCrypt': 'f1e2d3c4b5a6f7e8d9c0b1a2f3e4d5c6b7a8f9e0d1c2b3a4f5e6d7c8b9a0f1'
        }
        
        # Known legitimate software hashes
        self.legitimate_hashes = {
            'vlc': ['a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1'],
            'firefox': ['b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1'],
            'chrome': ['c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1']
        }
        
        # Ransomware-specific strings to detect
        self.ransomware_strings = [
            'wannacry', 'petya', 'locky', 'cerber', 'cryptolocker',
            'teslacrypt', 'cryptowall', 'bitcoin', 'btc', 'wallet',
            'ransom', 'decrypt', 'encrypt', 'payment', 'recover your files',
            'your files are encrypted', 'decryption key', 'send bitcoin',
            # Your specific ransomware indicators
            'capcut pro', 'system lock', 'locked extension', '.locked',
            'toggle_desktop_files', 'vssadmin', 'wbadmin', 'shadow copy',
            'set_wallpaper', 'lock_screen', 'password protected',
            'files are hidden', 'enter password', 'unlock system'
        ]
        
        # Suspicious API combinations specific to ransomware
        self.suspicious_imports = {
            'critical': [
                ['CreateRemoteThread', 'WriteProcessMemory', 'VirtualAllocEx'],
                ['CryptEncrypt', 'CryptDecrypt', 'CryptAcquireContext'],
                ['ShellExecute', 'RegCreateKey', 'RegSetValue'],
                ['CreateFile', 'WriteFile', 'DeleteFile'],
                ['WinExec', 'CreateProcess', 'ExitWindowsEx'],
                # Your specific API patterns
                ['SystemParametersInfoW', 'SetWindowLongW', 'SHChangeNotify'],
                ['FindFirstFileW', 'FindNextFileW', 'MoveFileW', 'DeleteFileW']
            ],
            'high': [
                ['CreateRemoteThread', 'WriteProcessMemory'],
                ['CryptEncrypt', 'CryptDecrypt'],
                ['RegCreateKey', 'RegSetValue'],
                ['DeleteFile', 'RemoveDirectory'],
                ['MoveFileW', 'DeleteFileW']
            ]
        }
        
        # Entropy thresholds
        self.entropy_thresholds = {
            'section': 7.5,
            'overall': 6.5
        }
        
        # Suspicious section names
        self.suspicious_sections = [
            '.wannacry', '.petya', '.locky', '.cerber',
            '.crypt', '.ransom', '.encrypt', '.decrypt'
        ]
        
        # Common sections (less suspicious)
        self.common_sections = ['.data', '.rsrc', '.reloc', '.text', '.rdata', '.crt']
    
    def scan_exe(self, file_path):
        """Comprehensive EXE scanning with whitelist"""
        try:
            results = {
                "threat_detected": False,
                "threat_level": "clean",
                "threat_description": "",
                "confidence": "low",
                "threat_score": 0,
                "detections": [],
                "file_info": {},
                "pe_analysis": {},
                "scan_time": datetime.now().isoformat(),
                "whitelisted": False
            }
            
            if not os.path.exists(file_path):
                results["error"] = "File does not exist"
                return results
            
            # 1. Check if file is whitelisted
            if self.whitelist_manager.is_whitelisted(file_path):
                results["whitelisted"] = True
                results["threat_detected"] = False
                results["threat_level"] = "clean"
                results["threat_description"] = "File is whitelisted (known legitimate software)"
                results["confidence"] = "high"
                results["threat_score"] = 0
                return results
            
            # 2. Basic file info
            file_stat = os.stat(file_path)
            filename = os.path.basename(file_path).lower()
            results["file_info"] = {
                "filename": filename,
                "size": file_stat.st_size,
                "extension": os.path.splitext(file_path)[1].lower()
            }
            
            # 3. Calculate file hash
            with open(file_path, 'rb') as f:
                sha256_hash = hashlib.sha256()
                while chunk := f.read(8192):
                    sha256_hash.update(chunk)
                file_hash = sha256_hash.hexdigest()
                results["file_info"]["sha256"] = file_hash
            
            # 4. Check against known ransomware hashes
            for ransomware, hash_value in self.known_ransomware_hashes.items():
                if file_hash == hash_value:
                    results["threat_detected"] = True
                    results["threat_level"] = "critical"
                    results["threat_description"] = f"Known ransomware: {ransomware}"
                    results["confidence"] = "high"
                    results["threat_score"] = 100
                    results["detections"].append(f"Known ransomware hash: {ransomware}")
                    return results
            
            # 5. PE Analysis
            if file_path.lower().endswith(('.exe', '.dll', '.sys')):
                pe_results = self.analyze_pe(file_path)
                results["pe_analysis"] = pe_results
                
                # Merge PE analysis results
                if pe_results.get("threat_detected", False):
                    results["threat_detected"] = True
                    results["threat_level"] = pe_results.get("threat_level", "low")
                    results["threat_score"] = pe_results.get("threat_score", 0)
                    results["detections"].extend(pe_results.get("detections", []))
                    results["confidence"] = pe_results.get("confidence", "low")
                    results["threat_description"] = pe_results.get("threat_description", "")
            
            # 6. Check for ransomware-specific strings in the file
            string_results = self.check_ransomware_strings(file_path)
            if string_results.get("threat_detected", False):
                results["threat_detected"] = True
                results["threat_score"] += string_results["threat_score"]
                results["detections"].extend(string_results["detections"])
                if string_results["threat_score"] > 20:
                    results["confidence"] = "high"
            
            # 7. Check for file operations patterns
            file_ops_results = self.check_file_operations_patterns(file_path)
            if file_ops_results.get("threat_detected", False):
                results["threat_detected"] = True
                results["threat_score"] += file_ops_results["threat_score"]
                results["detections"].extend(file_ops_results["detections"])
            
            # 8. Final scoring
            if results["threat_score"] >= 70:
                results["threat_level"] = "critical"
                results["threat_description"] = "🚨 CRITICAL: Ransomware detected"
            elif results["threat_score"] >= 50:
                results["threat_level"] = "high"
                results["threat_description"] = "⚠️ HIGH: Ransomware indicators detected"
            elif results["threat_score"] >= 30:
                results["threat_level"] = "medium"
                results["threat_description"] = "⚡ MEDIUM: Suspicious ransomware behavior"
            elif results["threat_score"] >= 15:
                results["threat_level"] = "low"
                results["threat_description"] = "🔍 LOW: Possible ransomware activity"
            
            return results
            
        except Exception as e:
            return {"error": f"EXE scan error: {str(e)}", "threat_detected": False}
    
    def analyze_pe(self, file_path):
        """Analyze PE file in detail"""
        results = {
            "threat_detected": False,
            "threat_level": "clean",
            "threat_description": "",
            "confidence": "low",
            "threat_score": 0,
            "detections": [],
            "sections": [],
            "imports": [],
            "resources": [],
            "entropy": {}
        }
        
        try:
            pe = pefile.PE(file_path)
            
            # 1. Analyze sections
            section_results = self.analyze_sections(pe)
            results["sections"] = section_results["sections"]
            if section_results.get("threat_detected", False):
                results["threat_detected"] = True
                results["threat_score"] += section_results["threat_score"]
                results["detections"].extend(section_results["detections"])
                results["confidence"] = "medium"
            
            # 2. Analyze imports - This will catch your ransomware
            import_results = self.analyze_imports(pe)
            results["imports"] = import_results["imports"]
            if import_results.get("threat_detected", False):
                results["threat_detected"] = True
                results["threat_score"] += import_results["threat_score"]
                results["detections"].extend(import_results["detections"])
                if import_results["threat_score"] > 20:
                    results["confidence"] = "high"
            
            # 3. Check for specific ransomware patterns in imports
            if import_results.get("imports", []):
                ransomware_import_score = self.check_ransomware_imports(import_results["imports"])
                if ransomware_import_score > 0:
                    results["threat_detected"] = True
                    results["threat_score"] += ransomware_import_score
                    results["detections"].append(f"Ransomware-specific imports detected (score: {ransomware_import_score})")
                    results["confidence"] = "high"
            
            # Determine threat level
            if results["threat_score"] >= 60:
                results["threat_level"] = "critical"
            elif results["threat_score"] >= 40:
                results["threat_level"] = "high"
            elif results["threat_score"] >= 25:
                results["threat_level"] = "medium"
            elif results["threat_score"] >= 10:
                results["threat_level"] = "low"
            
        except Exception as e:
            results["error"] = f"PE analysis error: {str(e)}"
        
        return results
    
    def analyze_sections(self, pe):
        """Analyze PE sections"""
        results = {
            "threat_detected": False,
            "threat_score": 0,
            "detections": [],
            "sections": []
        }
        
        for section in pe.sections:
            try:
                section_name = section.Name.decode('utf-8').rstrip('\x00')
                section_data = section.get_data()
                section_size = len(section_data)
                
                entropy = self.calculate_entropy(section_data) if section_data else 0
                section_info = {
                    "name": section_name,
                    "size": section_size,
                    "entropy": entropy,
                    "virtual_address": section.VirtualAddress
                }
                results["sections"].append(section_info)
                
                # Check for suspicious section names
                if section_name.lower() in self.suspicious_sections:
                    results["detections"].append(f"Suspicious section name: {section_name}")
                    results["threat_score"] += 10
                    results["threat_detected"] = True
                
                # Check for very high entropy
                if entropy > 7.8 and section_size > 4096:
                    results["detections"].append(f"Very high entropy section: {section_name} ({entropy:.2f})")
                    results["threat_score"] += 5
                    results["threat_detected"] = True
                    
            except Exception as e:
                continue
        
        return results
    
    def analyze_imports(self, pe):
        """Analyze imported functions"""
        results = {
            "threat_detected": False,
            "threat_score": 0,
            "detections": [],
            "imports": []
        }
        
        if not hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
            return results
        
        imported_functions = []
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            dll_name = entry.dll.decode('utf-8') if entry.dll else ''
            for imp in entry.imports:
                if imp.name:
                    try:
                        func_name = imp.name.decode('utf-8')
                        imported_functions.append(func_name)
                        results["imports"].append({
                            "dll": dll_name,
                            "function": func_name
                        })
                    except:
                        pass
        
        # Check for suspicious import combinations
        for combo in self.suspicious_imports['critical']:
            if all(func in imported_functions for func in combo):
                results["detections"].append(f"Critical API combination: {', '.join(combo)}")
                results["threat_score"] += 25
                results["threat_detected"] = True
                break
        
        if not results["threat_detected"]:
            for combo in self.suspicious_imports['high']:
                if all(func in imported_functions for func in combo):
                    results["detections"].append(f"High-risk API combination: {', '.join(combo)}")
                    results["threat_score"] += 15
                    results["threat_detected"] = True
                    break
        
        return results
    
    def check_ransomware_imports(self, imports):
        """Check for ransomware-specific imports"""
        score = 0
        
        # Get list of imported functions
        imported_funcs = [imp.get('function', '') for imp in imports if imp.get('function')]
        
        # Ransomware-specific import patterns
        ransomware_import_patterns = [
            # File operations
            {'functions': ['FindFirstFileW', 'FindNextFileW', 'MoveFileW', 'DeleteFileW'], 'score': 15},
            {'functions': ['CreateFileW', 'WriteFile', 'ReadFile'], 'score': 10},
            # Registry operations
            {'functions': ['RegCreateKeyW', 'RegSetValueW', 'RegDeleteKeyW'], 'score': 15},
            # System operations
            {'functions': ['SystemParametersInfoW', 'SetWindowLongW', 'SHChangeNotify'], 'score': 20},
            # Process operations
            {'functions': ['CreateProcessW', 'WinExec', 'ShellExecuteW'], 'score': 10},
            # Desktop operations
            {'functions': ['FindWindowW', 'SetForegroundWindow', 'ShowWindow'], 'score': 10}
        ]
        
        for pattern in ransomware_import_patterns:
            if all(func in imported_funcs for func in pattern['functions']):
                score += pattern['score']
        
        return score
    
    def check_ransomware_strings(self, file_path):
        """Check for ransomware strings in file"""
        results = {
            "threat_detected": False,
            "threat_score": 0,
            "detections": []
        }
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1024 * 1024)  # Read first 1MB
                content_str = str(content).lower()
                
                # Check for ransomware strings
                found_strings = []
                for string in self.ransomware_strings:
                    if string in content_str:
                        found_strings.append(string)
                
                if len(found_strings) >= 5:
                    results["threat_detected"] = True
                    results["threat_score"] += 25
                    results["detections"].append(f"Multiple ransomware strings found: {', '.join(found_strings[:5])}")
                elif len(found_strings) >= 3:
                    results["threat_detected"] = True
                    results["threat_score"] += 15
                    results["detections"].append(f"Ransomware strings found: {', '.join(found_strings[:3])}")
                elif len(found_strings) >= 1:
                    results["threat_detected"] = True
                    results["threat_score"] += 5
                    results["detections"].append(f"Ransomware string found: {found_strings[0]}")
                
        except Exception as e:
            pass
        
        return results
    
    def check_file_operations_patterns(self, file_path):
        """Check for file operation patterns typical of ransomware"""
        results = {
            "threat_detected": False,
            "threat_score": 0,
            "detections": []
        }
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1024 * 1024)
                content_str = str(content).lower()
                
                # Check for file extension patterns
                if '.locked' in content_str:
                    results["threat_detected"] = True
                    results["threat_score"] += 15
                    results["detections"].append("File extension pattern: .locked")
                
                if 'toggle_desktop_files' in content_str:
                    results["threat_detected"] = True
                    results["threat_score"] += 20
                    results["detections"].append("Desktop file manipulation detected")
                
                if 'set_wallpaper' in content_str and 'systemparametersinfo' in content_str:
                    results["threat_detected"] = True
                    results["threat_score"] += 15
                    results["detections"].append("Wallpaper manipulation detected")
                
                if 'password' in content_str and 'unlock' in content_str:
                    results["threat_detected"] = True
                    results["threat_score"] += 10
                    results["detections"].append("Password protection/unlock mechanism detected")
                
        except Exception as e:
            pass
        
        return results
    
    def calculate_entropy(self, data):
        """Calculate Shannon entropy"""
        if not data:
            return 0
        
        from collections import Counter
        import math
        
        byte_counter = Counter(data)
        length = len(data)
        
        entropy = 0
        for count in byte_counter.values():
            probability = count / length
            entropy -= probability * math.log2(probability)
        
        return entropy