"""
===============================================================================
[Design] ARCHITECTURE OVERVIEW: INTERACTIVE HTML REPORTING ENGINE
===============================================================================
This module converts test execution telemetry payloads into standalone HTML reports.
Key Design Requirements:
1. Zero External Dependencies: Reports use self-contained CSS tokens and inline SVG/images
   so reports render offline without CDN dependencies.
2. High Visual Quality: Executive dark palette, KPI summary cards, pass/fail status badges,
   and screenshot overlays with red touch target highlights.
3. Master Suite Reports: Aggregates multi-scenario batch runs into a single dashboard overview.

Data Flow Diagram:
+-------------------+      +----------------------+      +----------------------+
| Test Execution    | ---> | HTML Template Engine | ---> | Standalone HTML      |
| Telemetry Summary |      | Relative Image Links |      | Report File (.html)  |
+-------------------+      +----------------------+      +----------------------+
===============================================================================
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List


class ReportGenerator:
    """
    [Teacher] Generates interactive HTML report artifacts from scenario execution summaries.
    """

    # =========================================================================
    # [Guide] SECTION 1: SINGLE SCENARIO REPORT GENERATION
    # =========================================================================

    @staticmethod
    def GenerateSingleScenarioHtmlReport(summary: Dict[str, Any], output_path: str = "reports/latest_report.html") -> str:
        """
        [Function] Generates standalone HTML report for a single test scenario run.
        [Why] Uses relative paths for screenshots so report directory can be zipped and shared.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        passed = summary.get("passed", False)
        status_badge = '<span class="badge pass">PASSED</span>' if passed else '<span class="badge fail">FAILED</span>'
        
        telemetry_sum = summary.get("telemetry_summary", {})
        avg_vlm = telemetry_sum.get("avg_vlm_ms", 0)
        avg_adb = telemetry_sum.get("avg_adb_ms", 0)
        
        steps_html = ""
        for step in summary.get("steps", []):
            step_passed = step.get("passed", False)
            step_badge = '<span class="step-badge pass">PASS</span>' if step_passed else '<span class="step-badge fail">FAIL</span>'
            
            shot = step.get("tapped_screenshot") or step.get("screenshot") or ""
            rel_shot = os.path.relpath(shot, out_file.parent) if shot and os.path.exists(shot) else ""
            
            img_html = f'<a href="{rel_shot}" target="_blank"><img src="{rel_shot}" class="step-img" alt="Step Screenshot"></a>' if rel_shot else '<div class="no-img">No Image Available</div>'

            telem = step.get("telemetry", {})
            telem_html = f"""
            <div class="telemetry-bar">
                <span class="telemetry-pill">ADB Capture: <b>{telem.get('screencap_ms', 0)}ms</b></span>
                <span class="telemetry-pill">VLM Coarse: <b>{telem.get('vlm_pass1_ms', 0)}ms</b></span>
                <span class="telemetry-pill">VLM Zoom Fine: <b>{telem.get('vlm_pass2_ms', 0)}ms</b></span>
                <span class="telemetry-pill">ADB Action: <b>{telem.get('adb_input_ms', 0)}ms</b></span>
            </div>
            """ if telem else ""

            root_cause_html = ""
            rc_trace = step.get("root_cause_trace")
            if rc_trace and (not step_passed or len(rc_trace.get("attempts", [])) > 1):
                attempts_html = ""
                for att in rc_trace.get("attempts", []):
                    raw_resp = att.get("raw_response", "")
                    crop_shot = att.get("zoom_crop_screenshot", "")
                    rel_crop = os.path.relpath(crop_shot, out_file.parent) if crop_shot and os.path.exists(crop_shot) else ""
                    crop_img_tag = f'<div style="margin-top:8px;"><strong>Zoom Crop Target Area:</strong><br><img src="{rel_crop}" class="crop-thumb"></div>' if rel_crop else ''

                    attempts_html += f"""
                    <div class="attempt-box">
                        <div><strong>Attempt {att.get('attempt')}:</strong> Target: ({att.get('final_x', 0):.1f}%, {att.get('final_y', 0):.1f}%)</div>
                        {f'<div style="color:#f87171;"><strong>Failure Cause:</strong> {att.get("assertion_reason")}</div>' if att.get("assertion_reason") else ''}
                        <div class="raw-response-box">
                            <strong>Raw VLM Response (Debug Payload):</strong>
                            <pre><code>{raw_resp}</code></pre>
                        </div>
                        {crop_img_tag}
                    </div>
                    """

                root_cause_html = f"""
                <div class="root-cause-card">
                    <h4>Root Cause Diagnostic Analysis</h4>
                    <p><strong>Diagnostic Detail:</strong> {rc_trace.get('step_notes')}</p>
                    {attempts_html}
                </div>
                """

            steps_html += f"""
            <div class="step-card {'fail' if not step_passed else ''}">
                <div class="step-header">
                    <h3>Step {step.get('step_index')}: {step.get('type')}</h3>
                    <div>{step_badge} <span class="time">{step.get('duration_seconds')}s</span></div>
                </div>
                <p><strong>Target:</strong> <code>{step.get('target')}</code></p>
                <p><strong>Notes:</strong> {step.get('notes')}</p>
                {telem_html}
                {root_cause_html}
                <div class="img-container">
                    {img_html}
                </div>
            </div>
            """

        final_assertion = summary.get("final_assertion", {})
        final_passed = final_assertion.get("passed", False)
        final_badge = '<span class="step-badge pass">PASS</span>' if final_passed else '<span class="step-badge fail">FAIL</span>'
        final_shot = final_assertion.get("screenshot", "")
        rel_final_shot = os.path.relpath(final_shot, out_file.parent) if final_shot and os.path.exists(final_shot) else ""
        final_img_html = f'<div class="img-container" style="margin-top:14px;"><strong>Final Assertion Target Screenshot:</strong><br><a href="{rel_final_shot}" target="_blank"><img src="{rel_final_shot}" class="step-img" alt="Final Assertion Screenshot"></a></div>' if rel_final_shot else ''

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Q - Test Arsenal Report - {summary.get('scenario_name')}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --accent-pass: #10b981;
            --accent-fail: #ef4444;
            --accent-info: #38bdf8;
            --text-muted: #94a3b8;
        }}
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 24px;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header-card {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        h1 {{ margin: 0 0 8px 0; font-size: 26px; letter-spacing: -0.5px; }}
        .meta {{ color: var(--text-muted); font-size: 14px; }}
        .badge {{ padding: 8px 16px; border-radius: 9999px; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .badge.pass {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-pass); border: 1px solid var(--accent-pass); }}
        .badge.fail {{ background: rgba(239, 68, 68, 0.15); color: var(--accent-fail); border: 1px solid var(--accent-fail); }}
        
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            border: 1px solid #334155;
        }}
        .kpi-val {{ font-size: 24px; font-weight: 700; margin-top: 4px; color: var(--accent-info); }}

        .step-badge {{ padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; }}
        .step-badge.pass {{ background: var(--accent-pass); color: #000; }}
        .step-badge.fail {{ background: var(--accent-fail); color: #fff; }}
        .time {{ color: var(--text-muted); font-size: 13px; margin-left: 8px; }}

        .step-card {{ background: var(--card-bg); border-radius: 12px; padding: 18px; margin-bottom: 16px; border: 1px solid #334155; }}
        .step-header {{ display: flex; justify-content: space-between; align-items: center; }}
        .step-header h3 {{ margin: 0; font-size: 18px; color: #38bdf8; }}
        code {{ background: #090d16; padding: 2px 6px; border-radius: 4px; color: #f472b6; font-family: monospace; }}
        
        .telemetry-bar {{ display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }}
        .telemetry-pill {{ background: #090d16; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; font-size: 12px; color: var(--text-muted); }}
        .telemetry-pill b {{ color: var(--text-color); }}

        .img-container {{ margin-top: 12px; text-align: center; }}
        .step-img {{ max-width: 100%; max-height: 350px; border-radius: 8px; border: 1px solid #475569; transition: transform 0.2s; }}
        .step-img:hover {{ transform: scale(1.02); }}

        .step-card.fail {{ border-left: 4px solid var(--accent-fail); }}

        .root-cause-card {{ background: #1a0f1a; border: 1px solid #701a75; border-radius: 8px; padding: 14px; margin-top: 14px; color: #f5d0fe; }}
        .root-cause-card h4 {{ margin: 0 0 8px 0; color: #f472b6; font-size: 15px; display: flex; align-items: center; gap: 6px; }}
        .attempt-box {{ background: #0f172a; border-radius: 6px; padding: 10px; margin-top: 8px; font-size: 13px; border: 1px solid #334155; }}
        .raw-response-box {{ margin-top: 6px; background: #020617; border-radius: 4px; padding: 8px; font-family: monospace; font-size: 11px; overflow-x: auto; color: #a7f3d0; }}
        .raw-response-box pre {{ margin: 0; white-space: pre-wrap; }}
        .crop-thumb {{ max-height: 140px; border-radius: 6px; border: 1px solid #e11d48; margin-top: 6px; }}

        .nav-bar {{ margin-bottom: 16px; }}
        .back-link {{ color: #38bdf8; text-decoration: none; font-size: 14px; font-weight: 600; transition: color 0.2s; }}
        .back-link:hover {{ color: #7dd3fc; text-decoration: underline; }}

        .assertion-card {{ background: #111827; border-left: 4px solid var(--accent-pass); border-radius: 8px; padding: 16px; margin-top: 24px; }}
        .assertion-card.fail {{ border-left-color: var(--accent-fail); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="nav-bar">
            <a href="master_report.html" class="back-link">&larr; Return to Master Dashboard</a>
        </div>
        <div class="header-card">
            <div>
                <h1>Q - Test Arsenal</h1>
                <div class="meta">Scenario: <strong>{summary.get('scenario_name')}</strong></div>
            </div>
            <div>{status_badge}</div>
        </div>

        <div class="kpi-row">
            <div class="kpi-card">
                <div class="meta">Total Duration</div>
                <div class="kpi-val">{summary.get('total_duration_seconds')}s</div>
            </div>
            <div class="kpi-card">
                <div class="meta">Avg VLM Latency</div>
                <div class="kpi-val">{avg_vlm}ms</div>
            </div>
            <div class="kpi-card">
                <div class="meta">Avg ADB Latency</div>
                <div class="kpi-val">{avg_adb}ms</div>
            </div>
        </div>

        <h2>Step Execution Breakdown</h2>
        {steps_html}

        <div class="assertion-card {'fail' if not final_passed else ''}">
            <h3>Final Visual Assertion: {final_badge}</h3>
            <p><strong>Result:</strong> {final_assertion.get('reason')}</p>
            {final_img_html}
        </div>
    </div>
</body>
</html>
"""

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[Report Generator] HTML report generated successfully at: {out_file.resolve()}")
        return str(out_file.resolve())

    # =========================================================================
    # [Guide] SECTION 2: MASTER SUITE BATCH REPORT GENERATION
    # =========================================================================

    @staticmethod
    def GenerateMasterSuiteHtmlReport(summaries: List[Dict[str, Any]], output_path: str = "reports/master_report.html") -> str:
        """
        [Function] Generates master dashboard overview for batch test suite runs.
        [Why] Aggregates pass/fail KPIs and scenario summaries into a single HTML view.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        total_scenarios = len(summaries)
        passed_scenarios = sum(1 for s in summaries if s.get("passed", False))
        failed_scenarios = total_scenarios - passed_scenarios
        total_duration = round(sum(s.get("total_duration_seconds", 0) for s in summaries), 2)

        master_badge = '<span class="badge pass">SUITE PASSED</span>' if failed_scenarios == 0 else '<span class="badge fail">SUITE FAILED</span>'

        cards_html = ""
        for s in summaries:
            s_passed = s.get("passed", False)
            s_badge = '<span class="step-badge pass">PASSED</span>' if s_passed else '<span class="step-badge fail">FAILED</span>'
            
            steps_count = len(s.get("steps", []))
            report_file = s.get("report_file") or f"{s.get('scenario_name', '').lower().replace(' ', '_')}_report.html"
            
            cards_html += f"""
            <div class="scenario-row {'fail' if not s_passed else ''}">
                <div>
                    <h3>{s.get('scenario_name')}</h3>
                    <div class="meta">Steps: {steps_count} | Duration: {s.get('total_duration_seconds')}s</div>
                </div>
                <div class="scenario-actions">
                    {s_badge}
                    <a href="{report_file}" class="report-btn {'fail' if not s_passed else ''}">View Detailed Report &rarr;</a>
                </div>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Q - Test Arsenal - Master Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --accent-pass: #10b981;
            --accent-fail: #ef4444;
            --text-muted: #94a3b8;
        }}
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 24px;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header-card {{
            background: var(--card-bg);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}
        h1 {{ margin: 0 0 4px 0; font-size: 26px; letter-spacing: -0.5px; }}
        .meta {{ color: var(--text-muted); font-size: 14px; }}
        .kpi-container {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            border: 1px solid #334155;
        }}
        .kpi-val {{ font-size: 28px; font-weight: 700; margin-top: 4px; }}
        .kpi-val.pass {{ color: var(--accent-pass); }}
        .kpi-val.fail {{ color: var(--accent-fail); }}
        
        .badge {{ padding: 8px 16px; border-radius: 9999px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
        .badge.pass {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-pass); border: 1px solid var(--accent-pass); }}
        .badge.fail {{ background: rgba(239, 68, 68, 0.15); color: var(--accent-fail); border: 1px solid var(--accent-fail); }}
        
        .step-badge {{ padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; }}
        .step-badge.pass {{ background: var(--accent-pass); color: #000; }}
        .step-badge.fail {{ background: var(--accent-fail); color: #fff; }}

        .scenario-row {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #334155;
            transition: border-color 0.2s;
        }}
        .scenario-row:hover {{ border-color: #38bdf8; }}
        .scenario-row.fail {{ border-left: 4px solid var(--accent-fail); }}
        .scenario-row h3 {{ margin: 0 0 4px 0; font-size: 18px; color: #38bdf8; }}

        .scenario-actions {{ display: flex; align-items: center; gap: 14px; }}
        .report-btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: #0284c7;
            color: #ffffff;
            text-decoration: none;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            transition: background 0.2s, transform 0.1s;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
        }}
        .report-btn:hover {{ background: #0369a1; transform: translateY(-1px); }}
        .report-btn.fail {{ background: #dc2626; box-shadow: 0 4px 12px rgba(220, 38, 38, 0.25); }}
        .report-btn.fail:hover {{ background: #b91c1c; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-card">
            <div>
                <h1>Q - Test Arsenal Executive Dashboard</h1>
                <div class="meta">Batch Test Suite Execution Summary</div>
            </div>
            <div>{master_badge}</div>
        </div>

        <div class="kpi-container">
            <div class="kpi-card">
                <div class="meta">Total Scenarios</div>
                <div class="kpi-val">{total_scenarios}</div>
            </div>
            <div class="kpi-card">
                <div class="meta">Passed / Failed</div>
                <div class="kpi-val pass">{passed_scenarios} <span style="font-size:16px; color:#94a3b8;">/</span> <span class="fail">{failed_scenarios}</span></div>
            </div>
            <div class="kpi-card">
                <div class="meta">Total Duration</div>
                <div class="kpi-val">{total_duration}s</div>
            </div>
        </div>

        <h2>Executed Scenarios ({total_scenarios})</h2>
        {cards_html}
    </div>
</body>
</html>
"""

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[Report Generator] Master suite dashboard generated at: {out_file.resolve()}")
        return str(out_file.resolve())

    # Legacy Aliases
    @staticmethod
    def generate_html_report(summary: Dict[str, Any], output_path: str = "reports/latest_report.html"):
        return ReportGenerator.GenerateSingleScenarioHtmlReport(summary, output_path)

    @staticmethod
    def generate_master_suite_report(summaries: List[Dict[str, Any]], output_path: str = "reports/master_report.html"):
        return ReportGenerator.GenerateMasterSuiteHtmlReport(summaries, output_path)
