#!/usr/bin/env python3
"""
===============================================================================
VALIDATORE COMPLETO DELL'AMBIENTE DI SVILUPPO E RUNTIME PER Q - TEST ARSENAL
===============================================================================
Verifica:
1. Dipendenze Python (PyYAML, Pillow, ImageHash, Rich, httpx).
2. Moduli interni del framework.
3. File di configurazione globale e scenari di test YAML.
4. Strumenti di sistema: ADB e dispositivi Android connessi.
5. Engine VLM: eseguibile llama-server e stato del server.
6. File dei modelli LLM/VLM (.gguf e mmproj.gguf).
===============================================================================
"""

import os
import sys
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Tuple, Dict, Any


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" 🔍 {title}")
    print("=" * 60)


def check_python_packages() -> bool:
    print_header("1. VERIFICA DIPENDENZE PYTHON")
    all_ok = True

    packages = [
        ("yaml", "PyYAML"),
        ("PIL", "Pillow"),
        ("imagehash", "ImageHash"),
        ("rich", "Rich (CLI UI & Spinners)"),
        ("httpx", "HTTPX"),
    ]

    for pkg_name, label in packages:
        try:
            __import__(pkg_name)
            print(f" ✓ {label:<30} [INSTALLATO]")
        except ImportError:
            print(f" ❌ {label:<30} [MANCANTE] -> Installa con: pip install {pkg_name}")
            all_ok = False

    return all_ok


def check_project_modules() -> bool:
    print_header("2. VERIFICA MODULI PROGETTO Q - TEST ARSENAL")
    all_ok = True

    modules = [
        ("q_test_arsenal.core.logger", "Core Logger & Spinners"),
        ("q_test_arsenal.core.adb_engine", "ADB Engine & Touch Primitive"),
        ("q_test_arsenal.core.vision_engine", "Vision Engine (Zoom Crop 2-Passes)"),
        ("q_test_arsenal.core.server_manager", "Llama Server Manager"),
        ("q_test_arsenal.core.scenario_parser", "Scenario Parser YAML"),
        ("q_test_arsenal.runner.test_runner", "Test Runner"),
        ("q_test_arsenal.runner.report_generator", "Report Generator HTML"),
        ("q_test_arsenal.cli.main", "CLI Entrypoint"),
    ]

    for mod_path, label in modules:
        try:
            __import__(mod_path)
            print(f" ✓ {label:<30} [OK]")
        except Exception as e:
            print(f" ❌ {label:<30} [ERRORE]: {e}")
            all_ok = False

    return all_ok


def check_config_and_scenarios() -> Tuple[bool, Dict[str, Any]]:
    print_header("3. VERIFICA CONFIGURAZIONE E SCENARI")
    all_ok = True
    config = {}

    config_path = Path("q_test_arsenal/config/default_config.yaml")
    if config_path.exists():
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            print(f" ✓ File di configurazione trovato: {config_path}")
        except Exception as e:
            print(f" ❌ Errore lettura {config_path}: {e}")
            all_ok = False
    else:
        print(f" ❌ File di configurazione NON trovato: {config_path}")
        all_ok = False

    scenarios_dir = Path("scenarios")
    if scenarios_dir.exists():
        scenario_files = list(scenarios_dir.glob("*.yaml")) + list(scenarios_dir.glob("*.yml"))
        if scenario_files:
            print(f" ✓ Trovati {len(scenario_files)} scenari di test nella cartella 'scenarios/':")
            for sf in scenario_files:
                print(f"   • {sf.name}")
        else:
            print(" ⚠️ Nessun file .yaml trovato nella cartella 'scenarios/'.")
    else:
        print(" ⚠️ Cartella 'scenarios/' non trovata.")

    return all_ok, config


