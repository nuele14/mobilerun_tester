"""
===============================================================================
[Design] ARCHITECTURE OVERVIEW: CLI ENTRYPOINT & BATCH DISPATCHER
===============================================================================
This module provides the Command Line Interface (CLI) entrypoint for MobileRun Tester.
CLI Dispatch Logic:
1. If no scenario path argument is provided, automatically scans 'scenarios/' directory
   for all *.yaml / *.yml files and triggers Batch Execution Mode.
2. If a specific scenario path is provided, runs single-scenario mode.
3. Generates individual step reports as well as Master Suite HTML Dashboard.
4. Returns exit code 0 on suite PASS and 1 on suite FAIL for CI/CD compatibility.

CLI Dispatch Diagram:
+-------------------+      +----------------------+      +----------------------+
| CLI Invocation    | ---> | Check Arguments      | ---> | Scenario Argument?   |
| (python -m ...)   |      | Parse --config & arg |      | Yes -> Single Run    |
+-------------------+      +----------------------+      +----------------------+
                                                                 | No
                                                                 v
                                                       +----------------------+
                                                       | Scan 'scenarios/'    |
                                                       | Run Batch Suite      |
                                                       | Master HTML Dashboard|
                                                       +----------------------+
===============================================================================
"""

import argparse
import sys
from pathlib import Path
from mobilerun_tester.core.scenario_parser import ScenarioParser
from mobilerun_tester.runner.test_runner import TestRunner
from mobilerun_tester.runner.report_generator import ReportGenerator
from mobilerun_tester.core.logger import GetLogger, console


