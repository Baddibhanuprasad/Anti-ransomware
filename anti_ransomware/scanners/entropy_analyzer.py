import os
import math
from collections import Counter
import numpy as np
from datetime import datetime

class EntropyAnalyzer:
    def __init__(self):
        # Known file types and their typical entropy ranges
        self.file_type_entropy = {
            '.txt': (3.0, 5.0),
            '.pdf': (5.0, 7.5),
            '.docx': (6.0, 7.5),
            '.xlsx': (6.0, 7.5),
            '.zip': (6.5, 8.0),
            '.rar': (6.5, 8.0),
            '.jpg': (6.0, 7.8),
            '.png': (6.0, 7.8),
            '.mp4': (6.5, 7.8),
            '.exe': (4.0, 7.0),
            '.dll': (4.0, 6.5),
            '.py': (3.0, 5.5),
            '.js': (3.5, 5.5),
            '.css': (3.5, 5.5),
            '.html': (3.5, 5.5)
        }
        
        # High entropy threshold (above this is suspicious)
        self.high_entropy_threshold = 7.8
    
    def analyze_file(self, file_path):
        """Perform comprehensive entropy analysis"""
        try:
            results = {
                "threat_detected": False,
                "threat_description": "",
                "entropy_metrics": {},
                "scan_time": datetime.now().isoformat(),
                "confidence": "low"
            }
            
            if not os.path.exists(file_path):
                results["error"] = "File does not exist"
                return results
            
            file_size = os.path.getsize(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            results["entropy_metrics"]["file_size"] = file_size
            results["entropy_metrics"]["extension"] = ext
            
            # Skip tiny files
            if file_size < 1024:
                results["entropy_metrics"]["note"] = "File too small for entropy analysis"
                return results
            
            # Read file in blocks
            block_size = 4096
            entropies = []
            high_entropy_blocks = 0
            total_blocks = 0
            
            with open(file_path, 'rb') as f:
                while True:
                    block = f.read(block_size)
                    if not block:
                        break
                    
                    entropy = self.calculate_entropy(block)
                    entropies.append(entropy)
                    total_blocks += 1
                    
                    if entropy > self.high_entropy_threshold:
                        high_entropy_blocks += 1
            
            if entropies:
                avg_entropy = np.mean(entropies)
                max_entropy = np.max(entropies)
                min_entropy = np.min(entropies)
                std_entropy = np.std(entropies)
                high_entropy_pct = (high_entropy_blocks / total_blocks * 100) if total_blocks > 0 else 0
                
                results["entropy_metrics"]["average_entropy"] = avg_entropy
                results["entropy_metrics"]["max_entropy"] = max_entropy
                results["entropy_metrics"]["min_entropy"] = min_entropy
                results["entropy_metrics"]["std_entropy"] = std_entropy
                results["entropy_metrics"]["high_entropy_percentage"] = high_entropy_pct
                
                # Check against expected entropy for this file type
                if ext in self.file_type_entropy:
                    expected_min, expected_max = self.file_type_entropy[ext]
                    
                    # Check if entropy is significantly different from expected
                    if avg_entropy > expected_max + 1.0:
                        # Entropy is much higher than expected for this file type
                        results["threat_detected"] = True
                        results["threat_description"] = f"Entropy ({avg_entropy:.2f}) significantly higher than expected for {ext} files ({expected_max:.2f})"
                        results["confidence"] = "medium"
                    
                    elif avg_entropy < expected_min - 1.0:
                        # Entropy is much lower than expected (could be corrupted or malicious)
                        results["threat_detected"] = True
                        results["threat_description"] = f"Entropy ({avg_entropy:.2f}) significantly lower than expected for {ext} files ({expected_min:.2f})"
                        results["confidence"] = "medium"
                else:
                    # Unknown file type - check if entropy is extremely high
                    if avg_entropy > self.high_entropy_threshold and high_entropy_pct > 80:
                        # Check if it contains ransomware markers
                        if self.check_ransomware_markers(file_path):
                            results["threat_detected"] = True
                            results["threat_description"] = f"High entropy ({avg_entropy:.2f}) with ransomware markers"
                            results["confidence"] = "high"
                        else:
                            # Flag as suspicious but with lower confidence
                            results["threat_detected"] = True
                            results["threat_description"] = f"Unusually high entropy ({avg_entropy:.2f}) in unknown file type"
                            results["confidence"] = "low"
            
            return results
            
        except Exception as e:
            return {"error": f"Entropy analysis error: {str(e)}", "threat_detected": False}
    
    def calculate_entropy(self, data):
        """Calculate Shannon entropy of data"""
        if not data:
            return 0
        
        byte_counter = Counter(data)
        length = len(data)
        
        entropy = 0
        for count in byte_counter.values():
            probability = count / length
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def check_ransomware_markers(self, file_path):
        """Check for ransomware markers in file content"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(2048)
                header_str = str(header).lower()
                
                ransomware_markers = [
                    'wannacry', 'petya', 'locky', 'cerber', 'cryptolocker',
                    'teslacrypt', 'bitcoin', 'btc', 'wallet', 'ransom',
                    'decrypt', 'encrypt', 'payment', 'recover your files'
                ]
                
                marker_count = 0
                for marker in ransomware_markers:
                    if marker in header_str:
                        marker_count += 1
                
                return marker_count >= 2
        except:
            pass
        
        return False