def check_adb_and_devices() -> bool:
    print_header("4. VERIFICA STRUMENTI DI SISTEMA (ADB)")
    all_ok = True

    adb_bin = shutil.which("adb")
    if adb_bin:
        print(f" ✓ ADB installato nel PATH: {adb_bin}")
        try:
            res = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, check=True)
            lines = res.stdout.strip().split("\n")[1:]
            devices = [l.split("\t")[0] for l in lines if "\tdevice" in l]
            if devices:
                print(f" ✓ Dispositivo/Emulatore Android connesso: {', '.join(devices)}")
            else:
                print(" ⚠️ Nessun dispositivo o emulatore Android attualmente connesso via ADB.")
                print("   Assicurati che l'emulatore o lo smartphone sia collegato e che 'USB Debugging' sia attivo.")
        except Exception as e:
            print(f" ❌ Errore durante l'esecuzione di 'adb devices': {e}")
            all_ok = False
    else:
        print(" ❌ ADB (Android Debug Bridge) NON trovato nel PATH del sistema!")
        print("   Installa ADB:")
        print("   • macOS:   brew install android-platform-tools")
        print("   • Linux:   sudo apt install android-tools-adb")
        print("   • Windows: winget install Google.PlatformTools  oppure  scoop install adb")
        all_ok = False

    return all_ok


def check_vlm_engine_and_models(config: Dict[str, Any]) -> bool:
    print_header("5. VERIFICA ENGINE VLM E MODELLI GGUF (llama-server)")
    all_ok = True

    server_cfg = config.get("server", {})
    binary_name = server_cfg.get("binary", "llama-server")
    server_bin = shutil.which(binary_name) or shutil.which("llama-server")

    if server_bin:
        print(f" ✓ Eseguibile llama-server trovato: {server_bin}")
    else:
        print(f" ⚠️ Eseguibile '{binary_name}' non trovato nel PATH di sistema.")
        print("   Assicurati che llama.cpp sia installato (es. 'brew install llama.cpp' o scaricando i binari).")

    # Controlla se il server è già attivo in ascolto su HTTP
    host = server_cfg.get("host", "127.0.0.1")
    port = server_cfg.get("port", 8080)
    health_url = f"http://{host}:{port}/health"

    try:
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                print(f" ✓ llama-server già ATTIVO ed in ascolto su {health_url}")
    except Exception:
        print(f" ℹ️ llama-server non è in ascolto su {health_url} (verrà avviato automaticamente al lancio del test).")

    # Verification dei file modello .gguf e mmproj.gguf
    model_path_str = server_cfg.get("model_path", "~/.modelli_llm/UI-TARS-7B-DPO-Q4_K_M.gguf")
    mmproj_path_str = server_cfg.get("mmproj_path", "~/.modelli_llm/mmproj-UI-TARS-7B-f16.gguf")

    model_path = Path(os.path.expanduser(model_path_str))
    mmproj_path = Path(os.path.expanduser(mmproj_path_str))

    if model_path.exists():
        size_gb = round(model_path.stat().st_size / (1024 ** 3), 2)
        print(f" ✓ Modello VLM trovato: {model_path} ({size_gb} GB)")
    else:
        print(f" ❌ File Modello VLM NON trovato: {model_path}")
        print(f"   Percorso configurato in default_config.yaml: '{model_path_str}'")
        print("   Scarica il modello consigliato da HuggingFace:")
        print("   • UI-TARS-7B (Q4_K_M): https://huggingface.co/bytedance-research/UI-TARS-7B-DPO-GGUF")
        all_ok = False

    if mmproj_path.exists():
        size_mb = round(mmproj_path.stat().st_size / (1024 ** 2), 2)
        print(f" ✓ Proiettore Multimodale (mmproj) trovato: {mmproj_path} ({size_mb} MB)")
    else:
        print(f" ❌ File mmproj NON trovato: {mmproj_path}")
        print(f"   Percorso configurato in default_config.yaml: '{mmproj_path_str}'")
        all_ok = False

    return all_ok


def main():
    print("=" * 60)
    print(" 🚀 Q - TEST ARSENAL - VALIDAZIONE AMBIENTE E COMPONENTI")
    print("=" * 60)

    p_ok = check_python_packages()
    m_ok = check_project_modules()
    c_ok, config = check_config_and_scenarios()
    a_ok = check_adb_and_devices()
    v_ok = check_vlm_engine_and_models(config)

    print("\n" + "=" * 60)
    if p_ok and m_ok and c_ok and a_ok and v_ok:
        print(" 🎉 VALIDAZIONE COMPLETATA CON SUCCESSO! L'ambiente è pronto all'uso.")
        print("=" * 60)
        sys.exit(0)
    else:
        print(" ❌ VALIDAZIONE FALLITA O INCOMPLETA - Verificare i punti sopra.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()