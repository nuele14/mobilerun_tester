"""
===============================================================================
[Design] ADB ENGINE: Native Android input primitives and geometry scaling.
1. Dispatches ADB shell taps without UI Automator overhead.
2. Scales percentage coordinates to actual dynamic screenshot aspect ratio.
3. Clears textfields via 3-step sequence: MOVE_END -> SELECT_ALL -> DELETE.
===============================================================================
"""

import re
import shutil
import subprocess
import time
import yaml
from pathlib import Path
from typing import Tuple, List
from PIL import Image
from mobilerun_tester.core.logger import GetLogger, console


class ADBDevice:
    """[Teacher] Hardware ADB input dispatcher and dynamic screen orientation tracker."""

    # === [ SECTION 1: INIT & GEOMETRY ] ===

    def __init__(self, serial: str = "", adb_path: str = "adb", config_path: str = "mobilerun_tester/config/default_config.yaml"):
        self.adb_path = shutil.which(adb_path) or adb_path
        self.config_path = config_path
        self.serial = self.ResolveOrSelectDevice(serial)
        self.screen_width, self.screen_height = self.FetchScreenSize()
        self.EnableTouchVisualizer()

    def GetConnectedDevices(self) -> List[str]:
        """[Function] Returns list of currently connected ADB device serials."""
        try:
            res = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, check=True)
            lines = res.stdout.strip().split("\n")[1:]
            return [l.split("\t")[0] for l in lines if "\tdevice" in l]
        except Exception:
            return []

    def SaveDeviceToConfig(self, serial: str):
        """[Function] Persists the selected ADB device serial to configuration YAML file."""
        logger = GetLogger()
        if not self.config_path:
            return

        cfg_file = Path(self.config_path)
        if not cfg_file.exists():
            return

        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg_data = yaml.safe_load(f) or {}

            if "device" not in cfg_data or not isinstance(cfg_data["device"], dict):
                cfg_data["device"] = {}

            if cfg_data["device"].get("serial") == serial:
                return

            cfg_data["device"]["serial"] = serial

            with open(cfg_file, "w", encoding="utf-8") as f:
                yaml.dump(cfg_data, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved selected ADB device '{serial}' to {self.config_path}")
            console.print(f"💾 [bold green]Dispositivo '{serial}' salvato con successo nelle preferenze[/bold green] ([dim]{self.config_path}[/dim])\n")
        except Exception as e:
            logger.warning(f"Could not save device serial to config: {e}")

    def ResolveOrSelectDevice(self, configured_serial: str) -> str:
        """
        [Function] Resolves target ADB device serial:
        1. If configured_serial is present in connected devices -> use it immediately.
        2. If configured_serial is empty or not connected:
           - Prompts user interactively to select a device.
           - Saves the choice into config file for future runs.
        """
        logger = GetLogger()
        connected = self.GetConnectedDevices()

        if not connected:
            logger.error("No ADB devices connected.")
            console.print("[bold red]❌ Errore: Nessun dispositivo o emulatore Android connesso via ADB![/bold red]")
            console.print("[dim]Assicurati che lo smartphone o l'emulatore sia collegato e che 'USB Debugging' sia attivo.[/dim]")
            raise RuntimeError("No ADB devices connected.")

        # Se il serial salvato nelle preferenze è attualmente connesso, usalo direttamente
        if configured_serial and configured_serial in connected:
            logger.info(f"Using configured ADB device: {configured_serial}")
            return configured_serial

        # Altrimenti, mostriamo la selezione interattiva
        console.print("\n[bold yellow]📱 SELEZIONE DISPOSITIVO ANDROID (ADB)[/bold yellow]")
        if configured_serial:
            console.print(f"[dim]Il dispositivo salvato nelle preferenze ('{configured_serial}') non è attualmente connesso.[/dim]")
        else:
            console.print("[dim]Nessun dispositivo predefinito salvato nelle preferenze.[/dim]")

        console.print("Dispositivi connessi disponibili:")
        for idx, dev_serial in enumerate(connected, 1):
            console.print(f"  [bold cyan]{idx})[/bold cyan] [bold white]{dev_serial}[/bold white]")

        selected_serial = connected[0]
        if len(connected) == 1:
            selected_serial = connected[0]
            console.print(f"\n[green]✓ Selezionato automaticamente:[/green] [bold]{selected_serial}[/bold]")
        else:
            while True:
                try:
                    choice = input(f"\nSeleziona il dispositivo (1-{len(connected)}) [1]: ").strip()
                    if not choice:
                        selected_serial = connected[0]
                        break
                    idx_choice = int(choice)
                    if 1 <= idx_choice <= len(connected):
                        selected_serial = connected[idx_choice - 1]
                        break
                    else:
                        console.print(f"[red]Inserisci un numero compreso tra 1 e {len(connected)}[/red]")
                except (ValueError, KeyboardInterrupt):
                    console.print(f"[yellow]Selezione predefinita: {connected[0]}[/yellow]")
                    selected_serial = connected[0]
                    break

        self.SaveDeviceToConfig(selected_serial)
        return selected_serial

    def FetchScreenSize(self) -> Tuple[int, int]:
        """[Function] Fetches raw physical resolution from 'wm size'."""
        try:
            out = self.ExecuteAdbCommand(["shell", "wm", "size"])
            m = re.search(r"(\d+)x(\d+)", out)
            if m:
                return int(m.group(1)), int(m.group(2))
        except Exception:
            pass
        return 1080, 2400

    def EnableTouchVisualizer(self):
        """[Function] Enables on-screen white touch indicators."""
        try:
            self.ExecuteAdbCommand(["shell", "settings", "put", "system", "show_touches", "1"])
        except Exception:
            pass

    # === [ SECTION 2: SCREEN CAPTURE ] ===

    def ExecuteAdbCommand(self, args: list) -> str:
        """[Function] Subprocess runner injecting device serial."""
        cmd = [self.adb_path] + (["-s", self.serial] if self.serial else []) + args
        return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()

    def CaptureScreenBuffer(self, output_path: str) -> str:
        """[Function] Captures raw PNG screen buffer and updates display orientation."""
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        cmd = [self.adb_path] + (["-s", self.serial] if self.serial else []) + ["exec-out", "screencap", "-p"]
        with open(out_file, "wb") as f:
            subprocess.run(cmd, stdout=f, check=True)
        self.UpdateScreenGeometry(str(out_file))
        return str(out_file)

    def UpdateScreenGeometry(self, image_path: str):
        """[Function] Syncs screen width/height from actual screenshot dimensions."""
        try:
            with Image.open(image_path) as img:
                self.screen_width, self.screen_height = img.size
        except Exception:
            pass

    # === [ SECTION 3: INPUT PRIMITIVES ] ===

    def HideSoftKeyboard(self):
        """[Function] Dismisses soft keyboard if currently open."""
        try:
            out = self.ExecuteAdbCommand(["shell", "dumpsys", "input_method"])
            if "mInputShown=true" in out or "mInputShown=True" in out:
                self.ExecuteAdbCommand(["shell", "input", "keyevent", "4"])
                time.sleep(0.3)
        except Exception:
            pass

    def ExecuteNativeTap(self, x_pct: float, y_pct: float):
        """[Function] Dispatches single native tap with status bar Y-margin protection."""
        eff_y = max(6.5, y_pct) if y_pct < 5.0 else y_pct
        px_x, px_y = int((x_pct / 100.0) * self.screen_width), int((eff_y / 100.0) * self.screen_height)
        GetLogger().debug(f"[ADB Tap] ({x_pct:.1f}%, {eff_y:.1f}%) -> Pixel ({px_x}, {px_y}) [{self.screen_width}x{self.screen_height}]")
        self.ExecuteAdbCommand(["shell", "input", "tap", str(px_x), str(px_y)])

    def ExecuteDoubleTap(self, x_pct: float, y_pct: float):
        """[Function] Dispatches two taps with 100ms delay."""
        self.ExecuteNativeTap(x_pct, y_pct)
        time.sleep(0.1)
        self.ExecuteNativeTap(x_pct, y_pct)

    def ExecuteBurstTap(self, x_pct: float, y_pct: float, count: int = 3):
        """[Function] Dispatches rapid burst taps for stubborn UI elements."""
        for _ in range(count):
            self.ExecuteNativeTap(x_pct, y_pct)
            time.sleep(0.08)

    def ExecuteLongPress(self, x_pct: float, y_pct: float, duration_ms: int = 2000):
        """[Function] Executes stationary swipe to emulate long press."""
        px_x, px_y = int((x_pct / 100.0) * self.screen_width), int((y_pct / 100.0) * self.screen_height)
        GetLogger().debug(f"[ADB LongPress] ({x_pct:.1f}%, {y_pct:.1f}%) -> ({px_x}, {px_y}) [{duration_ms}ms]")
        self.ExecuteAdbCommand(["shell", "input", "swipe", str(px_x), str(px_y), str(px_x), str(px_y), str(duration_ms)])

    def DispatchRobustTap(self, x_pct: float, y_pct: float, mode: str = "tap", duration_ms: int = 350):
        """[Function] Routes interaction to tap, double-tap, burst, or long-press."""
        if mode == "double_tap":
            self.ExecuteDoubleTap(x_pct, y_pct)
        elif mode == "burst":
            self.ExecuteBurstTap(x_pct, y_pct)
        elif mode == "long_press":
            self.ExecuteLongPress(x_pct, y_pct, duration_ms=max(duration_ms, 1200))
        else:
            self.ExecuteNativeTap(x_pct, y_pct)

    # === [ SECTION 4: TEXT INPUT ] ===

    def ClearTextFieldContent(self):
        """[Function] Clears textfield using MOVE_END -> CTRL+A -> DELETE sequence."""
        GetLogger().debug("Purging textfield (MOVE_END -> CTRL+A -> DEL)...")
        self.ExecuteAdbCommand(["shell", "input", "keyevent", "123"])
        time.sleep(0.08)
        self.ExecuteAdbCommand(["shell", "input", "keyevent", "--metastate", "28672", "29"])
        time.sleep(0.08)
        self.ExecuteAdbCommand(["shell", "input", "keyevent"] + ["67"] * 35)
        time.sleep(0.15)

    def InjectText(self, text: str, clear_existing: bool = True):
        """[Function] Purges and types sanitized text into focused field."""
        if clear_existing:
            self.ClearTextFieldContent()
        GetLogger().debug(f"[ADB Input] Typing: '{text}'")
        self.ExecuteAdbCommand(["shell", "input", "text", text.replace(" ", "%s")])
