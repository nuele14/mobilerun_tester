import base64
import json
import re
import urllib.request
from typing import Tuple, Dict, Any
from PIL import Image, ImageDraw


def highlight_tap_on_image(image_path: str, x_percent: float, y_percent: float, output_path: str):
    """Disegna un cerchio rosso semitrasparente ed un mirino sul punto del tap per il debug visivo nel report."""
    try:
        with Image.open(image_path).convert("RGBA") as base_img:
            overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            w, h = base_img.size
            cx = int((x_percent / 100.0) * w)
            cy = int((y_percent / 100.0) * h)
            
            radius = int(min(w, h) * 0.035)
            
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(255, 0, 0, 100), outline=(255, 0, 0, 230), width=4)
            draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(255, 255, 255, 255))
            
            draw.line([cx - radius - 8, cy, cx + radius + 8, cy], fill=(255, 0, 0, 220), width=2)
            draw.line([cx, cy - radius - 8, cx, cy + radius + 8], fill=(255, 0, 0, 220), width=2)
            
            combined = Image.alpha_composite(base_img, overlay)
            combined.convert("RGB").save(output_path, "PNG")
    except Exception as e:
        print(f" ⚠️ Impossibile generare immagine con evidenziazione tocco: {e}")


class VisionEngine:
    """Interagisce con il server VLM per Grounding visivo, Zoom ed Asserzioni."""

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
            "temperature": 0.0
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
        """Esegue il Grounding visivo per trovare le coordinate percentuali (0-100) dell'elemento."""
        prompt = (
            f"Analizza l'immagine dello schermo mobile.\n"
            f"Trova l'elemento descritto come: '{target_description}'.\n"
            f"Rispondi ESCLUSIVAMENTE in formato JSON valido con le coordinate percentuali (da 0 a 100):\n"
            f'{{"x": float, "y": float}}\n'
            f"Nessun altro testo prima o dopo il JSON."
        )

        raw_response = self.query(image_path, prompt)
        print(f"🤖 [VLM Response]: {raw_response.strip()}")

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

        match_tuple = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)?", raw_response)
        if match_tuple:
            x_val = float(match_tuple.group(1))
            y_val = float(match_tuple.group(2))
            if x_val > 100 or y_val > 100:
                x_val /= 10.0
                y_val /= 10.0
            print(f" 🎯 [UI-TARS Grounding] Coordinate decodificate: ({x_val:.1f}%, {y_val:.1f}%)")
            return x_val, y_val

        raise ValueError(f"Impossibile estrarre le coordinate dalla risposta VLM: {raw_response}")

    def get_element_coordinates_smart(self, image_path: str, target_description: str, force_zoom: bool = False) -> Tuple[float, float]:
        """
        Grounding veloce Single-Pass con fallback automatico a Zoom Crop in caso di errore o se esplicitamente richiesto.
        """
        if force_zoom:
            return self.get_element_coordinates_with_zoom(image_path, target_description)

        try:
            x_pct, y_pct = self.get_element_coordinates(image_path, target_description)
            print(f" ⚡ [Fast Single-Pass Vision] Coordinata individuata: ({x_pct:.1f}%, {y_pct:.1f}%)")
            return x_pct, y_pct
        except Exception as e:
            print(f" ⚠️ [Fast Vision Fallback] Attivazione Zoom Crop causa: {e}")
            return self.get_element_coordinates_with_zoom(image_path, target_description)

    def get_element_coordinates_with_zoom(self, image_path: str, target_description: str, crop_padding_pct: float = 12.0) -> Tuple[float, float]:
        """Grounding a due livelli (Coarse + Fine Zoom Crop) per elementi estremamente piccoli."""
        coarse_x, coarse_y = self.get_element_coordinates(image_path, target_description)

        try:
            img = Image.open(image_path)
            width, height = img.size
            
            crop_xmin_pct = max(0.0, coarse_x - crop_padding_pct)
            crop_xmax_pct = min(100.0, coarse_x + crop_padding_pct)
            crop_ymin_pct = max(0.0, coarse_y - crop_padding_pct)
            crop_ymax_pct = min(100.0, coarse_y + crop_padding_pct)
            
            px_xmin = int((crop_xmin_pct / 100.0) * width)
            px_xmax = int((crop_xmax_pct / 100.0) * width)
            px_ymin = int((crop_ymin_pct / 100.0) * height)
            px_ymax = int((crop_ymax_pct / 100.0) * height)
            
            cropped_img = img.crop((px_xmin, px_ymin, px_xmax, px_ymax))
            cropped_path = image_path.replace(".png", "_zoom_crop.png")
            cropped_img.save(cropped_path)
            
            fine_prompt = (
                f"Questa è una sotto-immagine INGRANDITA (ZOOM) di un'area dello schermo.\n"
                f"Individua l'elemento UI descritto come: '{target_description}'.\n"
                f"Rispondi ESCLUSIVAMENTE in formato JSON valido con i valori percentuali (0-100):\n"
                f'{{"xmin": float, "ymin": float, "xmax": float, "ymax": float, "x": float, "y": float}}\n'
                f"Nessun altro testo."
            )
            
            raw_response = self.query(cropped_path, fine_prompt)
            sub_x, sub_y = 50.0, 50.0

            match_json = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match_json:
                data = json.loads(match_json.group(0))
                sub_x = float(data.get("x", 50.0))
                sub_y = float(data.get("y", 50.0))

            final_global_x = crop_xmin_pct + (sub_x / 100.0) * (crop_xmax_pct - crop_xmin_pct)
            final_global_y = crop_ymin_pct + (sub_y / 100.0) * (crop_ymax_pct - crop_ymin_pct)
            
            return final_global_x, final_global_y
        except Exception:
            return coarse_x, coarse_y

    def verify_assertion(self, image_path: str, assertion_description: str) -> Dict[str, Any]:
        """Esegue un'asserzione visiva sullo screenshot per verificare lo stato dell'UI."""
        prompt = (
            f"Verifica se la seguente asserzione è vera basandoti sullo screenshot attuale:\n"
            f"Asserzione: '{assertion_description}'.\n"
            f"Rispondi ESCLUSIVAMENTE in formato JSON valido:\n"
            f'{{"pass": true|false, "reason": "spiegazione sintetica"}}\n'
            f"Nessun altro testo."
        )

        raw_response = self.query(image_path, prompt)

        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        
        return {"pass": False, "reason": f"Risposta VLM non formattata: {raw_response}"}
