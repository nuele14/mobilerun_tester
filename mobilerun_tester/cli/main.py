import argparse
import sys
from pathlib import Path
from mobilerun_tester.core.scenario_parser import ScenarioParser
from mobilerun_tester.runner.test_runner import TestRunner
from mobilerun_tester.runner.report_generator import ReportGenerator


def main():
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

    args = parser.parse_args()

    config_path = Path(args.config)
    config = ScenarioParser.load_config(str(config_path)) if config_path.exists() else {}
    runner = TestRunner(config)

    print("=" * 60)
    print(" 🚀 MOBILERUN TESTER - FRAMEWORK DI TESTING MOBILE (PRODUZIONE)")
    print("=" * 60)

    # CASO 1: Nessun parametro passato -> Esecuzione Batch di tutti i file in scenarios/
    if not args.scenario:
        scenarios_dirs = [Path("scenarios"), Path("mobilerun_tester/scenarios")]
        scenario_files = []
        for s_dir in scenarios_dirs:
            if s_dir.exists():
                scenario_files.extend(sorted(s_dir.glob("*.yaml")))
                scenario_files.extend(sorted(s_dir.glob("*.yml")))

        if not scenario_files:
            print("⚠️ Nessun file .yaml o .yml trovato nella cartella 'scenarios/'.")
            sys.exit(0)

        print(f"📦 Trovati {len(scenario_files)} scenari di test nella cartella 'scenarios/':")
        for f in scenario_files:
            print(f"   • {f}")
        print("-" * 60)

        suite_summaries = []
        all_passed = True

        for scenario_file in scenario_files:
            try:
                summary = runner.run_scenario(str(scenario_file))
                suite_summaries.append(summary)
                
                # Report HTML per il singolo scenario
                report_name = f"reports/{scenario_file.stem}_report.html"
                ReportGenerator.generate_html_report(summary, report_name)

                if not summary.get("passed", False):
                    all_passed = False
            except Exception as e:
                print(f"❌ Errore durante l'esecuzione dello scenario {scenario_file}: {e}")
                all_passed = False

        # Master Report HTML di riepilogo
        ReportGenerator.generate_master_suite_report(suite_summaries, "reports/master_report.html")

        if not all_passed:
            sys.exit(1)

    # CASO 2: Esecuzione di un singolo scenario specificato da riga di comando
    else:
        scenario_path = Path(args.scenario)
        if not scenario_path.exists():
            print(f"❌ File scenario {scenario_path} non trovato!")
            sys.exit(1)

        try:
            summary = runner.run_scenario(str(scenario_path))
            ReportGenerator.generate_html_report(summary, args.html_report)

            if not summary.get("passed", False):
                sys.exit(1)

        except Exception as e:
            print(f"❌ [MobileRun Failure] Errore durante l'esecuzione: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
