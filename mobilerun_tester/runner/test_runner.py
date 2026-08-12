import time
from pathlib import Path
from typing import Dict, Any, List
from mobilerun_tester.core.adb_engine import ADBDevice
from mobilerun_tester.core.vision_engine import VisionEngine, DrawTapTargetHighlight
from mobilerun_tester.core.server_manager import LlamaServerManager
from mobilerun_tester.core.scenario_parser import ScenarioParser
from mobilerun_tester.core.macro_manager import MacroManager
from mobilerun_tester.core.logger import GetLogger, GetLogFilePath, StatusSpinner, console


class TestRunner:
    """[Teacher] Orchestrates test steps and gathers performance metrics."""

    def __init__(self, config: Dict[str, Any], config_path: str = "mobilerun_tester/config/default_config.yaml"):
        self.config = config
        self.config_path = config_path
        self.server_mgr = LlamaServerManager(config)
        self.reports_dir = Path(config.get("runner", {}).get("reports_dir", "reports"))
        self.screenshots_dir = Path(config.get("runner", {}).get("debug_screenshots_dir", "reports/screenshots"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def ExecuteTestScenario(self, scenario_path: str, save_macro: bool = False, use_macro: bool = False) -> Dict[str, Any]:
        """[Function] Runs complete scenario step loop returning telemetry dictionary."""
        logger = GetLogger()
        scenario = ScenarioParser.LoadTestScenario(scenario_path)
        scenario_name = scenario.get("name", "Unknown Scenario")
        
        logger.info(f"Starting test scenario: '{scenario_name}' ({scenario_path}) [save_macro={save_macro}, use_macro={use_macro}]")
        console.print(f"\n📋 [bold yellow]Scenario:[/bold yellow] [bold white]{scenario_name}[/bold white]")

        macro_mgr = MacroManager()
        loaded_macro = macro_mgr.LoadMacroSequence(scenario_path) if use_macro else None
        recorded_actions: List[Dict[str, Any]] = []

        if use_macro:
            if loaded_macro:
                console.print("⚡ [bold cyan]Esecuzione Ibrida Macro Attiva:[/bold cyan] Fast-path abilitato con fallback automatico a VLM.")
            else:
                console.print("⚠️ [bold yellow]Macro non trovata:[/bold yellow] Esecuzione completa VLM in corso.")

        with StatusSpinner("🦙 Inizializzazione server Llama VLM..."):
            if not self.server_mgr.StartLlamaServer():
                logger.error("Failed to start VLM server.")
                raise RuntimeError("Failed to start VLM server.")

        adb = ADBDevice(serial=self.config.get("device", {}).get("serial", ""), config_path=self.config_path)
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

                screencap_start = time.time()
                with StatusSpinner(f"📸 Cattura screenshot per Step {i}/{total_steps}..."):
                    adb.HideSoftKeyboard()
                    shot_path = str(self.screenshots_dir / f"step_{i}_{stype}.png")
                    adb.CaptureScreenBuffer(shot_path)
                screencap_ms = int((time.time() - screencap_start) * 1000)

                step_passed, step_notes = True, ""
                vlm_p1_ms, vlm_p2_ms, vlm_tot_ms, adb_ms = 0, 0, 0, 0
                attempt_traces = []

                current_hash = MacroManager.ComputeScreenHash(shot_path)
                macro_match_found = False
                macro_sim_score = 0.0
                saved_action_coords = None

                if use_macro and loaded_macro:
                    macro_actions = loaded_macro.get("actions", [])
                    if i <= len(macro_actions):
                        m_act = macro_actions[i - 1]
                        saved_hash = m_act.get("pre_state", {}).get("screen_hash", "")
                        macro_sim_score = MacroManager.CompareScreenHashes(saved_hash, current_hash)
                        if macro_sim_score >= 0.85:
                            macro_match_found = True
                            saved_action_coords = m_act.get("coordinates", {})
                            logger.info(f"⚡ [Macro Fast Path] Step {i}: Similarity {macro_sim_score*100:.1f}% >= 85%. Replay a ({saved_action_coords.get('x_pct')}%, {saved_action_coords.get('y_pct')}%)")
                        else:
                            logger.warning(f"⚠️ [Macro Divergence] Step {i}: Similarity {macro_sim_score*100:.1f}% < 85%. Fallback automatico a VLM.")
                            console.print(f" [yellow]⚠️ Step {i} Macro Divergence ({macro_sim_score*100:.0f}% match < 85%)[/yellow] -> Fallback VLM")
                    else:
                        logger.info(f"ℹ️ [Macro Skip] Step {i}: Step non presente nel file macro (totale salvati: {len(macro_actions)}).")
                        console.print(f" [dim]ℹ️ Step {i} non presente nel file macro (salvati: {len(macro_actions)})[/dim] -> Esecuzione VLM")

                if stype in ("action_until", "long_press_until"):
                    cond = step.get("until_condition", "")
                    is_fulfilled = False

                    # If not macro fast-path, check prior condition
                    if not macro_match_found:
                        with StatusSpinner(f"🔍 Verifica condizione visiva '{cond}'..."):
                            res_ast = vision.VerifyScreenAssertion(shot_path, cond)
                            is_fulfilled = res_ast.get("pass")
                            vlm_tot_ms += res_ast.get("vlm_ms", 0)

                    if is_fulfilled:
                        step_notes = f"Condition '{cond}' verified prior to tap."
                    else:
                        succ = False
                        for att in range(1, step.get("max_retries", 3) + 1):
                            if macro_match_found and saved_action_coords:
                                x = float(saved_action_coords.get("x_pct", 50.0))
                                y = float(saved_action_coords.get("y_pct", 50.0))
                                DrawTapTargetHighlight(shot_path, x, y, shot_path.replace(".png", "_tapped.png"), target_desc=f"[Macro Fast Path] {target}")
                                v_metrics = {}
                            else:
                                with StatusSpinner(f"🧠 Grounding VLM per '{target}' (Tentativo {att})..."):
                                    x, y, v_metrics = vision.PredictCoordinatesFast(shot_path, target, force_zoom=use_zoom)
                                    vlm_p1_ms += v_metrics.get("pass1_ms", 0)
                                    vlm_p2_ms += v_metrics.get("pass2_ms", 0)
                                    vlm_tot_ms += v_metrics.get("vlm_total_ms", 0)
                                    DrawTapTargetHighlight(shot_path, x, y, shot_path.replace(".png", "_tapped.png"), target_desc=target)

                            t_adb_start = time.time()
                            with StatusSpinner(f"⚡ Esecuzione azione ADB ({stype}) su ({x:.1f}%, {y:.1f}%)..."):
                                if stype == "long_press_until":
                                    adb.ExecuteLongPress(x, y, duration_ms=step.get("duration_ms", 2000))
                                else:
                                    adb.DispatchRobustTap(x, y, mode=tap_mode)
                                time.sleep(0.8)
                            adb_ms += int((time.time() - t_adb_start) * 1000)

                            after_shot = str(self.screenshots_dir / f"step_{i}_until_attempt_{att}.png")
                            adb.CaptureScreenBuffer(after_shot)
                            with StatusSpinner(f"🔍 Verifica esito tentata azione..."):
                                ast_check = vision.VerifyScreenAssertion(after_shot, cond)
                                vlm_tot_ms += ast_check.get("vlm_ms", 0)

                                attempt_traces.append({
                                    "attempt": att,
                                    "coarse_x": saved_action_coords.get("x_pct") if macro_match_found else v_metrics.get("coarse_x"),
                                    "coarse_y": saved_action_coords.get("y_pct") if macro_match_found else v_metrics.get("coarse_y"),
                                    "final_x": x,
                                    "final_y": y,
                                    "raw_response": "[Macro Replay]" if macro_match_found else v_metrics.get("raw_response"),
                                    "zoom_crop_screenshot": shot_path.replace(".png", "_tapped.png"),
                                    "assertion_reason": ast_check.get("reason"),
                                    "assertion_passed": ast_check.get("pass")
                                })

                                if ast_check.get("pass"):
                                    succ = True
                                    step_notes = f"⚡ Macro Fast-Path ({macro_sim_score*100:.0f}% match) met condition at attempt {att}." if macro_match_found else f"Condition met at attempt {att}."
                                    break
                            shot_path = after_shot

                        if not succ:
                            step_passed = overall_passed = False
                            step_notes = f"Condition '{cond}' unfulfilled after {step.get('max_retries', 3)} retries."

                elif stype == "action":
                    if macro_match_found and saved_action_coords:
                        x = float(saved_action_coords.get("x_pct", 50.0))
                        y = float(saved_action_coords.get("y_pct", 50.0))
                        DrawTapTargetHighlight(shot_path, x, y, shot_path.replace(".png", "_tapped.png"), target_desc=f"[Macro] {target}")
                        attempt_traces.append({
                            "attempt": 1,
                            "final_x": x,
                            "final_y": y,
                            "raw_response": f"[Macro Replay Match {macro_sim_score*100:.0f}%]",
                            "zoom_crop_screenshot": shot_path.replace(".png", "_tapped.png")
                        })
                    else:
                        with StatusSpinner(f"🧠 Grounding VLM & Calcolo coordinate per '{target}'..."):
                            x, y, v_metrics = vision.PredictCoordinatesFast(shot_path, target, force_zoom=use_zoom)
                            vlm_p1_ms = v_metrics.get("pass1_ms", 0)
                            vlm_p2_ms = v_metrics.get("pass2_ms", 0)
                            vlm_tot_ms = v_metrics.get("vlm_total_ms", 0)
                            DrawTapTargetHighlight(shot_path, x, y, shot_path.replace(".png", "_tapped.png"), target_desc=target)

                            attempt_traces.append({
                                "attempt": 1,
                                "coarse_x": v_metrics.get("coarse_x"),
                                "coarse_y": v_metrics.get("coarse_y"),
                                "final_x": x,
                                "final_y": y,
                                "raw_response": v_metrics.get("raw_response"),
                                "zoom_crop_screenshot": v_metrics.get("cropped_tapped_path")
                            })

                    t_adb_start = time.time()
                    with StatusSpinner(f"⚡ Esecuzione tap ADB su ({x:.1f}%, {y:.1f}%)..."):
                        adb.DispatchRobustTap(x, y, mode=tap_mode)
                        time.sleep(0.8)
                    adb_ms = int((time.time() - t_adb_start) * 1000)
                    step_notes = f"⚡ Macro Fast-Path ({macro_sim_score*100:.0f}% match) at ({x:.1f}%, {y:.1f}%)" if macro_match_found else f"Tap at ({x:.1f}%, {y:.1f}%)"

                elif stype == "type_text":
                    if macro_match_found and saved_action_coords:
                        x = float(saved_action_coords.get("x_pct", 50.0))
                        y = float(saved_action_coords.get("y_pct", 50.0))
                        DrawTapTargetHighlight(shot_path, x, y, shot_path.replace(".png", "_tapped.png"), target_desc=f"[Macro] {target}")
                        attempt_traces.append({
                            "attempt": 1,
                            "final_x": x,
                            "final_y": y,
                            "raw_response": f"[Macro Replay Match {macro_sim_score*100:.0f}%]",
                            "zoom_crop_screenshot": shot_path.replace(".png", "_tapped.png")
                        })
                    else:
                        with StatusSpinner(f"🧠 Grounding VLM per campo '{target}'..."):
                            x, y, v_metrics = vision.PredictCoordinatesFast(shot_path, target, force_zoom=use_zoom)
                            vlm_p1_ms = v_metrics.get("pass1_ms", 0)
                            vlm_p2_ms = v_metrics.get("pass2_ms", 0)
                            vlm_tot_ms = v_metrics.get("vlm_total_ms", 0)
                            DrawTapTargetHighlight(shot_path, x, y, shot_path.replace(".png", "_tapped.png"), target_desc=target)

                            attempt_traces.append({
                                "attempt": 1,
                                "coarse_x": v_metrics.get("coarse_x"),
                                "coarse_y": v_metrics.get("coarse_y"),
                                "final_x": x,
                                "final_y": y,
                                "raw_response": v_metrics.get("raw_response"),
                                "zoom_crop_screenshot": v_metrics.get("cropped_tapped_path")
                            })

                    t_adb_start = time.time()
                    with StatusSpinner(f"⌨️ Inserimento testo ADB: '{val}'..."):
                        adb.DispatchRobustTap(x, y, mode="tap")
                        time.sleep(0.2)
                        adb.InjectText(val)
                        time.sleep(0.3)
                        adb.HideSoftKeyboard()
                    adb_ms = int((time.time() - t_adb_start) * 1000)
                    step_notes = f"⚡ Macro Fast-Path ({macro_sim_score*100:.0f}% match) typed '{val}' at ({x:.1f}%, {y:.1f}%)" if macro_match_found else f"Typed '{val}' at ({x:.1f}%, {y:.1f}%)"

                elif stype == "wait":
                    wait_sec = float(step.get("seconds") or step.get("duration") or step.get("duration_seconds") or 1.0)
                    x, y = 50.0, 50.0
                    with StatusSpinner(f"⏳ Pausa di {wait_sec}s in corso..."):
                        time.sleep(wait_sec)
                    step_notes = f"Pausa di attesa di {wait_sec}s completata."

                dur = round(time.time() - t_start, 2)
                step_ms = int(dur * 1000)

                if save_macro and step_passed:
                    recorded_actions.append({
                        "step_index": i,
                        "action_type": stype,
                        "target_description": target or f"Wait {dur}s",
                        "value": str(dur) if stype == "wait" else val,
                        "coordinates": {
                            "x_pct": round(x, 2),
                            "y_pct": round(y, 2),
                            "px_x": int((x / 100.0) * adb.screen_width),
                            "px_y": int((y / 100.0) * adb.screen_height)
                        },
                        "pre_state": {
                            "screen_hash": current_hash,
                            "screen": {"width": adb.screen_width, "height": adb.screen_height}
                        },
                        "elapsed_since_previous_ms": step_ms
                    })

                logger.info(f"📊 [Step Telemetry {i}] Screencap={screencap_ms}ms | VLM Pass1={vlm_p1_ms}ms | VLM Pass2={vlm_p2_ms}ms | VLM Total={vlm_tot_ms}ms | ADB Input={adb_ms}ms | Total={step_ms}ms")

                if not step_passed:
                    logger.warning(f"❌ [ROOT CAUSE DEBUG TRACE] Step {i} ({stype}) failed for '{target}'. Note: {step_notes}")
                    for att_t in attempt_traces:
                        logger.warning(f"   • Attempt {att_t.get('attempt')}: Target=({att_t.get('final_x'):.1f}%, {att_t.get('final_y'):.1f}%) | AssertionReason='{att_t.get('assertion_reason')}' | RawVLM='{att_t.get('raw_response')}'")

                if step_passed:
                    console.print(f" [bold green]✔[/bold green] [bold]Step {i}/{total_steps}[/bold] {stype} | '{target or 'wait'}' ({dur}s) [dim](VLM: {vlm_tot_ms}ms, ADB: {adb_ms}ms)[/dim]")
                else:
                    console.print(f" [bold red]✖[/bold red] [bold]Step {i}/{total_steps}[/bold] {stype} | '{target or 'wait'}' - [bold red]FALLITO[/bold red] ({dur}s)")

                step_results.append({
                    "step_index": i, "type": stype, "target": target or f"Wait {dur}s", "passed": step_passed,
                    "duration_seconds": dur, "screenshot": shot_path,
                    "tapped_screenshot": shot_path.replace(".png", "_tapped.png"), "notes": step_notes,
                    "telemetry": {
                        "screencap_ms": screencap_ms,
                        "vlm_pass1_ms": vlm_p1_ms,
                        "vlm_pass2_ms": vlm_p2_ms,
                        "vlm_total_ms": vlm_tot_ms,
                        "adb_input_ms": adb_ms,
                        "total_step_ms": step_ms
                    },
                    "root_cause_trace": {
                        "target": target or f"Wait {dur}s",
                        "step_notes": step_notes,
                        "attempts": attempt_traces
                    } if (not step_passed or attempt_traces) else None
                })

            assertion = scenario.get("assertion", {})
            ast_passed, ast_reason, final_shot = True, "No final assertion defined.", ""
            if assertion:
                desc = assertion.get("description", "")
                wait_sec = float(assertion.get("wait_seconds") or assertion.get("wait") or 0.0)
                if wait_sec > 0:
                    console.print(f" ⏳ [bold cyan]Attesa di {wait_sec}s per completamento animazioni/transizioni UI...[/bold cyan]")
                    with StatusSpinner(f"⏳ Attesa di {wait_sec}s prima dell'asserzione finale visiva..."):
                        time.sleep(wait_sec)

                with StatusSpinner(f"🔍 Verifica asserzione finale visiva: '{desc}'..."):
                    final_shot = str(self.screenshots_dir / f"final_assertion_{Path(scenario_path).stem}.png")
                    adb.CaptureScreenBuffer(final_shot)
                    res = vision.VerifyScreenAssertion(final_shot, desc)
                    ast_passed = bool(res.get("pass"))
                    ast_reason = str(res.get("reason"))
                    if not ast_passed:
                        overall_passed = False

            tot_dur = round(time.time() - start_t, 2)

            # Scenario Summary Telemetry KPIs
            total_vlm_ms = sum(s.get("telemetry", {}).get("vlm_total_ms", 0) for s in step_results)
            total_adb_ms = sum(s.get("telemetry", {}).get("adb_input_ms", 0) for s in step_results)
            total_screencap_ms = sum(s.get("telemetry", {}).get("screencap_ms", 0) for s in step_results)
            avg_vlm_ms = int(total_vlm_ms / max(1, len(step_results)))
            avg_adb_ms = int(total_adb_ms / max(1, len(step_results)))

            log_file = GetLogFilePath()
            status_str = "[bold green]✅ SUITE PASSED[/bold green]" if overall_passed else "[bold red]❌ SUITE FAILED[/bold red]"
            console.print(f"\n{status_str} | Tempo totale: [bold]{tot_dur}s[/bold] (VLM Med: {avg_vlm_ms}ms, ADB Med: {avg_adb_ms}ms) | Log: [dim]{log_file}[/dim]\n")

            logger.info(f"Scenario finished: passed={overall_passed}, total_dur={tot_dur}s, total_vlm={total_vlm_ms}ms, total_adb={total_adb_ms}ms")

            if save_macro and overall_passed:
                macro_mgr.SaveMacroSequence(
                    scenario_path=scenario_path,
                    scenario_name=scenario_name,
                    actions=recorded_actions,
                    device_info={"width": adb.screen_width, "height": adb.screen_height, "serial": adb.serial}
                )

            return {
                "scenario_name": scenario_name, "passed": overall_passed,
                "total_duration_seconds": tot_dur, "steps": step_results,
                "final_assertion": {
                    "passed": ast_passed,
                    "reason": ast_reason,
                    "screenshot": final_shot
                },
                "telemetry_summary": {
                    "total_vlm_ms": total_vlm_ms,
                    "total_adb_ms": total_adb_ms,
                    "total_screencap_ms": total_screencap_ms,
                    "avg_vlm_ms": avg_vlm_ms,
                    "avg_adb_ms": avg_adb_ms
                }
            }

        finally:
            if self.server_mgr.process:
                self.server_mgr.StopLlamaServer()

    def run_scenario(self, scenario_path: str) -> Dict[str, Any]:
        return self.ExecuteTestScenario(scenario_path)
