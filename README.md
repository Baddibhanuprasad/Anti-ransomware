# Anti-Ransomware Protection System

Desktop anti-ransomware utility for Windows built with `PyQt5`. The application combines several lightweight detection layers, USB drive monitoring, and sandbox-based file opening to help inspect suspicious files before running them on the host system.

## Overview

This project is a GUI-first security tool that:

- scans selected files with multiple detection techniques
- monitors the system for suspicious new processes
- watches removable USB drives and alerts when one is inserted
- opens files or USB content inside `Sandboxie-Plus` when available
- provides a fallback sandbox workflow when `Sandboxie-Plus` is not installed
- includes an emergency cleanup feature aimed at stopping sandboxed or ransomware-mimic lock-screen behavior

The main application entry point is `main.py`, which starts the `PyQt5` app and opens `AntiRansomwareUI` from `ui/main_window.py`.

## Features

- `SmartScanner` behavior scoring for ransomware-like patterns
- `SignatureScanner` checks for known ransomware names and suspicious PE imports
- `HeuristicScanner` scans executables for shadow-copy deletion, recovery disable, encryption, and ransom-note strings
- `EntropyAnalyzer` flags files whose entropy is far outside the expected range for their type
- `DeceptionScanner` creates temporary canary files and checks whether they were modified
- `ComprehensiveScanner` combines smart scan results with whitelist checks and final recommendations
- `USBMonitor` detects removable drives and triggers large on-screen warnings
- `USBScanner` inspects USB content for executables, suspicious extensions, and `autorun.inf`
- `SandboxManager` launches files in `Sandboxie-Plus` or a fallback temporary sandbox directory
- emergency kill flow to stop sandbox-related processes, unlock `.locked` desktop files, and attempt wallpaper recovery

## Project Structure

```text
anti_ransomware/
├── main.py
├── requirements.txt
├── sandbox/
│   └── sandbox_manager.py
├── scanners/
│   ├── comprehensive_scanner.py
│   ├── deception_scanner.py
│   ├── entropy_analyzer.py
│   ├── exe_scanner.py
│   ├── heuristic_scanner.py
│   ├── process_monitor.py
│   ├── signature_scanner.py
│   ├── smart_scanner.py
│   ├── usb_monitor.py
│   └── whitelist_manager.py
├── ui/
│   ├── main_window.py
│   └── sandbox_dialog.py
└── utils/
    └── file_utils.py
```

## How It Works

### 1. Main UI

`ui/main_window.py` provides the primary desktop interface with tabs for:

- scan log
- scan results
- detailed analysis
- USB drives
- sandbox status
- about information

When the app starts, it also:

- initializes all scanners
- starts background process monitoring
- starts USB monitoring
- checks whether `Sandboxie-Plus` is installed

### 2. File Scanning Pipeline

When a user selects a file and clicks scan, a `QThread` runs:

1. `SmartScanner`
2. selected individual scanners:
   - `SignatureScanner`
   - `HeuristicScanner`
   - `EntropyAnalyzer`
   - `DeceptionScanner`
3. `ComprehensiveScanner`

The UI then merges results into:

- a color-coded summary table
- a detailed text report
- threat popups for medium, high, or critical findings

### 3. USB Protection

`USBMonitor` polls for removable drives every 2 seconds using Windows APIs. On insertion it:

- logs the event
- refreshes the USB list
- gathers drive metadata
- shows a large alert dialog
- allows the user to:
  - open the USB in sandbox
  - open normally
  - cancel

`USBScanner` can scan one or all detected USB drives and flags:

- many executable files
- suspicious scriptable extensions like `.vbs`, `.js`, `.scr`, `.jar`, `.com`
- `autorun.inf`

### 4. Sandbox Flow

`SandboxManager` tries to use `Sandboxie-Plus` first by launching `Start.exe` with the configured box. If `Sandboxie-Plus` is missing or launch fails, it falls back to:

- copying the file into a temporary directory
- launching it from that directory
- monitoring the spawned process
- cleaning the temp sandbox after exit when possible

The sandbox dialog in `ui/sandbox_dialog.py` exposes:

- sandbox status
- execution log
- cleanup
- emergency kill

## Module Notes

### `scanners/smart_scanner.py`

Primary behavior scoring engine. Looks for patterns related to:

- file locking or hiding
- wallpaper changes
- registry modification
- password-based lock screens
- encryption references
- Windows API system control

It also contains allowlist-style logic for common legitimate software such as browsers, office apps, and media players.

