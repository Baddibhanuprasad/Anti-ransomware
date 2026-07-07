import os
import hashlib
import shutil
from datetime import datetime
import tempfile

class DeceptionScanner:
    def __init__(self):
        self.canary_files = []
        self.canary_dir = None
        self.setup_canary_files()
    
    def setup_canary_files(self):
        """Set up canary files"""
        self.canary_dir = tempfile.mkdtemp(prefix="canary_")
        
        # Create realistic canary files
        canary_templates = [
            {"name": "important_business_data.docx", "content": "canary_marker_001"},
            {"name": "confidential_financial.xlsx", "content": "canary_marker_002"},
            {"name": "personal_photos_2024.jpg", "content": "canary_marker_003"},
            {"name": "backup_archive.zip", "content": "canary_marker_004"},
            {"name": "system_config.ini", "content": "canary_marker_005"},
            {"name": "database_backup.sql", "content": "canary_marker_006"},
            {"name": "project_source_code.cpp", "content": "canary_marker_007"},
            {"name": "email_archive.pst", "content": "canary_marker_008"}
        ]
        
        self.canary_files = []
        for template in canary_templates:
            file_path = os.path.join(self.canary_dir, template["name"])
            with open(file_path, 'w') as f:
                f.write(template["content"])
            
            file_hash = self.calculate_hash(file_path)
            self.canary_files.append({
                "path": file_path,
                "name": template["name"],
                "hash": file_hash,
                "original_content": template["content"],
                "status": "clean"
            })
    
    def calculate_hash(self, file_path):
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def scan_with_canary(self, file_path):
        """Monitor canary files"""
        try:
            results = {
                "threat_detected": False,
                "threat_description": "",
                "canary_status": [],
                "triggered_canaries": [],
                "scan_time": datetime.now().isoformat(),
                "confidence": "low"
            }
            
            # Only check for executables
            if not file_path.lower().endswith(('.exe', '.scr', '.dll')):
                results["note"] = "Canary detection only applies to executable files"
                return results
            
            # Check canary files
            triggered_count = 0
            for canary in self.canary_files:
                status = self.check_canary_file(canary)
                results["canary_status"].append(status)
                
                if status["modified"]:
                    triggered_count += 1
                    results["triggered_canaries"].append(canary["name"])
            
            # Determine threat based on number of triggered canaries
            if triggered_count >= 3:
                results["threat_detected"] = True
                results["threat_description"] = f"Multiple canary files modified ({triggered_count}) - potential ransomware activity"
                results["confidence"] = "high"
            elif triggered_count >= 1:
                results["threat_detected"] = True
                results["threat_description"] = f"Canary file modified: {results['triggered_canaries'][0]}"
                results["confidence"] = "medium"
            
            return results
            
        except Exception as e:
            return {"error": f"Deception scan error: {str(e)}", "threat_detected": False}
    
    def check_canary_file(self, canary):
        status = {
            "name": canary["name"],
            "path": canary["path"],
            "modified": False,
            "current_hash": "",
            "previous_hash": canary["hash"],
            "timestamp": datetime.now().isoformat()
        }
        
        if os.path.exists(canary["path"]):
            current_hash = self.calculate_hash(canary["path"])
            status["current_hash"] = current_hash
            
            if current_hash != canary["hash"]:
                status["modified"] = True
        else:
            status["modified"] = True
            status["deleted"] = True
        
        return status
    
    def cleanup(self):
        try:
            shutil.rmtree(self.canary_dir)
        except:
            pass