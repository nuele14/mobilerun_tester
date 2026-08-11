import time
from pathlib import Path
from typing import Dict, Any, List
from mobilerun_tester.core.adb_engine import ADBDevice
from mobilerun_tester.core.vision_engine import VisionEngine, highlight_tap_on_image
from mobilerun_tester.core.server_manager import LlamaServerManager
from mobilerun_tester.core.scenario_parser import ScenarioParser


class TestRunner:
    """Esegue gli scenari di test registrando tempi, log ed esiti delle asserzioni visive."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.server_mgr = LlamaServerManager(config)
        self.reports_dir = Path(config.get("runner", {}).get("reports_dir", "reports"))
        self.screenshots_dir = Path(config.get("runner", {}).get("debug_screenshots_dir", "reports/screenshots"))
        
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def run_scenario(self, scenario_path: str) -> Dict[str, Any]:
        """Esegue uno scenario YAML completo restituendo il report dell'esecuzione."""
        scenario = ScenarioParser.load_scenario(scenario_path)
        print(f"\n📋 [MobileRun Suite] Avvio Scenario: '{scenario.get('name')}'")
        print(f"   Descrizione: {scenario.get('description')}\n")

        if not self.server_mgr.start():
            raise RuntimeError("Impossibile avviare llama-server VLM Engine.")

        device_serial = self.config.get("device", {}).get("serial", "")
        adb = ADBDevice(serial=device_serial)
        vision_engine = VisionEngine(self.server_mgr.base_url)

        start_time = time.time()
        step_results: List[Dict[str, Any]] = []
        overall_passed = True

        try:
            for i, step in enumerate(scenario.get("steps", []), 1):
                step_start = time.time()
                step_type = step.get("type")
                target = step.get("target", "")
                value = step.get("value", "")
                use_zoom = step.get("use_zoom", False)

                print(f"--- [Step {i}] Tipo: {step_type} | Target: '{target}' ---")
                
                adb.hide_keyboard_if_shown()
                shot_name = f"step_{i}_{step_type}.png"
                shot_path = str(self.screenshots_dir / shot_name)
                adb.capture_screenshot(shot_path)

                tap_mode = step.get("tap_mode", "tap")
                step_passed = True
                step_notes = ""

                if step_type in ("action_until", "long_press_until"):
                    until_condition = step.get("until_condition", "")
                    max_retries = step.get("max_retries", 3)
                    duration_ms = step.get("duration_ms", 2000)

                    check_initial = vision_engine.verify_assertion(shot_path, until_condition)
                    if check_initial.get("pass"):
                        print(f" ✅ Condizione '{until_condition}' già soddisfatta! Procedo.")
                        step_notes = f"Condizione '{until_condition}' già verificata prima del tap."
                    else:
                        success = False
                        for attempt in range(1, max_retries + 1):
                            print(f" 🔄 Tentativo {attempt}/{max_retries}...")
                            x_pct, y_pct = vision_engine.get_element_coordinates_smart(shot_path, target, force_zoom=use_zoom)
                            tapped_shot = shot_path.replace(".png", "_tapped.png")
                            highlight_tap_on_image(shot_path, x_pct, y_pct, tapped_shot)

                            if step_type == "long_press_until":
                                adb.long_press(x_pct, y_pct, duration_ms=duration_ms)
                            else:
                                adb.robust_tap(x_pct, y_pct, mode=tap_mode)

                            time.sleep(0.8)
                            after_shot = str(self.screenshots_dir / f"step_{i}_until_attempt_{attempt}.png")
                            adb.capture_screenshot(after_shot)
                            check_res = vision_engine.verify_assertion(after_shot, until_condition)

                            if check_res.get("pass"):
                                print(f" ✅ Condizione verificata con successo al tentativo {attempt}!")
                                success = True
                                step_notes = f"Condizione verificata al tentativo {attempt}."
                                break
                            else:
                                shot_path = after_shot

                        if not success:
                            step_passed = False
                            overall_passed = False
                            step_notes = f"Condizione '{until_condition}' non soddisfatta dopo {max_retries} tentativi."

                elif step_type == "action":
                    x_pct, y_pct = vision_engine.get_element_coordinates_smart(shot_path, target, force_zoom=use_zoom)
                    tapped_shot = shot_path.replace(".png", "_tapped.png")
                    highlight_tap_on_image(shot_path, x_pct, y_pct, tapped_shot)
                    adb.robust_tap(x_pct, y_pct, mode=tap_mode)
                    time.sleep(1.0)
                    step_notes = f"Tap eseguito a ({x_pct:.1f}%, {y_pct:.1f}%)"

                elif step_type == "type_text":
                    x_pct, y_pct = vision_engine.get_element_coordinates_smart(shot_path, target, force_zoom=use_zoom)
                    tapped_shot = shot_path.replace(".png", "_tapped.png")
                    highlight_tap_on_image(shot_path, x_pct, y_pct, tapped_shot)
                    adb.robust_tap(x_pct, y_pct, mode="tap")
                    time.sleep(0.2)
                    adb.input_text(value)
                    time.sleep(0.3)
                    adb.hide_keyboard_if_shown()
                    step_notes = f"Inserito testo '{value}' a ({x_pct:.1f}%, {y_pct:.1f}%)"

                step_duration = round(time.time() - step_start, 2)
                step_results.append({
                    "step_index": i,
                    "type": step_type,
                    "target": target,
                    "passed": step_passed,
                    "duration_seconds": step_duration,
                    "screenshot": shot_path,
                    "tapped_screenshot": shot_path.replace(".png", "_tapped.png"),
                    "notes": step_notes
                })

            # Valutazione Asserzione Visiva Finale dello Scenario
            assertion = scenario.get("assertion", {})
            assertion_passed = True
            assertion_reason = "Nessuna asserzione finale specificata."
            
            if assertion:
                print("\n🔍 --- Esecuzione Asserzione Visiva Finale ---")
                assertion_desc = assertion.get("description", "")
                final_shot = str(self.screenshots_dir / "final_assertion_screen.png")
                adb.capture_screenshot(final_shot)
                
                result = vision_engine.verify_assertion(final_shot, assertion_desc)
                assertion_passed = bool(result.get("pass"))
                assertion_reason = str(result.get("reason"))
                if not assertion_passed:
                    overall_passed = False

            total_duration = round(time.time() - start_time, 2)
            
            summary = {
                "scenario_name": scenario.get("name"),
                "passed": overall_passed,
                "total_duration_seconds": total_duration,
                "steps": step_results,
                "final_assertion": {
                    "passed": assertion_passed,
                    "reason": assertion_reason
                }
            }

            print("\n" + "=" * 60)
            if overall_passed:
                print(" ✅ RISULTATO SUITE TEST: PASSED")
            else:
                print(" ❌ RISULTATO SUITE TEST: FAILED")
            print(f" ⏱️ Tempo Totale: {total_duration}s")
            print(f" 📝 Motivazione Asserzione Finale: {assertion_reason}")
            print("=" * 60)

            return summary

        finally:
            if self.server_mgr.process:
                self.server_mgr.stop()
