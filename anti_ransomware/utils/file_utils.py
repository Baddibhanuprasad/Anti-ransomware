import os
import json
import hashlib
import shutil
from datetime import datetime

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file"""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_file_info(file_path):
    """Get detailed file information"""
    if not os.path.exists(file_path):
        return None
    
    stat = os.stat(file_path)
    return {
        "path": file_path,
        "name": os.path.basename(file_path),
        "size": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
        "is_file": os.path.isfile(file_path),
        "is_dir": os.path.isdir(file_path)
    }

def backup_file(file_path, backup_dir=None):
    """Create a backup of a file"""
    if not os.path.exists(file_path):
        return None
    
    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(file_path), "backup")
    
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(file_path)
    backup_path = os.path.join(backup_dir, f"{filename}.{timestamp}.backup")
    
    shutil.copy2(file_path, backup_path)
    return backup_path

def restore_file(backup_path, restore_path):
    """Restore file from backup"""
    if not os.path.exists(backup_path):
        return False
    
    shutil.copy2(backup_path, restore_path)
    return True