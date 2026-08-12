"""
===============================================================================
[Design] MACRO MANAGER: Action-level recording, visual state matching, & replay.
1. Saves executed scenario steps into structured JSON (schema v2.0).
2. Computes perceptual image hashes (imagehash.phash) for screen state matching.
3. Fast-path replay execution when screen matches (>= 85% similarity).
4. Automatic fallback (handoff) to VLM when UI divergence is detected.
===============================================================================
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image
import imagehash
from mobilerun_tester.core.logger import GetLogger, console


class MacroManager:
    """[Teacher] Manages recording, storage, perceptual screen matching, and fast-path replay."""

    def __init__(self, macros_dir: str = "scenarios/macros"):
        self.macros_dir = Path(macros_dir)
        self.macros_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def ComputeScreenHash(image_path: str) -> str:
        """[Function] Computes perceptual pHash of a screenshot file."""
        try:
            with Image.open(image_path) as img:
                return str(imagehash.phash(img))
        except Exception as e:
            GetLogger().warning(f"Could not compute pHash for {image_path}: {e}")
            return ""

    @staticmethod
    def CompareScreenHashes(hash1: str, hash2: str) -> float:
        """
        [Function] Returns similarity score (0.0 to 1.0) between two pHash strings.
        Perceptual pHash uses 64-bit hexadecimal strings. Maximum Hamming distance is 64.
        """
        if not hash1 or not hash2:
            return 0.0
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            distance = h1 - h2
            similarity = round(max(0.0, 1.0 - (distance / 64.0)), 4)
            return similarity
        except Exception:
            return 0.0

    def GetMacroFilePath(self, scenario_path: str) -> Path:
        """[Function] Resolves macro destination path for a given scenario file."""
        stem = Path(scenario_path).stem
        return self.macros_dir / f"{stem}.macro.json"

    def SaveMacroSequence(self, scenario_path: str, scenario_name: str, actions: List[Dict[str, Any]], device_info: Dict[str, Any]) -> str:
        """[Function] Writes recorded macro actions to JSON file."""
        logger = GetLogger()
        out_path = self.GetMacroFilePath(scenario_path)

        macro_payload = {
            "version": "2.0",
            "created_at_ms": int(time.time() * 1000),
            "scenario_name": scenario_name,
            "device": device_info,
            "actions": actions
        }

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(macro_payload, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved macro sequence ({len(actions)} actions) to {out_path}")
            console.print(f"💾 [bold green]Macro salvata con successo:[/bold green] [dim]{out_path}[/dim]")
            return str(out_path)
        except Exception as e:
            logger.error(f"Failed to save macro sequence: {e}")
            return ""

    def LoadMacroSequence(self, scenario_path: str) -> Optional[Dict[str, Any]]:
        """[Function] Loads macro sequence JSON for a given scenario."""
        macro_path = self.GetMacroFilePath(scenario_path)
        if not macro_path.exists():
            return None
        try:
            with open(macro_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            GetLogger().warning(f"Could not load macro {macro_path}: {e}")
            return None
