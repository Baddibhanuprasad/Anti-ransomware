import os
import hashlib
import json

class WhitelistManager:
    def __init__(self):
        self.whitelist = {
            # Known legitimate software hashes (add more as needed)
            'hashes': {},
            # Known legitimate software signatures
            'signatures': {
                'vlc': ['vlc.exe', 'videolan', 'libvlc'],
                'firefox': ['firefox.exe', 'mozilla'],
                'chrome': ['chrome.exe', 'google'],
                'office': ['winword.exe', 'excel.exe', 'powerpnt.exe', 'outlook.exe'],
                'adobe': ['acrobat.exe', 'reader.exe'],
                'visual_studio': ['devenv.exe', 'msbuild.exe'],
                'vscode': ['code.exe'],
                'python': ['python.exe', 'python3.exe'],
                'java': ['java.exe', 'javaw.exe'],
                'git': ['git.exe'],
                'docker': ['docker.exe'],
                'vmware': ['vmware.exe', 'vmware-vmx.exe'],
                'virtualbox': ['virtualbox.exe'],
                'steam': ['steam.exe'],
                'discord': ['discord.exe'],
                'spotify': ['spotify.exe'],
                'telegram': ['telegram.exe'],
                'whatsapp': ['whatsapp.exe'],
                'zoom': ['zoom.exe'],
                'teamviewer': ['teamviewer.exe'],
                'anydesk': ['anydesk.exe']
            },
            # Known legitimate file paths
            'paths': [
                r'C:\Program Files',
                r'C:\Program Files (x86)',
                r'C:\Windows',
                r'C:\Users\*\AppData\Local\Programs',
                r'C:\Python*',
                r'C:\Users\*\AppData\Roaming\Microsoft\Windows\Start Menu\Programs',
                r'C:\Users\*\Desktop',
                r'C:\Users\*\Downloads'
            ],
            # Known legitimate publishers (from digital signatures)
            'publishers': [
                'VideoLAN', 'Microsoft Corporation', 'Google Inc', 'Google LLC',
                'Mozilla Corporation', 'Adobe Systems', 'Adobe Inc',
                'Oracle Corporation', 'VMware Inc', 'Docker Inc',
                'Valve Corporation', 'Discord Inc', 'Spotify AB',
                'Telegram FZ-LLC', 'WhatsApp Inc', 'Zoom Video Communications',
                'TeamViewer GmbH', 'AnyDesk Software GmbH'
            ]
        }
        
        # Load whitelist from file if exists
        self.load_whitelist()
    
    def load_whitelist(self):
        """Load whitelist from JSON file"""
        try:
            whitelist_file = os.path.join(os.path.dirname(__file__), 'whitelist.json')
            if os.path.exists(whitelist_file):
                with open(whitelist_file, 'r') as f:
                    data = json.load(f)
                    self.whitelist['hashes'].update(data.get('hashes', {}))
        except:
            pass
    
    def save_whitelist(self):
        """Save whitelist to JSON file"""
        try:
            whitelist_file = os.path.join(os.path.dirname(__file__), 'whitelist.json')
            with open(whitelist_file, 'w') as f:
                json.dump(self.whitelist, f, indent=2)
        except:
            pass
    
    def is_whitelisted(self, file_path):
        """Check if a file is whitelisted"""
        try:
            if not os.path.exists(file_path):
                return False
            
            filename = os.path.basename(file_path).lower()
            
            # 1. Check by file path
            for path_pattern in self.whitelist['paths']:
                if self.match_path_pattern(file_path, path_pattern):
                    return True
            
            # 2. Check by signature
            for app_name, signatures in self.whitelist['signatures'].items():
                for sig in signatures:
                    if sig.lower() in filename:
                        # Additional verification - check if it's in a legitimate location
                        if self.is_in_legitimate_location(file_path):
                            return True
            
            # 3. Check by hash (if we have it)
            file_hash = self.calculate_hash(file_path)
            if file_hash in self.whitelist['hashes']:
                return True
            
            # 4. Check by digital signature publisher
            publisher = self.get_digital_signature_publisher(file_path)
            if publisher in self.whitelist['publishers']:
                return True
            
            return False
            
        except Exception as e:
            return False
    
    def match_path_pattern(self, file_path, pattern):
        """Match file path against a pattern"""
        import fnmatch
        return fnmatch.fnmatch(file_path.lower(), pattern.lower())
    
    def is_in_legitimate_location(self, file_path):
        """Check if file is in a legitimate location"""
        file_path = file_path.lower()
        legitimate_locations = [
            r'c:\program files',
            r'c:\program files (x86)',
            r'c:\windows',
            r'c:\users\*\appdata\local\programs',
            r'c:\users\*\appdata\local\microsoft',
            r'c:\users\*\appdata\roaming\microsoft',
            r'c:\python',
            r'c:\users\*\desktop',
            r'c:\users\*\downloads'
        ]
        
        for location in legitimate_locations:
            if location.replace('*', '') in file_path:
                return True
        return False
    
    def calculate_hash(self, file_path):
        """Calculate SHA-256 hash of file"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return None
    
    def get_digital_signature_publisher(self, file_path):
        """Get publisher from digital signature (Windows only)"""
        try:
            import win32api
            import win32security
            
            # Check if file has digital signature
            try:
                # This is a simplified check - in reality, you'd use WinVerifyTrust
                # For now, we'll just check if the file is signed
                info = win32api.GetFileVersionInfo(file_path, '\\')
                if 'CompanyName' in info:
                    return info['CompanyName']
            except:
                pass
        except:
            pass
        
        return None
    
    def add_to_whitelist(self, file_path):
        """Add a file to the whitelist"""
        try:
            file_hash = self.calculate_hash(file_path)
            if file_hash:
                filename = os.path.basename(file_path)
                self.whitelist['hashes'][file_hash] = {
                    'filename': filename,
                    'path': file_path,
                    'added': 'auto'
                }
                self.save_whitelist()
                return True
        except:
            pass
        return False