import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image


class ADBDevice:
    """Gestisce la comunicazione ADB nativa con il dispositivo Android."""

    def __init__(self, serial: str = "", adb_path: str = "adb"):
        self.adb_path = shutil.which(adb_path) or adb_path
        self.serial = serial or self._get_default_device()
        self.screen_width, self.screen_height = self._get_screen_size()
        self._enable_show_touches()
        print(f"📱 [ADB Engine] Dispositivo attivo: {self.serial} ({self.screen_width}x{self.screen_height}px)")

    def _enable_show_touches(self):
        """Attiva l'evidenziatore del tocco a schermo per il debug visivo."""
        try:
            self._run_cmd(["shell", "settings", "put", "system", "show_touches", "1"])
        except Exception:
            pass

    def hide_keyboard_if_shown(self):
        """Nasconde la tastiera Android solo se visibile."""
        try:
            output = self._run_cmd(["shell", "dumpsys", "input_method"])
            if "mInputShown=true" in output or "mInputShown=True" in output:
                print(" ⌨️ Tastiera aperta rilevata, la nascondo...")
                self._run_cmd(["shell", "input", "keyevent", "4"])
                time.sleep(0.3)
        except Exception:
            pass

    def _run_cmd(self, args: list) -> str:
        cmd = [self.adb_path]
        if self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(args)
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()

    def _get_default_device(self) -> str:
        res = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, check=True)
        lines = res.stdout.strip().split("\n")[1:]
        devices = [l.split("\t")[0] for l in lines if "\tdevice" in l]
        if not devices:
            raise RuntimeError("Nessun dispositivo Android connesso via ADB.")
        return devices[0]

    def _get_screen_size(self) -> Tuple[int, int]:
        try:
            output = self._run_cmd(["shell", "wm", "size"])
            match = re.search(r"(\d+)x(\d+)", output)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception:
            pass
        return 1080, 2400

    def capture_screenshot(self, output_path: str) -> str:
        """Cattura uno screenshot nativo salvandolo nel percorso specificato."""
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        cmd = [self.adb_path]
        if self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(["exec-out", "screencap", "-p"])

        with open(out_file, "wb") as f:
            subprocess.run(cmd, stdout=f, check=True)

        self.update_screen_size_from_image(str(out_file))
        return str(out_file)

    def update_screen_size_from_image(self, image_path: str):
        """Aggiorna la geometria reale dello schermo leggendola dall'immagine dello screenshot."""
        try:
            with Image.open(image_path) as img:
                self.screen_width, self.screen_height = img.size
        except Exception:
            pass

    def flutter_tap(self, x_percent: float, y_percent: float):
        """Esegue un singolo tocco nativo ADB standard sulle coordinate percentuali indicate."""
        effective_y_pct = max(6.5, y_percent) if y_percent < 5.0 else y_percent
        
        real_x = int((x_percent / 100.0) * self.screen_width)
        real_y = int((effective_y_pct / 100.0) * self.screen_height)
        
        print(f"⚡ [ADB Tap] Coords: ({x_percent:.1f}%, {effective_y_pct:.1f}%) -> Pixel: ({real_x}, {real_y}) [{self.screen_width}x{self.screen_height}]")
        self._run_cmd(["shell", "input", "tap", str(real_x), str(real_y)])

    def tap(self, x_percent: float, y_percent: float):
        self.flutter_tap(x_percent, y_percent)

    def double_tap(self, x_percent: float, y_percent: float):
        """Esegue due tap in rapida sequenza a distanza di 100ms."""
        self.flutter_tap(x_percent, y_percent)
        time.sleep(0.1)
        self.flutter_tap(x_percent, y_percent)

    def burst_tap(self, x_percent: float, y_percent: float, count: int = 3):
        """Invia una raffica (burst) di tocchi consecutivi sullo stesso punto per attivare pulsanti ostici."""
        for _ in range(count):
            self.flutter_tap(x_percent, y_percent)
            time.sleep(0.08)

    def robust_tap(self, x_percent: float, y_percent: float, mode: str = "tap", duration_ms: int = 350):
        """Esegue il tocco basandosi sulla modalità selezionata ('tap', 'double_tap', 'long_press', 'burst')."""
        if mode == "double_tap":
            self.double_tap(x_percent, y_percent)
        elif mode == "burst":
            self.burst_tap(x_percent, y_percent, count=3)
        elif mode == "long_press":
            self.long_press(x_percent, y_percent, duration_ms=duration_ms if duration_ms > 350 else 1200)
        else:
            self.flutter_tap(x_percent, y_percent)

    def long_press(self, x_percent: float, y_percent: float, duration_ms: int = 2000):
        """Esegue una pressione prolungata (Long Press / Long Tap)."""
        real_x = int((x_percent / 100.0) * self.screen_width)
        real_y = int((y_percent / 100.0) * self.screen_height)
        print(f"👉 [ADB Long Press] Posizione: ({x_percent:.1f}%, {y_percent:.1f}%) -> Pixel: ({real_x}, {real_y}) per {duration_ms}ms")
        self._run_cmd(["shell", "input", "swipe", str(real_x), str(real_y), str(real_x), str(real_y), str(duration_ms)])

    def clear_textfield_content(self):
        """Svuota completamente il contenuto di un campo di testo (MOVE_END -> CTRL+A -> DELETE)."""
        print(" 🧹 Pulizia completa del campo testo (MOVE_END -> CTRL+A -> DELETE)...")
        self._run_cmd(["shell", "input", "keyevent", "123"])
        time.sleep(0.08)
        self._run_cmd(["shell", "input", "keyevent", "--metastate", "28672", "29"])
        time.sleep(0.08)
        keyevents = ["67"] * 35
        self._run_cmd(["shell", "input", "keyevent"] + keyevents)
        time.sleep(0.15)

    def input_text(self, text: str, clear_existing: bool = True):
        """Invia testo al campo correntemente selezionato, svuotandolo se richiesto."""
        if clear_existing:
            self.clear_textfield_content()

        print(f" ⌨️ [ADB Input] Inserimento testo: '{text}'")
        escaped_text = text.replace(" ", "%s")
        self._run_cmd(["shell", "input", "text", escaped_text])
