#!/usr/bin/env python3
"""
Proof of Concept (PoC) Test Runner per Mobilerun Tester.

Funzionalità:
1. Carica la configurazione da `poc_config.yaml`.
2. Gestisce in autonomia il processo `llama-server` (avvio, health-check, shutdown).
3. Cattura screenshot da dispositivi Android (compatibile con app Flutter e native).
4. Esegue il Grounding visuale usando un LLM Vision (es. Qwen2-VL) tramite llama.cpp.
5. Invia comandi di tocco e testo tramite ADB.
6. Esegue asserzioni visuali sullo stato finale dell'applicazione.
"""

import os
import sys
import time
import json
import base64
import re
import subprocess
import shutil
import urllib.request
import urllib.error
import yaml
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from PIL import Image, ImageDraw

POC_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = POC_DIR / "poc_config.yaml"


def highlight_tap_on_image(image_path: str, x_pct: float, y_pct: float, output_path: str = None) -> str:
    """Disegna un cerchio rosso brillante ed un mirino sullo screenshot per evidenziare dove è stato fatto il tap."""
    if not output_path:
        output_path = image_path.replace(".png", "_tapped.png")
        
    try:
        img = Image.open(image_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        width, height = img.size
        real_x = int((x_pct / 100.0) * width)
        real_y = int((y_pct / 100.0) * height)
        
        radius = max(25, int(width * 0.035))  # Raggio proporzionale
        
        # Disegna cerchio rosso con bordo spesso (spessore 8px)
        bbox = [real_x - radius, real_y - radius, real_x + radius, real_y + radius]
        draw.ellipse(bbox, outline=(255, 0, 0, 255), width=8)
        
        # Disegna punto centrale rosso pieno
        inner_radius = 6
        draw.ellipse([real_x - inner_radius, real_y - inner_radius, real_x + inner_radius, real_y + inner_radius], fill=(255, 0, 0, 255))
        
        # Disegna mirino a croce (+)
        line_len = radius + 15
        draw.line([real_x - line_len, real_y, real_x + line_len, real_y], fill=(255, 0, 0, 255), width=4)
        draw.line([real_x, real_y - line_len, real_x, real_y + line_len], fill=(255, 0, 0, 255), width=4)
        
        # Disegna rettangolo di testo con le coordinate
        label_text = f"TAP ({x_pct:.1f}%, {y_pct:.1f}%) -> ({real_x}, {real_y})px"
        text_bbox = [real_x - 140, real_y + radius + 10, real_x + 140, real_y + radius + 40]
        draw.rectangle(text_bbox, fill=(255, 0, 0, 220))
        draw.text((real_x - 130, real_y + radius + 15), label_text, fill=(255, 255, 255, 255))
        
        img.save(output_path)
        print(f" 🎨 [Visual Debug] Evidenziazione del tocco salvata in: {output_path}")
        return output_path
    except Exception as e:
        print(f" ⚠️ Impossibile evidenziare il tocco sullo screenshot: {e}")
        return image_path


class LlamaServerManager:
    """Gestisce il ciclo di vita del processo llama-server."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("llama_cpp", {})
        self.binary = os.path.expanduser(self.config.get("server_binary", "llama-server"))
        self.model_path = os.path.expanduser(self.config.get("model_path", ""))
        self.mmproj_path = os.path.expanduser(self.config.get("mmproj_path", ""))
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 8080)
        self.context_size = self.config.get("context_size", 4096)
        self.gpu_layers = self.config.get("gpu_layers", 99)
        self.auto_start = self.config.get("auto_start_server", True)
        self.timeout = self.config.get("startup_timeout_seconds", 60)
        
        self.base_url = f"http://{self.host}:{self.port}"
        self.process: Optional[subprocess.Popen] = None

    def is_server_running(self) -> bool:
        """Verifica se llama-server è già in ascolto ed operativo."""
        try:
            url = f"{self.base_url}/health"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        return False

    def start(self):
        """Avvia llama-server in autonomia se non è attivo."""
        if self.is_server_running():
            print(f"🟢 [llama.cpp] Server già attivo su {self.base_url}")
            return True

        if not self.auto_start:
            print(f"🔴 [llama.cpp] Server non attivo su {self.base_url} e 'auto_start_server' è disabilitato.")
            return False

        # Verifica che l'eseguibile sia disponibile
        binary_path = shutil.which(self.binary) or self.binary
        if not os.path.exists(binary_path) and not shutil.which(self.binary):
            raise FileNotFoundError(f"Eseguibile llama-server non trovato in: {self.binary}")

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"File modello GGUF non trovato: {self.model_path}")

        if not os.path.exists(self.mmproj_path):
            raise FileNotFoundError(f"File mmproj GGUF non trovato: {self.mmproj_path}")

        cmd = [
            binary_path,
            "-m", self.model_path,
            "--mmproj", self.mmproj_path,
            "--host", self.host,
            "--port", str(self.port),
            "-c", str(self.context_size),
            "-ngl", str(self.gpu_layers)
        ]

        print(f"🚀 [llama.cpp] Avvio in corso di llama-server...")
        print(f"   Comando: {' '.join(cmd)}")

        log_file = open("/tmp/llama_server.log", "w")
        self.process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Attesa del server con polling
        start_time = time.time()
        print("⏳ Attesa dell'inizializzazione del modello Vision...")
        while time.time() - start_time < self.timeout:
            if self.is_server_running():
                print(f"✅ [llama.cpp] Server avviato ed operativo su {self.base_url}")
                return True
            time.sleep(2)

        print(f"❌ [llama.cpp] Timeout durante l'avvio del server ({self.timeout}s).")
        self.stop()
        return False

    def stop(self):
        """Interrompe il processo llama-server se avviato dallo script."""
        if self.process:
            print("🛑 [llama.cpp] Arresto di llama-server in corso...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            print("✅ [llama.cpp] Server arrestato.")


class ADBDevice:
    """Gestisce la comunicazione ADB con il dispositivo Android."""

    def __init__(self, serial: str = ""):
        self.adb_path = shutil.which("adb")
        if not self.adb_path:
            raise EnvironmentError("ADB non trovato. Assicurati che 'adb' sia installato e nel PATH.")
        
        self.serial = serial or self._get_default_device()
        self.screen_width, self.screen_height = self._get_screen_size()
        self._enable_show_touches()
        print(f"📱 [ADB] Dispositivo connesso: {self.serial} ({self.screen_width}x{self.screen_height}px)")

    def _enable_show_touches(self):
        """Abilita il feedback visivo del tocco sullo schermo del dispositivo."""
        try:
            self._run_cmd(["shell", "settings", "put", "system", "show_touches", "1"])
            print("👁️ [ADB] Touch visualizer abilitato a schermo (show_touches=1)")
        except Exception:
            pass

    def hide_keyboard_if_shown(self):
        """Nasconde la tastiera Android ESCLUSIVAMENTE se è attualmente aperta a schermo, evitando di inviare il tasto BACK se è già chiusa."""
        try:
            output = self._run_cmd(["shell", "dumpsys", "input_method"])
            if "mInputShown=true" in output or "mInputShown=True" in output:
                print(" ⌨️ Tastiera aperta rilevata, la nascondo...")
                self._run_cmd(["shell", "input", "keyevent", "4"])
                time.sleep(0.5)
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
            # Esempio output: Physical size: 1080x2400
            match = re.search(r"(\d+)x(\d+)", output)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception:
            pass
        return 1080, 2400  # Fallback generico

    def capture_screenshot(self, name: str = "poc_current_screen.png") -> str:
        """Scatta uno screenshot e lo salva nella cartella di debug."""
        debug_dir = POC_DIR / "debug_screenshots"
        debug_dir.mkdir(exist_ok=True)
        output_path = debug_dir / name

        cmd = [self.adb_path]
        if self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(["exec-out", "screencap", "-p"])

        with open(output_path, "wb") as f:
            subprocess.run(cmd, stdout=f, check=True)
        return str(output_path)

    def double_tap(self, x_percent: float, y_percent: float):
        """Esegue due tap in rapida sequenza a distanza di 100ms."""
        real_x = int((x_percent / 100.0) * self.screen_width)
        real_y = int((y_percent / 100.0) * self.screen_height)
        print(f"👉👉 [ADB Double Tap] Posizione: ({x_percent:.1f}%, {y_percent:.1f}%) -> Pixel: ({real_x}, {real_y})")
        self._run_cmd(["shell", "input", "tap", str(real_x), str(real_y)])
        time.sleep(0.1)
        self._run_cmd(["shell", "input", "tap", str(real_x), str(real_y)])

    def burst_tap(self, x_percent: float, y_percent: float, count: int = 3):
        """Invia una raffica (burst) di tocchi consecutivi sullo stesso punto per attivare pulsanti ostici."""
        real_x = int((x_percent / 100.0) * self.screen_width)
        real_y = int((y_percent / 100.0) * self.screen_height)
        print(f"💥 [ADB Burst Tap x{count}] Inviati {count} tocchi su ({x_percent:.1f}%, {y_percent:.1f}%)")
        for _ in range(count):
            self._run_cmd(["shell", "input", "swipe", str(real_x), str(real_y), str(real_x), str(real_y), "150"])
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
            self.tap(x_percent, y_percent, duration_ms=duration_ms)

    def long_press(self, x_percent: float, y_percent: float, duration_ms: int = 2000):
        """Esegue una pressione prolungata (Long Press / Long Tap) mantenendo le coordinate per duration_ms."""
        real_x = int((x_percent / 100.0) * self.screen_width)
        real_y = int((y_percent / 100.0) * self.screen_height)
        print(f"👉 [ADB Long Press] Posizione: ({x_percent:.1f}%, {y_percent:.1f}%) -> Pixel: ({real_x}, {real_y}) per {duration_ms}ms")
        # In ADB, uno swipe stazionario per X ms equivale ad un Long Press
        self._run_cmd(["shell", "input", "swipe", str(real_x), str(real_y), str(real_x), str(real_y), str(duration_ms)])

    def input_text(self, text: str, clear_existing: bool = True):
        """Invia testo al campo correntemente selezionato, pulendo eventuale testo precedente."""
        if clear_existing:
            print(" 🧹 Pulizia testo preesistente nel campo...")
            keyevents = ["67"] * 20
            self._run_cmd(["shell", "input", "keyevent"] + keyevents)
            time.sleep(0.2)

        print(f" ⌨️ [ADB Input] Inserimento testo: '{text}'")
        # Sostituisce gli spazi con %s per ADB input
        escaped_text = text.replace(" ", "%s")
        self._run_cmd(["shell", "input", "text", escaped_text])


class VisionAgent:
    """Interagisce con llama-server per Vision Grounding ed Asserzioni."""

    def __init__(self, server_url: str):
        self.api_url = f"{server_url}/v1/chat/completions"

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def query(self, image_path: str, prompt: str) -> str:
        base64_image = self._encode_image(image_path)
        payload = {
            "model": "qwen2-vl",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            "temperature": 0.1
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.api_url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"❌ [Vision Error] Chiamata a llama-server fallita: {e}")
            raise

    def get_element_coordinates(self, image_path: str, target_description: str) -> Tuple[float, float]:
        """Chiede all'LLM le coordinate del centro esatto dell'elemento target."""
        prompt = (
            f"Analizza l'immagine dello schermo mobile.\n"
            f"Trova l'elemento descritto come: '{target_description}'.\n"
            f"Rispondi ESCLUSIVAMENTE in formato JSON valido con le coordinate percentuali (da 0 a 100):\n"
            f'{{"x": float, "y": float}}\n'
            f"Nessun altro testo prima o dopo il JSON."
        )

        raw_response = self.query(image_path, prompt)
        print(f"🤖 [LLM Vision Response]: {raw_response.strip()}")

        # 1. Tentativo di parse JSON
        match_json = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if match_json:
            try:
                data = json.loads(match_json.group(0))
                x_val = float(data.get("x", 50.0))
                y_val = float(data.get("y", 50.0))
                if x_val > 100 or y_val > 100:
                    x_val /= 10.0
                    y_val /= 10.0
                return x_val, y_val
            except Exception:
                pass

        # 2. Tentativo di parse tupla nativa UI-TARS (es. "(962,62)", "(962, 62)", "[962, 62]")
        match_tuple = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)?", raw_response)
        if match_tuple:
            x_val = float(match_tuple.group(1))
            y_val = float(match_tuple.group(2))
            if x_val > 100 or y_val > 100:
                x_val /= 10.0
                y_val /= 10.0
            print(f" 🎯 [UI-TARS Grounding] Coordinate decodificate da tupla: ({x_val:.1f}%, {y_val:.1f}%)")
            return x_val, y_val

        raise ValueError(f"Impossibile estrarre le coordinate dalla risposta: {raw_response}")

    def get_element_coordinates_with_zoom(self, image_path: str, target_description: str, crop_padding_pct: float = 12.0) -> Tuple[float, float]:
        """
        Esegue il Grounding a due livelli (Coarse + Fine Zoom):
        1. Trova le coordinate approssimative sull'immagine intera.
        2. Genera un Crop (Zoom) attorno all'area individuata.
        3. Riconosce la coordinata esplicita dentro l'immagine zoomata (dove l'elemento è molto più grande).
        4. Trasforma le coordinate locali della sotto-immagine in coordinate globali dello schermo.
        """
        # Fase 1: Coarse Grounding Globale
        coarse_x, coarse_y = self.get_element_coordinates(image_path, target_description)
        print(f" 🔍 [Zoom Phase 1] Coordinata globale approssimativa: ({coarse_x:.1f}%, {coarse_y:.1f}%)")

        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # Calcola il riquadro di Crop attorno al punto approssimativo (box 24% x 24%)
            crop_xmin_pct = max(0.0, coarse_x - crop_padding_pct)
            crop_xmax_pct = min(100.0, coarse_x + crop_padding_pct)
            crop_ymin_pct = max(0.0, coarse_y - crop_padding_pct)
            crop_ymax_pct = min(100.0, coarse_y + crop_padding_pct)
            
            px_xmin = int((crop_xmin_pct / 100.0) * width)
            px_xmax = int((crop_xmax_pct / 100.0) * width)
            px_ymin = int((crop_ymin_pct / 100.0) * height)
            px_ymax = int((crop_ymax_pct / 100.0) * height)
            
            # Effettua il ritaglio (Crop)
            cropped_img = img.crop((px_xmin, px_ymin, px_xmax, px_ymax))
            
            cropped_path = image_path.replace(".png", "_zoom_crop.png")
            cropped_img.save(cropped_path)
            print(f" 🔎 [Zoom Phase 2] Sotto-immagine ritagliata e zoomata salvata in: {cropped_path}")
            
            # Fase 2: Fine Grounding tramite Bounding Box sulla regione ingrandita
            fine_prompt = (
                f"Questa è una sotto-immagine INGRANDITA (ZOOM) di un'area dello schermo.\n"
                f"Individua l'elemento UI descritto come: '{target_description}'.\n"
                f"Trova la scatola (bounding box) che racchiude interamente questo elemento.\n"
                f"Rispondi ESCLUSIVAMENTE in formato JSON valido con i valori percentuali (0-100):\n"
                f'{{"xmin": float, "ymin": float, "xmax": float, "ymax": float, "x": float, "y": float}}\n'
                f"Nessun altro testo prima o dopo il JSON."
            )
            
            raw_response = self.query(cropped_path, fine_prompt)
            print(f"🤖 [LLM Fine Zoom Response]: {raw_response.strip()}")
            
            sub_x, sub_y = 50.0, 50.0
            found_coords = False

            # 1. Tentativo di parse JSON
            match_json = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match_json:
                try:
                    data = json.loads(match_json.group(0))
                    if "xmin" in data and "xmax" in data and "ymin" in data and "ymax" in data:
                        xmin, xmax = float(data["xmin"]), float(data["xmax"])
                        ymin, ymax = float(data["ymin"]), float(data["ymax"])
                        if xmax > 100 or ymax > 100:
                            xmin, xmax = xmin / 10.0, xmax / 10.0
                            ymin, ymax = ymin / 10.0, ymax / 10.0
                        sub_x = (xmin + xmax) / 2.0
                        sub_y = (ymin + ymax) / 2.0
                        print(f" 📐 [Zoom BBox Center] Box locale: [{xmin:.1f}%, {ymin:.1f}%, {xmax:.1f}%, {ymax:.1f}%] -> Centro locale: ({sub_x:.1f}%, {sub_y:.1f}%)")
                    else:
                        sub_x = float(data.get("x", 50.0))
                        sub_y = float(data.get("y", 50.0))
                        if sub_x > 100 or sub_y > 100:
                            sub_x /= 10.0
                            sub_y /= 10.0
                    found_coords = True
                except Exception:
                    pass

            # 2. Tentativo di parse tupla nativa (es. UI-TARS "(520,480)")
            if not found_coords:
                match_tuple = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)?", raw_response)
                if match_tuple:
                    sub_x = float(match_tuple.group(1))
                    sub_y = float(match_tuple.group(2))
                    if sub_x > 100 or sub_y > 100:
                        sub_x /= 10.0
                        sub_y /= 10.0
                    found_coords = True

            # Salva l'immagine di debug evidenziata sulla sotto-immagine ritagliata
            highlight_tap_on_image(cropped_path, sub_x, sub_y, cropped_path.replace(".png", "_tapped.png"))

            # Fase 3: Trasformazione da coordinate locali della sub-immagine a coordinate globali dello schermo
            final_global_x = crop_xmin_pct + (sub_x / 100.0) * (crop_xmax_pct - crop_xmin_pct)
            final_global_y = crop_ymin_pct + (sub_y / 100.0) * (crop_ymax_pct - crop_ymin_pct)
            
            print(f" 🎯 [Zoom Refinement Complete] Coord Locale: ({sub_x:.1f}%, {sub_y:.1f}%) -> Coord Globale Affinata: ({final_global_x:.2f}%, {final_global_y:.2f}%)")
            return final_global_x, final_global_y

        except Exception as e:
            print(f" ⚠️ [Zoom Warning] Impossibile eseguire l'affinamento dello zoom ({e}), uso coordinata globale standard.")
            
        return coarse_x, coarse_y

    def verify_assertion(self, image_path: str, assertion_description: str) -> Dict[str, Any]:
        """Esegue un'asserzione visiva sullo screenshot attuale."""
        prompt = (
            f"Verifica se la seguente asserzione è vera basandoti sullo screenshot attuale:\n"
            f"Asserzione: '{assertion_description}'.\n"
            f"Rispondi ESCLUSIVAMENTE in formato JSON valido:\n"
            f'{{"pass": true|false, "reason": "spiegazione sintetica"}}\n'
            f"Nessun altro testo."
        )

        raw_response = self.query(image_path, prompt)
        print(f"🤖 [LLM Assertion Response]: {raw_response.strip()}")

        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        
        return {"pass": False, "reason": f"Risposta LLM non formattata correttamente: {raw_response}"}


