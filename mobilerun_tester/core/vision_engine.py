"""
===============================================================================
[Design] VISION ENGINE: Fast single-pass grounding and visual assertions.
1. Predicts (x%, y%) coordinates on full screenshots in 1 pass.
2. Triggers 24% x 24% Zoom Crop fallback only on precision errors.
3. Evaluates visual assertion prompts returning structured JSON pass/fail status.
===============================================================================
"""

import base64
import json
import re
import urllib.request
from typing import Tuple, Dict, Any
from PIL import Image, ImageDraw
from mobilerun_tester.core.logger import GetLogger


# === [ SECTION 1: VISUAL OVERLAY ] ===

def DrawTapTargetHighlight(img_path: str, x_pct: float, y_pct: float, out_path: str):
    """[Function] Draws red circle target highlight on screenshot for debug reports."""
    try:
        with Image.open(img_path).convert("RGBA") as base:
            overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            w, h = base.size
            cx, cy = int((x_pct / 100.0) * w), int((y_pct / 100.0) * h)
            r = int(min(w, h) * 0.035)
            
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 0, 0, 100), outline=(255, 0, 0, 230), width=4)
            draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(255, 255, 255, 255))
            draw.line([cx - r - 8, cy, cx + r + 8, cy], fill=(255, 0, 0, 220), width=2)
            draw.line([cx, cy - r - 8, cx, cy + r + 8], fill=(255, 0, 0, 220), width=2)
            
            Image.alpha_composite(base, overlay).convert("RGB").save(out_path, "PNG")
    except Exception as e:
        GetLogger().warning(f"Overlay generation failed: {e}")


# === [ SECTION 2: VISION ENGINE ] ===

class VisionEngine:
    """[Teacher] Client for VLM completion API (Qwen2-VL / UI-TARS)."""

    def __init__(self, server_url: str):
        self.api_url = f"{server_url}/v1/chat/completions"

    def DispatchVlmQuery(self, img_path: str, prompt: str) -> str:
        """[Function] Sends base64 image and prompt to VLM endpoint with temperature 0.0."""
        with open(img_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")
            
        payload = {
            "model": "qwen2-vl",
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}]}],
            "temperature": 0.0
        }
        req = urllib.request.Request(self.api_url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"]

    def PredictElementCoordinates(self, img_path: str, target_desc: str) -> Tuple[float, float]:
        """[Function] Single-pass grounding predicting percentage (x%, y%) coordinates."""
        prompt = f"Analizza lo schermo. Trova: '{target_desc}'. Rispondi ESCLUSIVAMENTE JSON: {{\"x\": float, \"y\": float}}"
        resp = self.DispatchVlmQuery(img_path, prompt)
        GetLogger().debug(f"[VLM Response]: {resp.strip()}")

        m_json = re.search(r"\{.*\}", resp, re.DOTALL)
        if m_json:
            try:
                d = json.loads(m_json.group(0))
                x, y = float(d.get("x", 50.0)), float(d.get("y", 50.0))
                return (x / 10.0 if x > 100 else x), (y / 10.0 if y > 100 else y)
            except Exception:
                pass

        m_tup = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\)?", resp)
        if m_tup:
            x, y = float(m_tup.group(1)), float(m_tup.group(2))
            return (x / 10.0 if x > 100 else x), (y / 10.0 if y > 100 else y)

        raise ValueError(f"Could not parse VLM response: {resp}")

    def PredictCoordinatesFast(self, img_path: str, target_desc: str, force_zoom: bool = False) -> Tuple[float, float]:
        """[Function] Fast single-pass grounding with automatic Zoom Crop fallback."""
        if force_zoom:
            return self.PredictCoordinatesWithZoom(img_path, target_desc)
        try:
            x, y = self.PredictElementCoordinates(img_path, target_desc)
            GetLogger().debug(f"[Fast Vision] ({x:.1f}%, {y:.1f}%)")
            return x, y
        except Exception as e:
            GetLogger().warning(f"[Vision Fallback] Zoom Crop: {e}")
            return self.PredictCoordinatesWithZoom(img_path, target_desc)

    def PredictCoordinatesWithZoom(self, img_path: str, target_desc: str, pad_pct: float = 12.0) -> Tuple[float, float]:
        """[Function] 2-Pass Fine Grounding zooming a 24% x 24% crop region."""
        cx, cy = self.PredictElementCoordinates(img_path, target_desc)
        try:
            img = Image.open(img_path)
            w, h = img.size
            x1, x2 = max(0.0, cx - pad_pct), min(100.0, cx + pad_pct)
            y1, y2 = max(0.0, cy - pad_pct), min(100.0, cy + pad_pct)
            
            crop_path = img_path.replace(".png", "_zoom_crop.png")
            img.crop((int(x1/100*w), int(y1/100*h), int(x2/100*w), int(y2/100*h))).save(crop_path)
            
            prompt = f"Sotto-immagine ingrandita. Trova: '{target_desc}'. Rispondi JSON: {{\"x\": float, \"y\": float}}"
            resp = self.DispatchVlmQuery(crop_path, prompt)
            
            m_json = re.search(r"\{.*\}", resp, re.DOTALL)
            sub_x, sub_y = 50.0, 50.0
            if m_json:
                d = json.loads(m_json.group(0))
                sub_x, sub_y = float(d.get("x", 50.0)), float(d.get("y", 50.0))
                
            return x1 + (sub_x / 100.0) * (x2 - x1), y1 + (sub_y / 100.0) * (y2 - y1)
        except Exception:
            return cx, cy

    def VerifyScreenAssertion(self, img_path: str, assertion_desc: str) -> Dict[str, Any]:
        """[Function] Evaluates natural language visual assertion prompt."""
        prompt = f"Verifica asserzione sullo screenshot: '{assertion_desc}'. Rispondi ESCLUSIVAMENTE JSON: {{\"pass\": true|false, \"reason\": \"spiegazione\"}}"
        resp = self.DispatchVlmQuery(img_path, prompt)
        m = re.search(r"\{.*\}", resp, re.DOTALL)
        return json.loads(m.group(0)) if m else {"pass": False, "reason": f"Unformatted VLM response: {resp}"}