### `scanners/signature_scanner.py`

Checks:

- filename matches against known ransomware families
- PE section names
- suspicious imported API combinations
- multiple ransomware-related APIs in PE files

### `scanners/heuristic_scanner.py`

Performs string-based behavioral checks inside executable-like files for:

- `vssadmin delete shadows`
- `wbadmin delete catalog`
- `bcdedit /set recoveryenabled no`
- encryption-related strings
- process injection APIs
- crypto/ransom-note wording

### `scanners/entropy_analyzer.py`

Calculates Shannon entropy across file blocks and compares averages against expected ranges for known file types. This is used to spot possible encrypted or packed content.

### `scanners/deception_scanner.py`

Creates temporary canary files and stores their hashes. During a scan it checks whether those files were modified or deleted.

### `scanners/comprehensive_scanner.py`

Applies final classification by combining:

- whitelist status
- smart scanner results
- special lock-screen detection logic
- recommendation text

### `scanners/process_monitor.py`

Background monitor for new processes. It flags:

- exact blacklist name matches
- suspicious ransomware-related command lines
- very high CPU and memory usage in non-whitelisted processes

### `scanners/usb_monitor.py`

Contains both:

- `USBMonitor` for drive detection and notifications
- `USBScanner` for simple content analysis

### `scanners/whitelist_manager.py`

Provides multiple whitelist strategies:

- known path patterns
- filename signatures
- stored file hashes
- publisher checks

### `scanners/exe_scanner.py`

Standalone executable-focused scanner with deeper PE scoring, entropy, import analysis, and string checks.

Note: this module exists in the codebase but is not currently wired into the main UI scan thread.

### `sandbox/sandbox_manager.py`

Handles:

- locating `Sandboxie-Plus`
- launching files in sandbox
- fallback sandbox creation
- monitoring sandboxed processes
- cleanup and emergency kill

### `utils/file_utils.py`

Utility helpers for:

- SHA-256 file hashing
- file metadata lookup
- file backup
- restore from backup

## Requirements

The project is designed for **Windows** and depends on Windows-specific packages and APIs.

Python dependencies in `requirements.txt`:

- `PyQt5==5.15.9`
- `psutil==5.9.5`
- `pywin32==306`
- `numpy==1.24.3`
- `scipy==1.10.1`
- `pefile==2023.2.7`
- `yara-python==4.3.1`
- `watchdog==3.0.0`
- `Pillow==10.0.0`
- `win10toast==0.9`

## Installation

1. Install Python 3.10+ on Windows.
2. Create and activate a virtual environment.
3. Install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

4. Optional but recommended: install `Sandboxie-Plus` from [sandboxie-plus.com](https://sandboxie-plus.com/).

## Running the App

```powershell
python main.py
```

## Usage

### Scan a file

1. Launch the app.
2. Click `Select File`.
3. Choose which scan layers to enable.
4. Click `Scan File`.
5. Review the summary and detailed analysis tabs.

### Open a file in sandbox

1. Select a file.
2. Click `Open in Sandbox`.
3. Use `Sandboxie-Plus` if available, otherwise use the fallback sandbox.

### Scan a USB drive

1. Insert a removable drive.
2. Review the USB detection popup.
3. Open it in sandbox or scan it from the USB tab.

## Important Limitations

- This is a heuristic desktop tool, not a full antivirus engine.
- Several detections are string-based and may produce false positives or false negatives.
- `DeceptionScanner` checks local canary files created by the application; it does not execute a suspicious sample and watch live filesystem behavior.
- `ProcessMonitor` and USB detection use polling, not kernel-level monitoring.
- `WhitelistManager` trusts some broad paths such as desktop and downloads, which may be too permissive for real-world security use.
- `EXEScanner` is currently present but not integrated into the main scan workflow.
- `yara-python`, `watchdog`, `Pillow`, and `scipy` are listed as dependencies but are not actively used by the current code paths reviewed here.
- The fallback sandbox is convenience isolation, not strong containment.
- The emergency kill logic is aggressive and should be treated carefully.

## Suggested Improvements

- integrate `EXEScanner` into the main scan pipeline
- replace broad whitelist rules with stricter trust validation
- add real YARA rule support
- add persistent scan history and quarantine handling
- add automated tests for scanners and UI-safe business logic
- separate UI, detection logic, and OS integration into cleaner layers
- improve sandbox safety guarantees and logging

## License

The UI text says `MIT`, but no license file is currently included in the project. Add a `LICENSE` file if you want the repository to be formally licensed.
