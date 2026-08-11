import time
from pathlib import Path
from typing import Dict, Any, List
from mobilerun_tester.core.adb_engine import ADBDevice
from mobilerun_tester.core.vision_engine import VisionEngine, DrawTapTargetHighlight
from mobilerun_tester.core.server_manager import LlamaServerManager
from mobilerun_tester.core.scenario_parser import ScenarioParser
from mobilerun_tester.core.logger import GetLogger, GetLogFilePath, StatusSpinner, console


class TestRunner:
    """[Teacher] Orchestrates test steps and gathers performance metrics."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.server_mgr = LlamaServerManager(config)
        self.reports_dir = Path(config.get("runner", {}).get("reports_dir", "reports"))
        self.screenshots_dir = Path(config.get("runner", {}).get("debug_screenshots_dir", "reports/screenshots"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def ExecuteTestScenario(self, scenario_path: str) -> Dict[str, Any]:
        """[Function] Runs complete scenario step loop returning telemetry dictionary."""
        logger = GetLogger()
        scenario = ScenarioParser.LoadTestScenario(scenario_path)
        scenario_name = scenario.get("name", "Unknown Scenario")
        
        logger.info(f"Starting test scenario: '{scenario_name}' ({scenario_path})")
        console.print(f"\n📋 [bold yellow]Scenario:[/bold yellow] [bold white]{scenario_name}[/bold white]")

        with StatusSpinner("🦙 Inizializzazione server Llama VLM..."):
            if not self.server_mgr.StartLlamaServer():
                logger.error("Failed to start VLM server.")
                raise RuntimeError("Failed to start VLM server.")

        adb = ADBDevice(serial=self.config.get("device", {}).get("serial", ""))
        vision = VisionEngine(self.server_mgr.base_url)

        start_t = time.time()
        step_results: List[Dict[str, Any]] = []
        overall_passed = True
        steps = scenario.get("steps", [])
        total_steps = len(steps)

        try:
            for i, step in enumerate(steps, 1):
                t_start = time.time()
                stype = step.get("type")
                target = step.get("target", "")
                val = step.get("value", "")
                use_zoom = step.get("use_zoom", False)
                tap_mode = step.get("tap_mode", "tap")

                logger.info(f"Executing step {i}/{total_steps}: {stype} | target='{target}' | value='{val}'")

                with StatusSpinner(f"📸 Cattura screenshot per Step {i}/{total_steps}..."):
                    adb.HideSoftKeyboard()
                    shot_path = str(self.screenshots_dir / f"step_{i}_{stype}.png")
                    adb.CaptureScreenBuffer(shot_path)

                step_passed, step_notes = True, ""

                if stype in ("action_until", "long_press_until"):
                    cond = step.get("until_condition", "")
                    with StatusSpinner(f"🔍 Verifica condizione visiva '{cond}'..."):
                        is_fulfilled = vision.VerifyScreenAssertion(shot_path, cond).get("pass")

                    if is_fulfilled:
                        step_notes = f"Condition '{cond}' verified prior to tap."
                    else:
                        succ = False
                        for att in range(1, step.get("max_retries", 3) + 1):
                            with StatusSpinner(f"🧠 Grounding VLM per '{target}' (Tentativo {att})..."):
                                x, y = vision.PredictCoordinatesFast(shot_path, target, force_zoom=use_zoom)
                                DrawTapTargetHighlight(shot_path, x, y, shot_path.replace(".png", "_tapped.png"))

                            with StatusSpinner(f"⚡ Esecuzione azione ADB ({stype}) su ({x:.1f}%, {y:.1f}%)..."):
                                if stype == "long_press_until":
                                    adb.ExecuteLongPress(x, y, duration_ms=step.get("duration_ms", 2000))
                                else:
                                    adb.DispatchRobustTap(x, y, mode=tap_mode)
                                time.sleep(0.8)

                            after_shot = str(self.screenshots_dir / f"step_{i}_until_attempt_{att}.png")
                            adb.CaptureScreenBuffer(after_shot)
                            with StatusSpinner(f"🔍 Verifica esito tentata azione..."):
                                if vision.VerifyScreenAssertion(after_shot, cond).get("pass"):
                                    succ, step_notes = True, f"Condition met at attempt {att}."
                                    break
                            shot_path = after_shot

                        if not succ:
                            step_passed = overall_passed = False
                            step_notes = f"Condition '{cond}' unfulfilled after retries."

                elif stype == "action":
                    with StatusSpinner(f"🧠 Grounding VLM & Calcolo coordinate per '{target}'..."):
                        x, y = vision.PredictCoordinatesFast(shot_path, target, force_zoom=use_zoom)
                        DrawTapTargetHighlight(shot_path, x, y, shot_path.replace(".png", "_tapped.png"))

                    with StatusSpinner(f"⚡ Esecuzione tap ADB su ({x:.1f}%, {y:.1f}%)..."):
                        adb.DispatchRobustTap(x, y, mode=tap_mode)
                        time.sleep(1.0)
                        step_notes = f"Tap at ({x:.1f}%, {y:.1f}%)"

                elif stype == "type_text":
                    with StatusSpinner(f"🧠 Grounding VLM per campo '{target}'..."):
                        x, y = vision.PredictCoordinatesFast(shot_path, target, force_zoom=use_zoom)
                        DrawTapTargetHighlight(shot_path, x, y, shot_path.replace(".png", "_tapped.png"))

                    with StatusSpinner(f"⌨️ Inserimento testo ADB: '{val}'..."):
                        adb.DispatchRobustTap(x, y, mode="tap")
                        time.sleep(0.2)
                        adb.InjectText(val)
                        time.sleep(0.3)
                        adb.HideSoftKeyboard()
                        step_notes = f"Typed '{val}' at ({x:.1f}%, {y:.1f}%)"

                dur = round(time.time() - t_start, 2)
                if step_passed:
                    console.print(f" [bold green]✔[/bold green] [bold]Step {i}/{total_steps}[/bold] {stype} | '{target}' ({dur}s)")
                else:
                    console.print(f" [bold red]✖[/bold red] [bold]Step {i}/{total_steps}[/bold] {stype} | '{target}' - [bold red]FALLITO[/bold red] ({dur}s)")

                step_results.append({
                    "step_index": i, "type": stype, "target": target, "passed": step_passed,
                    "duration_seconds": dur, "screenshot": shot_path,
                    "tapped_screenshot": shot_path.replace(".png", "_tapped.png"), "notes": step_notes
                })

            assertion = scenario.get("assertion", {})
            ast_passed, ast_reason = True, "No final assertion defined."
            if assertion:
                desc = assertion.get("description", "")
                with StatusSpinner(f"🔍 Verifica asserzione finale visiva: '{desc}'..."):
                    final_shot = str(self.screenshots_dir / "final_assertion_screen.png")
                    adb.CaptureScreenBuffer(final_shot)
                    res = vision.VerifyScreenAssertion(final_shot, desc)
                    ast_passed = bool(res.get("pass"))
                    ast_reason = str(res.get("reason"))
                    if not ast_passed:
                        overall_passed = False

            tot_dur = round(time.time() - start_t, 2)
            log_file = GetLogFilePath()
            status_str = "[bold green]✅ SUITE PASSED[/bold green]" if overall_passed else "[bold red]❌ SUITE FAILED[/bold red]"
            console.print(f"\n{status_str} | Tempo totale: [bold]{tot_dur}s[/bold] | Log: [dim]{log_file}[/dim]\n")

            logger.info(f"Scenario finished: passed={overall_passed}, duration={tot_dur}s")

            return {
                "scenario_name": scenario_name, "passed": overall_passed,
                "total_duration_seconds": tot_dur, "steps": step_results,
                "final_assertion": {"passed": ast_passed, "reason": ast_reason}
            }

        finally:
            if self.server_mgr.process:
                self.server_mgr.StopLlamaServer()

    def run_scenario(self, scenario_path: str) -> Dict[str, Any]:
        return self.ExecuteTestScenario(scenario_path)
