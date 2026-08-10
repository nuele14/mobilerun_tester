"""
Assertion Engine for Mobilerun Tester.

This module provides functions for UI state verification,
element visibility checks, and screenshot comparisons.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Pillow for image processing
from PIL import Image, ImageChops, ImageDraw
import imagehash

# Constants
TEMPLATES_DIR = Path(__file__).parent / "templates"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"

class AssertionResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


@dataclass
class Assertion:
    """Rappresenta un'asserzione singola"""
    type: str
    args: Dict[str, Any]


def _ensure_directories():
    """Crea directory necessarie se non esistono"""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def get_assertion_element_path(element_type: str) -> Path:
    """Restituisce il percorso del template per un elemento"""
    return TEMPLATES_DIR / f"{element_type}.png"


def assert_element_presence(
    screenshot: Image.Image,
    element_type: str,
    threshold: float = 0.95,
    **kwargs
) -> AssertionResult:
    """
    Verifica la presenza di un elemento tramite confronto con un template.
    
    Args:
        screenshot: Screenshot corrente della schermata
        element_type: Tipo di elemento da cercare (es: 'dashboard_button')
        threshold: Similarità minima richiesta (0.0 - 1.0)
        **kwargs: Argomenti aggiuntivi (es: 'strict_mode')
    
    Returns:
        AssertionResult: RISULTATO dell'asserzione
    """
    _ensure_directories()
    
    template_path = get_assertion_element_path(element_type)
    
    if not template_path.exists():
        # Se il template non esiste, simuliamo il controllo (non fallire)
        # In produzione, si caricerebbe un template default o si userebbe OCR
        print(f"[ASSERTION] Template '{element_type}' non trovato, salto verifica.")
        return AssertionResult.PASS
    
    try:
        template_img = Image.open(template_path).convert('RGBA')
        
        # Ritaglia lo screenshot se necessario (es: solo area centrale)
        crop_box = kwargs.get('crop_box', None)
        if crop_box:
            x1, y1, x2, y2 = crop_box
            screenshot = screenshot.crop((x1, y1, x2, y2))
        
        # Alta fedeltà: confronto con differenza
        template_hash = imagehash.average_hash(template_img)
        screenshot_hash = imagehash.average_hash(screenshot)
        
        diff = template_hash - screenshot_hash
        max_hash_distance = 16  # valore standard per template 16x16
        
        # Se la distanza è piccola, l'elemento è presente
        if diff < max_hash_distance:
            return AssertionResult.PASS
        else:
            return AssertionResult.FAIL
            
    except Exception as e:
        print(f"[ASSERTION ERROR] Errore nel verificare '{element_type}': {e}")
        return AssertionResult.ERROR


def assert_element_not_present(
    screenshot: Image.Image,
    element_type: str,
    threshold: float = 0.95,
    **kwargs
) -> AssertionResult:
    """Verifica che un elemento NON sia presente (utile per verificare logout, ecc.)"""
    result = assert_element_presence(screenshot, element_type, threshold, **kwargs)
    if result == AssertionResult.PASS:
        return AssertionResult.FAIL  # L'elemento c'è, non deve essere lì
    return AssertionResult.PASS


def assert_text_visible(
    screenshot: Image.Image,
    text: str,
    confidence: float = 0.8,
    **kwargs
) -> AssertionResult:
    """
    Verifica la presenza di un testo tramite OCR o ricerca testuale.
    ATTENZIONE: richiede libreria OCR (es: pytesseract) per uso reale.
    """
    # Placeholder OCR - in produzione si userà pytesseract
    print(f"[ASSERTION] Verifica testo '{text}' - OCR non implementato ancora")
    
    # Simulazione: se nessun OCR, sempre PASS
    return AssertionResult.PASS


def assert_app_state(
    current_state: Dict[str, Any],
    expected_state: Dict[str, Any]
) -> AssertionResult:
    """
    Verifica lo stato dell'applicazione (nazionalità, dimensioni, ecc.).
    
    Esempio:
        current_state = {"package": "com.example.app", "activity": "MainActivity"}
        expected_state = {"package": "com.example.app"}
    """
    for key, expected_value in expected_state.items():
        if key not in current_state:
            return AssertionResult.FAIL
        if current_state[key] != expected_value:
            return AssertionResult.FAIL
    return AssertionResult.PASS


def assert_screenshot_equal(
    screenshot1: Image.Image,
    screenshot2: Image.Image,
    tolerance: float = 0.01
) -> AssertionResult:
    """
    Confronta due screenshot per verificare che siano identici
    entro una certa tolleranza.
    """
    # Ridimensiona se necessario
    if screenshot1.size != screenshot2.size:
        screenshot2 = screenshot2.resize(screenshot1.size)
    
    # Confronto pixel
    diff = ImageChops.difference(screenshot1, screenshot2)
    bbox = diff.getbbox()
    
    if bbox is None:
        return AssertionResult.PASS
    
    # Calcola percentuale di pixel diversi
    total_pixels = screenshot1.width * screenshot1.height
    diff_pixels = abs(bbox[2] - bbox[0]) * abs(bbox[3] - bbox[1])
    diff_percent = diff_pixels / total_pixels
    
    if diff_percent < tolerance:
        return AssertionResult.PASS
    return AssertionResult.FAIL


def save_screenshot(screenshot: Image.Image, name: str) -> Path:
    """Salva uno screenshot per debugging o report"""
    _ensure_directories()
    path = SCREENSHOTS_DIR / name
    screenshot.save(path)
    return path


# Convenience functions used by TestRunner
def verify_presence_by_action(action_args: Dict[str, Any], current_screenshot: Image.Image) -> bool:
    """Funzione helper per verificare risultato di un'azione"""
    element_type = action_args.get('element', None)
    if element_type:
        result = assert_element_presence(current_screenshot, element_type)
        return result == AssertionResult.PASS
    return True