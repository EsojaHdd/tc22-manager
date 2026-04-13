# TC22 Manager

CLI tool for managing Android scanners (Zebra TC22) via ADB over TCP/IP.
Python replacement for legacy `.bat` scripts used in warehouse operations.

## Features

- Connect multiple devices from a single `devices.txt` config file
- Interactive console menu — no hardcoded IPs
- Open screen mirror per device (scrcpy)
- Force-stop / launch any app across all devices
- Pull logs from devices with automatic IP-based file naming
- Clean logs on devices with confirmation prompt
- Install / uninstall APK on all devices simultaneously
- Full operation logging to `logs/tc22_YYYY-MM-DD.log`

## Requirements

- Python 3.10+
- [ADB](https://developer.android.com/tools/releases/platform-tools) available in PATH
- [scrcpy](https://github.com/Genymobile/scrcpy) available in PATH
- Android devices with ADB over TCP/IP enabled (port 5555)

## Setup

1. Clone the repository
git clone https://github.com/EsojaHdd/tc22-manager.git
cd tc22-manager

2. Add your device IPs to `devices.txt` (one per line):
10.0.0.1:5555
10.0.0.2:5555

3. Run the tool:
python tc22_manager.py

## Project Structure
tc22-manager/
├── tc22_manager.py       # Main script
├── devices.txt           # Device IP list
├── apps.txt              # App list (friendly name + package name)
├── log_profiles.json     # Log profile definitions
├── apk/                  # Place .apk files here for installation
├── logs/                 # Auto-generated operation logs
└── pulled_logs/          # Downloaded logs from devices

## Configuration Files

### devices.txt
One device IP per line. Lines starting with `#` are ignored.
Example
10.0.0.1:5555
10.0.0.2:5555

### apps.txt
Comma-separated list of apps available for launch, force-stop, and uninstall.
Format: Friendly name, package.name
My App, com.example.myapp
Chrome, com.android.chrome

### log_profiles.json
Defines log locations on the device for pull and cleanup operations.
```json
[
  {
    "name": "My Logs",
    "path": "/storage/emulated/0/Android/data/com.example.app/files/logs",
    "prefix": "log"
  }
]
```

Each profile requires three fields:
- `name` — display name shown in the menu
- `path` — full path on the Android device
- `prefix` — filename prefix used to filter files in that directory

### apk/
Place `.apk` files here. The install menu will list them automatically.

## Menu Options

| Option | Action |
|--------|--------|
| 1 | Connect all devices via ADB |
| 2 | Open scrcpy mirror per device |
| 3 | Force-stop selected app |
| 4 | Pull logs from devices |
| 5 | Clean logs on devices |
| 6 | Launch selected app |
| 7 | Uninstall selected app |
| 8 | Install new APK version |
| 0 | Exit |

## Background

This tool replaces a set of `.bat` files used to manage Zebra TC22 barcode
scanners in a warehouse environment. The Python rewrite adds error handling,
structured logging, and a unified interface for all device operations.