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
from q_test_arsenal import (
    __version__,
    __version_name__,
    __release_date__,
    __author__,
    __copyright__,
    __license__,
    Q_ASCII_ART,
)
from q_test_arsenal.core.scenario_parser import ScenarioParser
from q_test_arsenal.runner.test_runner import TestRunner
from q_test_arsenal.runner.report_generator import ReportGenerator
from q_test_arsenal.core.logger import GetLogger, console


def ExecuteCommandLineInterface():
    """
    [Function] Main CLI entrypoint parsing arguments and dispatching single or batch test suite runs.
    [Why] Zero-argument invocation defaults to running all test scenarios in 'scenarios/' directory.
    """
    parser = argparse.ArgumentParser(
        description="Q - Test Arsenal - Vision-Driven Automated Mobile Testing Framework"
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default=None,
        help="Percorso al file YAML dello scenario da eseguire. Se omesso, esegue tutti i test in 'scenarios/'"
    )
    parser.add_argument(
        "--version",
        "-v",
        action="store_true",
        help="Stampa la versione del framework ed i dettagli del sistema"
    )
    parser.add_argument(
        "--config",
        default="q_test_arsenal/config/default_config.yaml",
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
    parser.add_argument(
        "--select-model",
        "-m",
        action="store_true",
        help="Apre il menu interattivo per la selezione del modello e provider VLM (Local o Cloud)"
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Prosegue con gli step o sotto-scenari successivi anche se uno step o asserzione fallisce"
    )

    args = parser.parse_args()

    if args.version:
        console.print(f"[bold cyan]{Q_ASCII_ART}[/bold cyan]")
    config_path = Path(args.config)
    config = ScenarioParser.LoadConfigurationFile(str(config_path)) if config_path.exists() else {}

    from q_test_arsenal.core.i18n import I18n, t
    I18n.set_language(config.get("language", "en"))

    if args.version:
        console.print(f"[bold cyan]{Q_ASCII_ART}[/bold cyan]")
        console.print(f"[bold white]{t('sys_info_header')}[/bold white]")
        console.print("[dim]------------------------------------------------------------[/dim]")
        console.print(f"  • {t('ver_info', version=__version__, name=__version_name__)}")
        console.print(f"  • {t('release_date', date=__release_date__)}")
        console.print(f"  • {t('author', author=__author__)}")
        console.print(f"  • {t('license', license=__license__)}")
        console.print(f"  • {t('copyright', copyright=__copyright__)}")
        console.print("[dim]------------------------------------------------------------[/dim]\n")
        sys.exit(0)

    from q_test_arsenal.core.provider_manager import ProviderManager
    # Interactive Model Selection Menu if --select-model flag is passed OR if model is unselected/missing
    if args.select_model or ProviderManager.NeedsModelSelection(str(config_path)):
        ProviderManager.InteractiveSelectVisionModel(str(config_path))

    logger = GetLogger()
    logger.info("Initializing Q - Test Arsenal CLI")

    runner = TestRunner(config, config_path=str(config_path))

    console.print(f"\n[bold cyan]{t('cli_title')}[/bold cyan] [dim]- {t('cli_subtitle')}[/dim]")

    # =========================================================================
    # [Guide] MODE 1: BATCH SUITE EXECUTION (NO SCENARIO ARGUMENT PASSED)
    # =========================================================================
    if not args.scenario:
        scenarios_dirs = [Path("scenarios"), Path("q_test_arsenal/scenarios")]
        scenario_files = []
        for s_dir in scenarios_dirs:
            if s_dir.exists():
                scenario_files.extend(sorted(s_dir.glob("*.yaml")))
                scenario_files.extend(sorted(s_dir.glob("*.yml")))

        scenario_files = [f for f in scenario_files if f.name not in ("env.yaml", "env_example.yaml") and not f.name.startswith("env_")]

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
                summary = runner.ExecuteTestScenario(
                    str(scenario_file),
                    save_macro=args.save_macro,
                    use_macro=args.use_macro,
                    continue_on_failure=args.continue_on_failure
                )
                suite_summaries.append(summary)
                
                report_name = f"reports/{scenario_file.stem}_report.html"
                summary["report_file"] = f"{scenario_file.stem}_report.html"
                ReportGenerator.GenerateSingleScenarioHtmlReport(summary, report_name)

                if not summary.get("passed", False):
                    all_passed = False
                    if not args.continue_on_failure:
                        console.print(f"[bold red]🛑 Arresto esecuzione suite batch: scenario {scenario_file.name} fallito (continue_on_failure=false)[/bold red]")
                        break
            except Exception as e:
                logger.error(f"Error executing scenario {scenario_file}: {e}", exc_info=True)
                console.print(f"[bold red]❌ Errore durante l'esecuzione di {scenario_file}: {e}[/bold red]")
                all_passed = False
                if not args.continue_on_failure:
                    break

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
            suite_continue_on_fail = args.continue_on_failure or suite_manifest.get("continue_on_failure", False)

            console.print(f"\n[bold yellow]🏆 Esecuzione Suite Manifest:[/bold yellow] [bold white]{suite_name}[/bold white] [dim]({len(sub_scenarios)} scenari ordinati, continue_on_failure={suite_continue_on_fail})[/dim]")
            
            suite_summaries = []
            all_passed = True

            for item in sub_scenarios:
                sub_file = item.get("file")
                use_m = args.use_macro or item.get("use_macro", False)
                save_m = args.save_macro or item.get("save_macro", False)
                item_continue_on_fail = args.continue_on_failure or item.get("continue_on_failure", suite_continue_on_fail)

                sub_p = Path(sub_file)
                if not sub_p.exists():
                    sub_p = scenario_path.parent / sub_file

                if not sub_p.exists():
                    console.print(f"[bold red]❌ Errore: Sotto-scenario '{sub_file}' non trovato![/bold red]")
                    all_passed = False
                    if not item_continue_on_fail:
                        break
                    continue

                try:
                    summary = runner.ExecuteTestScenario(
                        str(sub_p),
                        save_macro=save_m,
                        use_macro=use_m,
                        continue_on_failure=item_continue_on_fail
                    )
                    suite_summaries.append(summary)

                    report_name = f"reports/{sub_p.stem}_report.html"
                    summary["report_file"] = f"{sub_p.stem}_report.html"
                    ReportGenerator.GenerateSingleScenarioHtmlReport(summary, report_name)

                    if not summary.get("passed", False):
                        all_passed = False
                        if not item_continue_on_fail:
                            console.print(f"[bold red]🛑 Arresto Suite Manifest: sotto-scenario '{sub_p.name}' fallito (continue_on_failure=false)[/bold red]")
                            break
                        else:
                            console.print(f"[dim]ℹ️ Sotto-scenario '{sub_p.name}' fallito ma continue_on_failure=true -> Proseguo col successivo...[/dim]")
                except Exception as e:
                    logger.error(f"Error executing sub-scenario {sub_p}: {e}", exc_info=True)
                    console.print(f"[bold red]❌ Errore durante l'esecuzione di {sub_p}: {e}[/bold red]")
                    all_passed = False
                    if not item_continue_on_fail:
                        break

            ReportGenerator.GenerateMasterSuiteHtmlReport(suite_summaries, "reports/master_report.html")

            if not all_passed:
                sys.exit(1)

        # Mode 2B: Single Scenario Execution
        else:
            try:
                summary = runner.ExecuteTestScenario(
                    str(scenario_path),
                    save_macro=args.save_macro,
                    use_macro=args.use_macro,
                    continue_on_failure=args.continue_on_failure
                )
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