def ExecuteCommandLineInterface():
    """
    [Function] Main CLI entrypoint parsing arguments and dispatching single or batch test suite runs.
    [Why] Zero-argument invocation defaults to running all test scenarios in 'scenarios/' directory.
    """
    logger = GetLogger()
    logger.info("Initializing MobileRun Tester CLI")

    parser = argparse.ArgumentParser(
        description="MobileRun Tester - Vision-Driven Automated Mobile Testing Framework"
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default=None,
        help="Percorso al file YAML dello scenario da eseguire. Se omesso, esegue tutti i test in 'scenarios/'"
    )
    parser.add_argument(
        "--config",
        default="mobilerun_tester/config/default_config.yaml",
        help="Percorso al file di configurazione globale"
    )
    parser.add_argument(
        "--html-report",
        default="reports/latest_report.html",
        help="Percorso di destinazione per il Report HTML visivo"
    )
    parser.add_argument(
        "--save-macro",
        action="store_true",
        help="Registra e salva automaticamente la sequenza di azioni in un file JSON di macro"
    )
    parser.add_argument(
        "--use-macro",
        action="store_true",
        help="Abilita l'esecutore ibrido Macro Fast-Path con fallback automatico al VLM"
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    config = ScenarioParser.LoadConfigurationFile(str(config_path)) if config_path.exists() else {}
    runner = TestRunner(config, config_path=str(config_path))

    console.print("\n[bold cyan]🚀 MOBILERUN TESTER[/bold cyan] [dim]- Framework di Testing Mobile[/dim]")

    # =========================================================================
    # [Guide] MODE 1: BATCH SUITE EXECUTION (NO SCENARIO ARGUMENT PASSED)
    # =========================================================================
    if not args.scenario:
        scenarios_dirs = [Path("scenarios"), Path("mobilerun_tester/scenarios")]
        scenario_files = []
        for s_dir in scenarios_dirs:
            if s_dir.exists():
                scenario_files.extend(sorted(s_dir.glob("*.yaml")))
                scenario_files.extend(sorted(s_dir.glob("*.yml")))

        if not scenario_files:
            console.print("[bold yellow]⚠️ Nessun file .yaml o .yml trovato nella cartella 'scenarios/'.[/bold yellow]")
            sys.exit(0)

        console.print(f"[dim]Trovati {len(scenario_files)} scenari di test in 'scenarios/':[/dim]")
        for f in scenario_files:
            console.print(f" [dim]• {f}[/dim]")

        suite_summaries = []
        all_passed = True

        for scenario_file in scenario_files:
            try:
                summary = runner.ExecuteTestScenario(str(scenario_file), save_macro=args.save_macro, use_macro=args.use_macro)
                suite_summaries.append(summary)
                
                report_name = f"reports/{scenario_file.stem}_report.html"
                summary["report_file"] = f"{scenario_file.stem}_report.html"
                ReportGenerator.GenerateSingleScenarioHtmlReport(summary, report_name)

                if not summary.get("passed", False):
                    all_passed = False
            except Exception as e:
                logger.error(f"Error executing scenario {scenario_file}: {e}", exc_info=True)
                console.print(f"[bold red]❌ Errore durante l'esecuzione di {scenario_file}: {e}[/bold red]")
                all_passed = False

        ReportGenerator.GenerateMasterSuiteHtmlReport(suite_summaries, "reports/master_report.html")

        if not all_passed:
            sys.exit(1)

    # =========================================================================
    # [Guide] MODE 2: SINGLE SCENARIO EXECUTION
    # =========================================================================
    else:
        scenario_path = Path(args.scenario)
        if not scenario_path.exists():
            console.print(f"[bold red]❌ File scenario {scenario_path} non trovato![/bold red]")
            sys.exit(1)

        # Mode 2A: Meta-Suite Manifest Execution
        if ScenarioParser.IsSuiteScenario(str(scenario_path)):
            suite_manifest = ScenarioParser.LoadSuiteManifest(str(scenario_path))
            suite_name = suite_manifest.get("name", scenario_path.stem)
            sub_scenarios = suite_manifest.get("scenarios", [])

            console.print(f"\n[bold yellow]🏆 Esecuzione Suite Manifest:[/bold yellow] [bold white]{suite_name}[/bold white] [dim]({len(sub_scenarios)} scenari ordinati)[/dim]")
            
            suite_summaries = []
            all_passed = True

            for item in sub_scenarios:
                sub_file = item.get("file")
                use_m = args.use_macro or item.get("use_macro", False)
                save_m = args.save_macro or item.get("save_macro", False)

                sub_p = Path(sub_file)
                if not sub_p.exists():
                    sub_p = scenario_path.parent / sub_file

                if not sub_p.exists():
                    console.print(f"[bold red]❌ Errore: Sotto-scenario '{sub_file}' non trovato![/bold red]")
                    all_passed = False
                    continue

                try:
                    summary = runner.ExecuteTestScenario(str(sub_p), save_macro=save_m, use_macro=use_m)
                    suite_summaries.append(summary)

                    report_name = f"reports/{sub_p.stem}_report.html"
                    summary["report_file"] = f"{sub_p.stem}_report.html"
                    ReportGenerator.GenerateSingleScenarioHtmlReport(summary, report_name)

                    if not summary.get("passed", False):
                        all_passed = False
                except Exception as e:
                    logger.error(f"Error executing sub-scenario {sub_p}: {e}", exc_info=True)
                    console.print(f"[bold red]❌ Errore durante l'esecuzione di {sub_p}: {e}[/bold red]")
                    all_passed = False

            ReportGenerator.GenerateMasterSuiteHtmlReport(suite_summaries, "reports/master_report.html")

            if not all_passed:
                sys.exit(1)

        # Mode 2B: Single Scenario Execution
        else:
            try:
                summary = runner.ExecuteTestScenario(str(scenario_path), save_macro=args.save_macro, use_macro=args.use_macro)
                ReportGenerator.GenerateSingleScenarioHtmlReport(summary, args.html_report)

                if not summary.get("passed", False):
                    sys.exit(1)

            except Exception as e:
                logger.error(f"Failure during scenario execution: {e}", exc_info=True)
                console.print(f"[bold red]❌ Errore durante l'esecuzione: {e}[/bold red]")
                sys.exit(1)


def main():
    ExecuteCommandLineInterface()


if __name__ == "__main__":
    main()
