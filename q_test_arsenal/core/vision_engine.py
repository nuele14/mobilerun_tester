"""
===============================================================================
[Design] VISION ENGINE: 2-Pass Grounding (Coarse + Fine Bounding Box Zoom)
Exact precision restoration matching commit 90e2091df90e36f30374960c2f3353a5a563ac45.
1. Pass 1: Global coarse grounding on full screenshot.
2. Pass 2: Fine Bounding Box Zoom Crop (24% x 24%) calculating exact element center.
3. High-visibility visual overlays with red target rings and description labels.
===============================================================================
"""

import base64
import json
import re
import time
import urllib.request
from typing import Tuple, Dict, Any
from PIL import Image, ImageDraw
from q_test_arsenal.core.logger import GetLogger


# === [ SECTION 1: VISUAL OVERLAY ] ===

def DrawTapTargetHighlight(img_path: str, x_pct: float, y_pct: float, out_path: str = None, target_desc: str = "") -> str:
    """[Function] Draws high-visibility target ring, crosshair (+), and label tag box on screenshot."""
    if not out_path:
        out_path = img_path.replace(".png", "_tapped.png")

    try:
        with Image.open(img_path).convert("RGBA") as img:
            draw = ImageDraw.Draw(img)
            w, h = img.size
            px_x = int((x_pct / 100.0) * w)
            px_y = int((y_pct / 100.0) * h)
            
            radius = max(24, int(w * 0.035))
            
            # Cerchio rosso principale con bordo spesso (width=8)
            bbox = [px_x - radius, px_y - radius, px_x + radius, px_y + radius]
            draw.ellipse(bbox, outline=(255, 0, 0, 255), width=8)
            
            # Punto centrale rosso pieno
            draw.ellipse([px_x - 6, px_y - 6, px_x + 6, px_y + 6], fill=(255, 0, 0, 255))
            
            # Mirino a croce (+)
            line_len = radius + 15
            draw.line([px_x - line_len, px_y, px_x + line_len, px_y], fill=(255, 0, 0, 255), width=4)
            draw.line([px_x, px_y - line_len, px_x, px_y + line_len], fill=(255, 0, 0, 255), width=4)
            
            # Tag Box / Etichetta con target e coordinate
            clean_desc = target_desc if len(target_desc) <= 30 else target_desc[:27] + "..."
            label_text = f"TAP ({x_pct:.1f}%, {y_pct:.1f}%) -> '{clean_desc}'" if clean_desc else f"TAP ({x_pct:.1f}%, {y_pct:.1f}%)"
            
            box_width = len(label_text) * 9 + 20
            box_height = 30
            
            tag_x1 = max(10, min(px_x - box_width // 2, w - box_width - 10))
            tag_y1 = px_y + radius + 10 if px_y + radius + 40 < h else px_y - radius - 38
            tag_x2 = tag_x1 + box_width
            tag_y2 = tag_y1 + box_height
            
            # Sfondo rosso semi-trasparente per l'etichetta
            draw.rectangle([tag_x1, tag_y1, tag_x2, tag_y2], fill=(255, 0, 0, 220), outline=(255, 255, 255, 255), width=1)
            draw.text((tag_x1 + 10, tag_y1 + 7), label_text, fill=(255, 255, 255, 255))
            
            img.convert("RGB").save(out_path, "PNG")
            GetLogger().info(f"Visual debug tap overlay saved to: {out_path}")
            return out_path
    except Exception as e:
        GetLogger().warning(f"Overlay generation failed for {img_path}: {e}")
        return img_path


# === [ SECTION 2: VISION ENGINE ] ===

class VisionEngine:
    """[Teacher] Client for VLM completion API (Qwen2-VL / UI-TARS) using commit 90e2091 precision logic."""

    def __init__(self, server_url: str):
        self.api_url = f"{server_url}/v1/chat/completions"

    def DispatchVlmQuery(self, img_path: str, prompt: str) -> str:
        """[Function] Sends base64 image and prompt to VLM endpoint with temperature 0.1 (matching commit 90e2091)."""
        with open(img_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")
            
        payload = {
            "model": "qwen2-vl",
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}]}],
            "temperature": 0.1
        }
        req = urllib.request.Request(self.api_url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"]

    def PredictElementCoordinates(self, img_path: str, target_desc: str) -> Tuple[float, float]:
        """[Function] Coarse Pass 1 predicting approximate percentage (x%, y%) coordinates."""
        prompt = (
            f"Analizza l'immagine dello schermo mobile.\n"
            f"Trova l'elemento descritto come: '{target_desc}'.\n"
            f"Rispondi ESCLUSIVAMENTE in formato JSON valido con le coordinate percentuali (da 0 a 100):\n"
            f'{{"x": float, "y": float}}\n'
            f"Nessun altro testo prima o dopo il JSON."
        )
        resp = self.DispatchVlmQuery(img_path, prompt)
        GetLogger().debug(f"[LLM Coarse Vision Response]: {resp.strip()}")

        m_json = re.search(r"\{.*\}", resp, re.DOTALL)
        if m_json:
            try:
                d = json.loads(m_json.group(0))
                x = float(d.get("x", 50.0))
                y = float(d.get("y", 50.0))
                if x > 100 or y > 100:
                    x /= 10.0
                    y /= 10.0
                return x, y
            except Exception:
                pass

        m_tup = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)?", resp)
        if m_tup:
            x = float(m_tup.group(1))
            y = float(m_tup.group(2))
            if x > 100 or y > 100:
                x /= 10.0
                y /= 10.0
            return x, y

        raise ValueError(f"Impossibile estrarre le coordinate dalla risposta: {resp}")

    def PredictCoordinatesWithZoom(self, img_path: str, target_desc: str, pad_pct: float = 12.0) -> Tuple[float, float, Dict[str, Any]]:
        """
        [Function] Grounding a 2 livelli (Coarse + Fine Bounding Box Zoom) da commit 90e2091:
        1. Trova le coordinate approssimative sull'immagine intera (Coarse).
        2. Genera un Crop (Zoom 24% x 24%) attorno all'area individuata.
        3. Chiede la Bounding Box (xmin, ymin, xmax, ymax) e calcola il centro esatto dell'elemento.
        4. Trasforma le coordinate locali della sotto-immagine in coordinate globali dello schermo.
        """
        logger = GetLogger()
        start_p1 = time.time()
        coarse_x, coarse_y = self.PredictElementCoordinates(img_path, target_desc)
        pass1_ms = int((time.time() - start_p1) * 1000)
        logger.info(f"🔍 [Zoom Phase 1] Coordinata globale approssimativa: ({coarse_x:.1f}%, {coarse_y:.1f}%) [{pass1_ms}ms]")

        pass2_ms = 0
        raw_response = ""

        try:
            img = Image.open(img_path)
            w, h = img.size

            crop_xmin_pct = max(0.0, coarse_x - pad_pct)
            crop_xmax_pct = min(100.0, coarse_x + pad_pct)
            crop_ymin_pct = max(0.0, coarse_y - pad_pct)
            crop_ymax_pct = min(100.0, coarse_y + pad_pct)

            px_xmin = int((crop_xmin_pct / 100.0) * w)
            px_xmax = int((crop_xmax_pct / 100.0) * w)
            px_ymin = int((crop_ymin_pct / 100.0) * h)
            px_ymax = int((crop_ymax_pct / 100.0) * h)

            cropped_img = img.crop((px_xmin, px_ymin, px_xmax, px_ymax))
            cropped_path = img_path.replace(".png", "_zoom_crop.png")
            cropped_img.save(cropped_path)
            logger.info(f"🔎 [Zoom Phase 2] Sotto-immagine ritagliata e zoomata salvata in: {cropped_path}")

            fine_prompt = (
                f"Questa è una sotto-immagine INGRANDITA (ZOOM) di un'area dello schermo.\n"
                f"Individua l'elemento UI descritto come: '{target_desc}'.\n"
                f"Trova la scatola (bounding box) che racchiude interamente questo elemento.\n"
                f"Rispondi ESCLUSIVAMENTE in formato JSON valido con i valori percentuali (0-100):\n"
                f'{{"xmin": float, "ymin": float, "xmax": float, "ymax": float, "x": float, "y": float}}\n'
                f"Nessun altro testo prima o dopo il JSON."
            )
            start_p2 = time.time()
            raw_response = self.DispatchVlmQuery(cropped_path, fine_prompt)
            pass2_ms = int((time.time() - start_p2) * 1000)
            logger.debug(f"🤖 [LLM Fine Zoom Response]: {raw_response.strip()} [{pass2_ms}ms]")

            sub_x, sub_y = 50.0, 50.0
            found_coords = False

            # 1. Tentativo di parse Bounding Box JSON (centraggio esatto del rettangolo)
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
                        logger.info(f"📐 [Zoom BBox Center] Box locale: [{xmin:.1f}%, {ymin:.1f}%, {xmax:.1f}%, {ymax:.1f}%] -> Centro locale: ({sub_x:.1f}%, {sub_y:.1f}%)")
                    else:
                        sub_x = float(data.get("x", 50.0))
                        sub_y = float(data.get("y", 50.0))
                        if sub_x > 100 or sub_y > 100:
                            sub_x /= 10.0
                            sub_y /= 10.0
                    found_coords = True
                except Exception:
                    pass

            # 2. Tentativo parse tupla
            if not found_coords:
                match_tuple = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)?", raw_response)
                if match_tuple:
                    sub_x = float(match_tuple.group(1))
                    sub_y = float(match_tuple.group(2))
                    if sub_x > 100 or sub_y > 100:
                        sub_x /= 10.0
                        sub_y /= 10.0
                    found_coords = True

            cropped_tapped_path = cropped_path.replace(".png", "_tapped.png")
            DrawTapTargetHighlight(cropped_path, sub_x, sub_y, cropped_tapped_path, target_desc=target_desc)

            # Trasformazione da coordinate locali del crop a coordinate globali dello schermo
            final_global_x = crop_xmin_pct + (sub_x / 100.0) * (crop_xmax_pct - crop_xmin_pct)
            final_global_y = crop_ymin_pct + (sub_y / 100.0) * (crop_ymax_pct - crop_ymin_pct)

            logger.info(f"🎯 [Zoom Refinement Complete] Coord Locale: ({sub_x:.1f}%, {sub_y:.1f}%) -> Coord Globale Affinata: ({final_global_x:.2f}%, {final_global_y:.2f}%)")
            metrics = {
                "pass1_ms": pass1_ms,
                "pass2_ms": pass2_ms,
                "vlm_total_ms": pass1_ms + pass2_ms,
                "coarse_x": coarse_x,
                "coarse_y": coarse_y,
                "sub_x": sub_x,
                "sub_y": sub_y,
                "final_x": final_global_x,
                "final_y": final_global_y,
                "cropped_path": cropped_path,
                "cropped_tapped_path": cropped_tapped_path,
                "raw_response": raw_response
            }
            return final_global_x, final_global_y, metrics

        except Exception as e:
            logger.warning(f"⚠️ [Zoom Warning] Impossibile eseguire l'affinamento dello zoom ({e}), uso coordinata globale standard.")

        metrics = {
            "pass1_ms": pass1_ms,
            "pass2_ms": pass2_ms,
            "vlm_total_ms": pass1_ms + pass2_ms,
            "coarse_x": coarse_x,
            "coarse_y": coarse_y,
            "sub_x": 50.0,
            "sub_y": 50.0,
            "final_x": coarse_x,
            "final_y": coarse_y,
            "cropped_path": "",
            "cropped_tapped_path": "",
            "raw_response": raw_response
        }
        return coarse_x, coarse_y, metrics

    def PredictCoordinatesFast(self, img_path: str, target_desc: str, force_zoom: bool = True) -> Tuple[float, float, Dict[str, Any]]:
        """[Function] Always uses 2-Pass Bounding-Box Zoom Grounding for exact target accuracy."""
        return self.PredictCoordinatesWithZoom(img_path, target_desc)

    def VerifyScreenAssertion(self, img_path: str, assertion_desc: str) -> Dict[str, Any]:
        """[Function] Evaluates visual assertion matching commit 90e2091."""
        start_t = time.time()
        prompt = (
            f"Verifica se la seguente asserzione è vera basandoti sullo screenshot attuale:\n"
            f"Asserzione: '{assertion_desc}'.\n"
            f"Rispondi ESCLUSIVAMENTE in formato JSON valido:\n"
            f'{{"pass": true|false, "reason": "spiegazione sintetica"}}\n'
            f"Nessun altro testo."
        )
        raw_response = self.DispatchVlmQuery(img_path, prompt)
        vlm_ms = int((time.time() - start_t) * 1000)
        GetLogger().debug(f"🤖 [LLM Assertion Response]: {raw_response.strip()} [{vlm_ms}ms]")
        m = re.search(r"\{.*\}", raw_response, re.DOTALL)
        res = json.loads(m.group(0)) if m else {"pass": False, "reason": f"Risposta LLM non formattata correttamente: {raw_response}"}
        res["vlm_ms"] = vlm_ms
        res["raw_response"] = raw_response
        return res