def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    print("=" * 60)
    print(" 🚀 MOBILERUN TESTER - PROOF OF CONCEPT (llama.cpp + Vision)")
    print("=" * 60)

    # 1. Carica configurazione
    if not CONFIG_FILE.exists():
        print(f"❌ File di configurazione {CONFIG_FILE} non trovato!")
        sys.exit(1)

    config = load_yaml(CONFIG_FILE)

    # 2. Avvia / Verifica llama-server
    server_mgr = LlamaServerManager(config)
    if not server_mgr.start():
        print("❌ Impossibile comunicare con llama-server. Abortito.")
        sys.exit(1)

    try:
        # 3. Connetti ADB
        device_serial = config.get("device", {}).get("serial", "")
        adb = ADBDevice(serial=device_serial)

        # 4. Inizializza Agente Vision
        vision_agent = VisionAgent(server_mgr.base_url)

        # 5. Carica Scenario YAML
        scenario_path = POC_DIR / config.get("scenario", {}).get("default_path", "poc_scenario.yaml")
        if not scenario_path.exists():
            print(f"❌ Scenario {scenario_path} non trovato!")
            sys.exit(1)

        scenario = load_yaml(scenario_path)
        print(f"\n📋 Esecuzione Scenario: {scenario.get('name')}")
        print(f"   Descrizione: {scenario.get('description')}\n")

        # 6. Esecuzione Step
        for i, step in enumerate(scenario.get("steps", []), 1):
            step_type = step.get("type")
            target = step.get("target", "")
            value = step.get("value", "")

            print(f"--- [Step {i}] Tipo: {step_type} | Target: '{target}' ---")
            
            # Nasconde la tastiera SOLO se visibile
            adb.hide_keyboard_if_shown()

            # Scatta screenshot per lo step corrente
            step_img_name = f"step_{i}_{step_type}.png"
            screenshot = adb.capture_screenshot(step_img_name)

            tap_mode = step.get("tap_mode", "burst")  # Default: 'burst' (3 tocchi a raffica) per garantire la gesture

            if step_type in ("action_until", "long_press_until"):
                until_condition = step.get("until_condition", "")
                max_retries = step.get("max_retries", 3)
                duration_ms = step.get("duration_ms", 2000)
                
                success = False
                for attempt in range(1, max_retries + 1):
                    print(f" 🔄 Tentativo {attempt}/{max_retries} per {step_type}...")
                    x_pct, y_pct = vision_agent.get_element_coordinates_with_zoom(screenshot, target)
                    highlight_tap_on_image(screenshot, x_pct, y_pct, screenshot.replace(".png", "_tapped.png"))
                    
                    if step_type == "long_press_until":
                        adb.long_press(x_pct, y_pct, duration_ms=duration_ms)
                    else:
                        adb.robust_tap(x_pct, y_pct, mode=tap_mode)
                        
                    time.sleep(1.5)
                    
                    # Verifichiamo se la condizione è soddisfatta
                    after_shot = adb.capture_screenshot(f"step_{i}_until_attempt_{attempt}.png")
                    check_res = vision_agent.verify_assertion(after_shot, until_condition)
                    
                    if check_res.get("pass"):
                        print(f" ✅ Condizione verificata con successo al tentativo {attempt}!")
                        success = True
                        break
                    else:
                        print(f" ⚠️ Condizione non ancora soddisfatta: {check_res.get('reason')}")
                        screenshot = after_shot  # Aggiorna lo screenshot per il prossimo tentativo
                
                if not success:
                    print(f" ❌ Impossibile soddisfare la condizione '{until_condition}' dopo {max_retries} tentativi.")

            elif step_type == "long_press":
                duration_ms = step.get("duration_ms", 2000)
                x_pct, y_pct = vision_agent.get_element_coordinates_with_zoom(screenshot, target)
                highlight_tap_on_image(screenshot, x_pct, y_pct, screenshot.replace(".png", "_tapped.png"))
                adb.long_press(x_pct, y_pct, duration_ms=duration_ms)
                time.sleep(2)

            elif step_type == "action":
                # Chiedi coordinate ed esegui tap robusto
                x_pct, y_pct = vision_agent.get_element_coordinates_with_zoom(screenshot, target)
                highlight_tap_on_image(screenshot, x_pct, y_pct, screenshot.replace(".png", "_tapped.png"))
                adb.robust_tap(x_pct, y_pct, mode=tap_mode)
                time.sleep(3.5)  # Pausa transizione UI/Network

            elif step_type == "type_text":
                # Trova il campo di testo con zoom, fai tap e digita
                x_pct, y_pct = vision_agent.get_element_coordinates_with_zoom(screenshot, target)
                highlight_tap_on_image(screenshot, x_pct, y_pct, screenshot.replace(".png", "_tapped.png"))
                adb.robust_tap(x_pct, y_pct, mode="tap")  # Tap standard per posizionare il cursore di testo
                time.sleep(0.5)
                adb.input_text(value)
                time.sleep(0.8)
                # Chiudi la tastiera SOLO se aperta per liberare i campi successivi
                adb.hide_keyboard_if_shown()

        # 7. Valutazione Asserzione Finale
        assertion = scenario.get("assertion", {})
        if assertion:
            print("\n🔍 --- Esecuzione Asserzione Visiva Finale ---")
            assertion_desc = assertion.get("description", "")
            final_screenshot = adb.capture_screenshot()
            
            result = vision_agent.verify_assertion(final_screenshot, assertion_desc)
            
            print("\n" + "=" * 60)
            if result.get("pass"):
                print(" ✅ RISULTATO TEST: PASSED")
            else:
                print(" ❌ RISULTATO TEST: FAILED")
            print(f" 📝 Motivazione: {result.get('reason')}")
            print("=" * 60)

    finally:
        # Pulisci o mantieni attivo il server
        if server_mgr.process:
            server_mgr.stop()


if __name__ == "__main__":
    main()
