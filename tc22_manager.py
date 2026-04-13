import subprocess
import logging
import os
import time
from datetime import datetime
import json

# --- Initialization ---
os.makedirs("logs", exist_ok=True)
os.makedirs("pulled_logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"logs/tc22_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler()
    ]
)

ADB = "adb"

# ─────────────────────────────────────────
# BASE FUNCTIONS
# ─────────────────────────────────────────

def load_devices(file="devices.txt"):
    try:
        with open(file, "r") as f:
            devices = [
                line.strip() for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
        if not devices:
            logging.error(f"File {file} is empty")
            return []
        return devices
    except FileNotFoundError:
        logging.error(f"File not found: {file}")
        return []

def load_apps(file="apps.txt"):
    apps = []
    try:
        with open(file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) == 2:
                    apps.append({
                        "name": parts[0].strip(),
                        "package": parts[1].strip()
                    })
    except FileNotFoundError:
        logging.error(f"File not found: {file}")
    return apps

def load_log_profiles(file="log_profiles.json"):
    try:
        with open(file, "r") as f:
            profiles = json.load(f)
        profiles = [p for p in profiles if "name" in p]
        if not profiles:
            logging.error("log_profiles.json is empty or malformed")
            return []
        return profiles
    except FileNotFoundError:
        logging.error(f"File not found: {file}")
        return []
    except json.JSONDecodeError:
        logging.error("Format error in log_profiles.json")
        return []

def run_adb(args, ip=None, timeout=10):
    """Run an ADB command and return the result."""
    cmd = [ADB]
    if ip:
        cmd += ["-s", ip]
    cmd += args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result
    except subprocess.TimeoutExpired:
        logging.error(f"TIMEOUT on {ip or 'global'}: {' '.join(args)}")
        return None

# ─────────────────────────────────────────
# SELECTION HELPERS
# ─────────────────────────────────────────

def select_app(action="use"):
    apps = load_apps()
    if not apps:
        print("No apps found in apps.txt or file does not exist.")
        return None

    print(f"\nAvailable apps:")
    for i, app in enumerate(apps, 1):
        print(f"  {i}. {app['name']} ({app['package']})")

    selection = input(f"\nSelect app number to {action}: ").strip()
    try:
        index = int(selection) - 1
        if index < 0 or index >= len(apps):
            print("Number out of range.")
            return None
        return apps[index]
    except ValueError:
        print("Invalid input.")
        return None

def select_log_profile(action="use"):
    profiles = load_log_profiles()
    if not profiles:
        print("No profiles found in log_profiles.json or file does not exist.")
        return None

    print(f"\nAvailable log profiles:")
    for i, profile in enumerate(profiles, 1):
        print(f"  {i}. {profile['name']} ({profile['path']})")

    selection = input(f"\nSelect profile number to {action}: ").strip()
    try:
        index = int(selection) - 1
        if index < 0 or index >= len(profiles):
            print("Number out of range.")
            return None
        return profiles[index]
    except ValueError:
        print("Invalid input.")
        return None

# ─────────────────────────────────────────
# OPERATIONS
# ─────────────────────────────────────────

def connect_devices(devices):
    logging.info("Starting ADB connection...")
    run_adb(["kill-server"])
    run_adb(["start-server"])
    successful = []
    for ip in devices:
        logging.info(f"Connecting {ip}...")
        result = run_adb(["connect", ip])
        if result and ("connected" in result.stdout or "already connected" in result.stdout):
            logging.info(f"OK: {ip}")
            successful.append(ip)
        else:
            output = result.stdout.strip() if result else "no response"
            logging.error(f"FAILED: {ip} — {output}")
    logging.info(f"Connection complete: {len(successful)}/{len(devices)} devices")
    return successful

def open_scrcpy(devices):
    logging.info("Opening scrcpy...")
    for ip in devices:
        name = f"TC22-{ip.split('.')[3].split(':')[0]}"
        logging.info(f"Opening {name} ({ip})")
        subprocess.Popen(["scrcpy", "-s", ip, "--no-audio", "--window-title", name])
        time.sleep(3)

def force_stop(devices):
    app = select_app("force-stop")
    if not app:
        return
    logging.info(f"Force-stopping {app['name']} on all devices...")
    for ip in devices:
        result = run_adb(["shell", "am", "force-stop", app["package"]], ip=ip)
        if result is not None:
            logging.info(f"OK: {ip}")
        else:
            logging.error(f"FAILED: {ip}")

def pull_logs(devices):
    profile = select_log_profile("download")
    if not profile:
        return
    logging.info(f"Downloading logs '{profile['name']}'...")
    for ip in devices:
        result = run_adb(["shell", "ls", profile["path"]], ip=ip)
        if not result:
            continue
        files = [
            f for f in result.stdout.splitlines()
            if f.startswith(profile["prefix"])
        ]
        if not files:
            logging.info(f"{ip}: no logs found")
            continue
        for file in files:
            name, ext = os.path.splitext(file)
            clean_ip = ip.replace(":", "-")
            destination = f"pulled_logs/{name}_{clean_ip}{ext}"
            run_adb(["pull", f"{profile['path']}/{file}", destination], ip=ip)
            logging.info(f"Downloaded: {destination}")

def clean_logs(devices):
    profile = select_log_profile("clean")
    if not profile:
        return
    confirm = input(f"Delete all '{profile['name']}' logs on ALL devices? (y/N): ").strip().lower()
    if confirm != "y":
        logging.info("Cleanup cancelled by user")
        return
    logging.info(f"Cleaning logs '{profile['name']}'...")
    for ip in devices:
        result = run_adb(["shell", "ls", profile["path"]], ip=ip)
        if not result:
            continue
        files = [
            f for f in result.stdout.splitlines()
            if f.startswith(profile["prefix"])
        ]
        for file in files:
            run_adb(["shell", "rm", f"{profile['path']}/{file}"], ip=ip)
            logging.info(f"Deleted on {ip}: {file}")

def launch_app(devices):
    app = select_app("launch")
    if not app:
        return
    logging.info(f"Launching {app['name']} on all devices...")
    for ip in devices:
        run_adb([
            "shell", "monkey", "-p", app["package"],
            "-c", "android.intent.category.LAUNCHER", "1"
        ], ip=ip)
        logging.info(f"OK: {ip}")
        time.sleep(2)

def uninstall_app(devices):
    app = select_app("uninstall")
    if not app:
        return
    confirm = input(f"Uninstall {app['name']} on ALL devices? (y/N): ").strip().lower()
    if confirm != "y":
        logging.info("Uninstall cancelled")
        return
    for ip in devices:
        logging.info(f"Uninstalling {app['name']} on {ip}...")
        result = run_adb(["uninstall", app["package"]], ip=ip)
        if result and "Success" in result.stdout:
            logging.info(f"OK: {ip}")
        else:
            output = result.stdout.strip() if result else "no response"
            logging.error(f"FAILED: {ip} — {output}")

def install_apk(devices):
    apk_folder = "apk"
    if not os.path.exists(apk_folder):
        print(f"Folder '{apk_folder}' not found. Create it and place APK files inside.")
        return

    apks = [f for f in os.listdir(apk_folder) if f.endswith(".apk")]
    if not apks:
        print("No .apk files found in 'apk/' folder.")
        return

    print("\nAvailable APKs:")
    for i, apk in enumerate(apks, 1):
        print(f"  {i}. {apk}")

    selection = input("\nSelect APK number to install: ").strip()
    try:
        index = int(selection) - 1
        if index < 0 or index >= len(apks):
            print("Number out of range.")
            return
    except ValueError:
        print("Invalid input.")
        return

    apk_path = os.path.join(apk_folder, apks[index])
    logging.info(f"Installing {apks[index]} on {len(devices)} devices...")

    for ip in devices:
        logging.info(f"Installing on {ip}...")
        result = run_adb(["install", "-r", apk_path], ip=ip, timeout=60)
        if result and "Success" in result.stdout:
            logging.info(f"OK: {ip}")
        else:
            output = result.stdout.strip() if result else "no response"
            logging.error(f"FAILED: {ip} — {output}")

# ─────────────────────────────────────────
# MENU
# ─────────────────────────────────────────

def show_menu(total, active):
    print("\n" + "="*45)
    print("   TC22 MANAGER — Android Scanner Tool")
    print("="*45)
    print(f"   Devices in devices.txt : {total}")
    print(f"   Active devices         : {active}")
    print("-"*45)
    print("  1. Connect all devices")
    print("  2. Open scrcpy (screen mirror)")
    print("  3. Force-stop an app")
    print("  4. Pull logs")
    print("  5. Clean logs on devices")
    print("  6. Launch app")
    print("  7. Uninstall app")
    print("  8. Install new APK version")
    print("  0. Exit")
    print("="*45)

def main():
    devices = load_devices()
    if not devices:
        print("No devices loaded. Check devices.txt")
        return

    active = devices[:]

    options = {
        "2": open_scrcpy,
        "3": force_stop,
        "4": pull_logs,
        "5": clean_logs,
        "6": launch_app,
        "7": uninstall_app,
        "8": install_apk,
    }

    while True:
        show_menu(len(devices), len(active))
        option = input("Select an option: ").strip()

        if option == "0":
            logging.info("Session ended by user")
            print("Goodbye.")
            break
        elif option == "1":
            active = connect_devices(devices)
        elif option in options:
            if not active:
                print("No active devices. Run option 1 first.")
            else:
                options[option](active)
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
