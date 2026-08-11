"""
===============================================================================
[Design] ARCHITECTURE OVERVIEW: INTERACTIVE HTML REPORTING ENGINE
===============================================================================
This module converts test execution telemetry payloads into standalone HTML reports.
Key Design Requirements:
1. Zero External Dependencies: Reports use self-contained CSS tokens and inline SVG/images
   so reports render offline without CDN dependencies.
2. High Visual Quality: Dark mode palette, KPI summary cards, pass/fail status badges,
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
        
        steps_html = ""
        for step in summary.get("steps", []):
            step_passed = step.get("passed", False)
            step_badge = '<span class="step-badge pass">PASS</span>' if step_passed else '<span class="step-badge fail">FAIL</span>'
            
            shot = step.get("tapped_screenshot") or step.get("screenshot") or ""
            rel_shot = os.path.relpath(shot, out_file.parent) if shot and os.path.exists(shot) else ""
            
            img_html = f'<a href="{rel_shot}" target="_blank"><img src="{rel_shot}" class="step-img" alt="Step Screenshot"></a>' if rel_shot else '<div class="no-img">No Image</div>'

            steps_html += f"""
            <div class="step-card">
                <div class="step-header">
                    <h3>Step {step.get('step_index')}: {step.get('type')}</h3>
                    <div>{step_badge} <span class="time">{step.get('duration_seconds')}s</span></div>
                </div>
                <p><strong>Target:</strong> <code>{step.get('target')}</code></p>
                <p><strong>Note:</strong> {step.get('notes')}</p>
                <div class="img-container">
                    {img_html}
                </div>
            </div>
            """

        final_assertion = summary.get("final_assertion", {})
        final_passed = final_assertion.get("passed", False)
        final_badge = '<span class="step-badge pass">PASS</span>' if final_passed else '<span class="step-badge fail">FAIL</span>'

        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MobileRun Tester Report - {summary.get('scenario_name')}</title>
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
        h1 {{ margin: 0 0 8px 0; font-size: 26px; }}
        .meta {{ color: var(--text-muted); font-size: 14px; }}
        .badge {{ padding: 8px 16px; border-radius: 9999px; font-weight: 700; font-size: 16px; text-transform: uppercase; }}
        .badge.pass {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-pass); border: 1px solid var(--accent-pass); }}
        .badge.fail {{ background: rgba(239, 68, 68, 0.2); color: var(--accent-fail); border: 1px solid var(--accent-fail); }}
        
        .step-badge {{ padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; }}
        .step-badge.pass {{ background: var(--accent-pass); color: #000; }}
        .step-badge.fail {{ background: var(--accent-fail); color: #fff; }}
        .time {{ color: var(--text-muted); font-size: 13px; margin-left: 8px; }}

        .step-card {{ background: var(--card-bg); border-radius: 12px; padding: 18px; margin-bottom: 16px; border: 1px solid #334155; }}
        .step-header {{ display: flex; justify-content: space-between; align-items: center; }}
        .step-header h3 {{ margin: 0; font-size: 18px; color: #38bdf8; }}
        code {{ background: #090d16; padding: 2px 6px; border-radius: 4px; color: #f472b6; }}
        .img-container {{ margin-top: 12px; text-align: center; }}
        .step-img {{ max-width: 100%; max-height: 350px; border-radius: 8px; border: 1px solid #475569; transition: transform 0.2s; }}
        .step-img:hover {{ transform: scale(1.02); }}

        .assertion-card {{ background: #111827; border-left: 4px solid var(--accent-pass); border-radius: 8px; padding: 16px; margin-top: 24px; }}
        .assertion-card.fail {{ border-left-color: var(--accent-fail); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-card">
            <div>
                <h1>📱 MobileRun Test Suite</h1>
                <div class="meta">Scenario: <strong>{summary.get('scenario_name')}</strong> | Durata: <strong>{summary.get('total_duration_seconds')}s</strong></div>
            </div>
            <div>{status_badge}</div>
        </div>

        <h2>📋 Dettaglio Esecuzione Step</h2>
        {steps_html}

        <div class="assertion-card {'fail' if not final_passed else ''}">
            <h3>🔍 Asserzione Visiva Finale: {final_badge}</h3>
            <p><strong>Esito:</strong> {final_assertion.get('reason')}</p>
        </div>
    </div>
</body>
</html>
"""

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"📊 [MobileRun Report] Report HTML generato con successo in: {out_file.resolve()}")
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
            cards_html += f"""
            <div class="scenario-row {'fail' if not s_passed else ''}">
                <div>
                    <h3>{s.get('scenario_name')}</h3>
                    <div class="meta">Steps: {steps_count} | Durata: {s.get('total_duration_seconds')}s</div>
                </div>
                <div>{s_badge}</div>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MobileRun Test Suite - Master Report</title>
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
        
        .badge {{ padding: 8px 16px; border-radius: 9999px; font-weight: 700; text-transform: uppercase; }}
        .badge.pass {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-pass); border: 1px solid var(--accent-pass); }}
        .badge.fail {{ background: rgba(239, 68, 68, 0.2); color: var(--accent-fail); border: 1px solid var(--accent-fail); }}
        
        .step-badge {{ padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; }}
        .step-badge.pass {{ background: var(--accent-pass); color: #000; }}
        .step-badge.fail {{ background: var(--accent-fail); color: #fff; }}

        .scenario-row {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #334155;
        }}
        .scenario-row.fail {{ border-left: 4px solid var(--accent-fail); }}
        .scenario-row h3 {{ margin: 0 0 4px 0; font-size: 18px; color: #38bdf8; }}
        .meta {{ color: var(--text-muted); font-size: 13px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-card">
            <div>
                <h1>🏆 MobileRun Master Test Suite</h1>
                <div class="meta">Riepilogo Esecuzione Batch Scenari</div>
            </div>
            <div>{master_badge}</div>
        </div>

        <div class="kpi-container">
            <div class="kpi-card">
                <div class="meta">Totale Scenari</div>
                <div class="kpi-val">{total_scenarios}</div>
            </div>
            <div class="kpi-card">
                <div class="meta">Passati / Falliti</div>
                <div class="kpi-val pass">{passed_scenarios} <span style="font-size:16px; color:#94a3b8;">/</span> <span class="fail">{failed_scenarios}</span></div>
            </div>
            <div class="kpi-card">
                <div class="meta">Tempo Totale</div>
                <div class="kpi-val">{total_duration}s</div>
            </div>
        </div>

        <h2>📂 Scenari Eseguiti ({total_scenarios})</h2>
        {cards_html}
    </div>
</body>
</html>
"""

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"🏆 [Master Suite Report] Dashboard di riepilogo generata in: {out_file.resolve()}")
        return str(out_file.resolve())

    # Legacy Aliases
    @staticmethod
    def generate_html_report(summary: Dict[str, Any], output_path: str = "reports/latest_report.html"):
        return ReportGenerator.GenerateSingleScenarioHtmlReport(summary, output_path)

    @staticmethod
    def generate_master_suite_report(summaries: List[Dict[str, Any]], output_path: str = "reports/master_report.html"):
        return ReportGenerator.GenerateMasterSuiteHtmlReport(summaries, output_path)
