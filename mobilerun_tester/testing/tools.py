"""
Helper tools for Mobilerun Tester.

Provides utilities for:
- App installation/uninstallation
- Device data management
- ADB command execution
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Check if ADB is available
ADB_PATH = shutil.which('adb')

@dataclass
class DeviceInfo:
    """Informazioni su un device Android"""
    serial: str
    model: str
    android_version: str
    is_rooted: bool
    is_online: bool


def ensure_adb_available() -> str:
    """Verifica che ADB sia disponibile nel sistema"""
    if ADB_PATH is None:
        raise EnvironmentError(
            "ADB non trovato. Installa Android SDK Platform Tools o aggiungi "
            "adb al PATH del sistema."
        )
    return ADB_PATH


def get_connected_devices() -> List[DeviceInfo]:
    """
    Restituisce l'elenco dei device Android connessi.
    
    Returns:
        List[DeviceInfo]: Elenco dei device disponibili
    """
    if ADB_PATH is None:
        raise EnvironmentError("ADB non disponibile")
    
    try:
        result = subprocess.run(
            [ADB_PATH, 'devices'],
            capture_output=True,
            text=True,
            check=True
        )
        
        devices = []
        lines = result.stdout.strip().split('\n')[1:]  # Salta header
        
        for line in lines:
            if '\t' in line:
                serial, status = line.split('\t')
                if status == 'device':
                    # Prendi dettagli device
                    model = _get_device_property(serial, 'ro.product.model')
                    version = _get_device_property(serial, 'ro.build.version.release')
                    devices.append(DeviceInfo(
                        serial=serial,
                        model=model or "Unknown",
                        android_version=version or "Unknown",
                        is_rooted=_is_device_rooted(serial),
                        is_online=True
                    ))
        
        return devices
    except subprocess.CalledProcessError:
        return []


def _get_device_property(serial: str, property_name: str) -> Optional[str]:
    """Ottiene una proprietà del device tramite ADB"""
    try:
        result = subprocess.run(
            [ADB_PATH, 'shell', f'getprop {property_name}'],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def _is_device_rooted(serial: str) -> bool:
    """Verifica se il device è rooted"""
    try:
        result = subprocess.run(
            [ADB_PATH, 'shell', 'su -c "id"'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return 'uid=0' in result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def install_app(apk_path: str, device_serial: Optional[str] = None) -> bool:
    """
    Installa un'app APK sul device.
    
    Args:
        apk_path: Percorso del file APK
        device_serial: Serial del device (opzionale)
    
    Returns:
        bool: True se l'installazione ha successo
    """
    if not Path(apk_path).exists():
        raise FileNotFoundError(f"APK non trovato: {apk_path}")
    
    cmd = [ADB_PATH, 'install', '-r', apk_path]  # -r riinstalla se già presente
    if device_serial:
        cmd.insert(1, '-s')
        cmd.insert(2, device_serial)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return 'Success' in result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[INSTALL ERROR] {e.stderr}")
        return False


def uninstall_app(package_name: str, device_serial: Optional[str] = None) -> bool:
    """
    Disinstalla un'app dal device.
    """
    cmd = [ADB_PATH, 'uninstall', package_name]
    if device_serial:
        cmd.insert(1, '-s')
        cmd.insert(2, device_serial)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return 'Success' in result.stdout
    except subprocess.CalledProcessError:
        return False


def clear_app_data(package_name: str, device_serial: Optional[str] = None) -> bool:
    """
    Pulisce i dati di un'app (simile a "Force Stop" + "Clear Data").
    """
    cmd = [ADB_PATH, 'shell', 'pm clear', package_name]
    if device_serial:
        cmd.insert(1, '-s')
        cmd.insert(2, device_serial)
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def start_activity(package_name: str, activity: str, device_serial: Optional[str] = None) -> bool:
    """
    Avvia un'attività specifica dell'app.
    """
    full_name = f"{package_name}/{activity}"
    cmd = [ADB_PATH, 'shell', 'am', 'start', '-n', full_name]
    if device_serial:
        cmd.insert(1, '-s')
        cmd.insert(2, device_serial)
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def pull_screenshot(device_serial: Optional[str] = None) -> Path:
    """
    Preleva uno screenshot dal device e lo salva localmente.
    """
    temp_path = Path("/sdcard/mobilerun_temp_screenshot.png")
    local_path = Path("/tmp/mobilerun_latest.png")
    
    cmd = [ADB_PATH, 'exec-out', 'screencap', '-p', '/sdcard/mobilerun_temp_screenshot.png']
    if device_serial:
        cmd.insert(1, '-s')
        cmd.insert(2, device_serial)
    
    try:
        # Esegui screenshot
        result = subprocess.run(cmd, capture_output=True, check=True)
        with open(local_path, 'wb') as f:
            f.write(result.stdout)
        return local_path
    except subprocess.CalledProcessError as e:
        print(f"[SCREENSHOT ERROR] {e}")
        return None


def enable_debugging(device_serial: Optional[str] = None) -> bool:
    """
    Abilita la modalità debugging/developer se necessario.
    """
    cmd = [ADB_PATH, 'shell', 'settings', 'put', 'global', 'development_settings_enabled', '1']
    if device_serial:
        cmd.insert(1, '-s')
        cmd.insert(2, device_serial)
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def check_portal_mode(device_serial: Optional[str] = None) -> bool:
    """
    Verifica se il device è in modalità Mobilerun Portal.
    (Richiede entità Mobilerun specifica)"
    """
    cmd = [ADB_PATH, 'shell', 'ps', '|', 'grep', 'mobilerun']
    if device_serial:
        cmd.insert(1, '-s')
        cmd.insert(2, device_serial)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return 'mobilerun' in result.stdout.lower()
    except subprocess.CalledProcessError:
        return False


# Convenience function
def setup_test_environment(apk_path: str = None, device_serial: str = None):
    """
    Prepara l'ambiente di test.
    """
    ensure_adb_available()
    devices = get_connected_devices()
    
    if not devices:
        raise RuntimeError("Nessun device Android connesso")
    
    if device_serial and device_serial != devices[0].serial:
        print(f"[WARNING] Device {device_serial} non trovato, uso {devices[0].serial}")
        device_serial = devices[0].serial
    
    if device_serial is None:
        device_serial = devices[0].serial
    
    print(f"Device selezionato: {devices[0]}")
    
    if apk_path:
        install_app(apk_path, device_serial)
        clear_app_data(apk_path, device_serial)
    
    return device_serial