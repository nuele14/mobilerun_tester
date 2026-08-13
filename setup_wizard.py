#!/usr/bin/env python3
"""
===============================================================================
Q - TEST ARSENAL: WIZARD INTERATTIVO DI SETUP AUTOMATIZZATO
===============================================================================
Guida l'utente passo-passo nella configurazione completa dell'ambiente:
1. Rilevamento Architettura di Sistema (macOS / Linux / Windows, ARM64 / x86_64)
2. Gestione ed Inizializzazione dell'Ambiente Virtuale (.venv)
3. Installazione Dipendenze Python e Pacchetto q-test-arsenal (pip install -e .)
4. Audit ed Installazione Strumenti di Sistema (ADB & llama-server via Homebrew/System)
5. Downloader Interattivo Modelli VLM Consigliati (UI-TARS 7B GGUF + mmproj fp16)
6. Wizard Configurazione Unificata & Credenziali dell'Applicazione
7. Esecuzione Diagnostica Finale (validate_setup.py)
===============================================================================
"""

import os
import sys
import json
import time
import shutil
import platform
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional

# Visual Styling Helpers
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


def print_banner():
    print("\n" + "=" * 70)
    print(" 🚀 Q - TEST ARSENAL: WIZARD DI SETUP AUTOMATIZZATO E GUIDATO")
    print("=" * 70)
    print(" Benvenuto nel setup guidato! Questo script preparerà l'ambiente di")
    print(" sviluppo ed esecuzione in pochi semplici passaggi interattivi.\n")


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Helper for interactive yes/no questions with Rich fallback."""
    if HAS_RICH and console:
        return Confirm.ask(question, default=default)
    else:
        suffix = " [Y/n]: " if default else " [y/N]: "
        res = input(question + suffix).strip().lower()
        if not res:
            return default
        return res in ("y", "yes", "s", "si")


def prompt_input(question: str, default_val: str = "") -> str:
    """Helper for text inputs with Rich fallback."""
    if HAS_RICH and console:
        return Prompt.ask(question, default=default_val)
    else:
        default_str = f" [{default_val}]" if default_val else ""
        res = input(f"{question}{default_str}: ").strip()
        return res if res else default_val


def print_section(title: str):
    print("\n" + "-" * 70)
    print(f" 🛠️  {title}")
    print("-" * 70)


def step_1_system_detection() -> Dict[str, str]:
    print_section("FASE 1: RILEVAMENTO SISTEMA OPERATIVO ED ARCHITETTURA")
    os_name = sys.platform
    arch = platform.machine().lower()

    if os_name == "darwin":
        os_label = "macOS"
    elif os_name.startswith("linux"):
        os_label = "Linux"
    elif os_name in ("win32", "cygwin"):
        os_label = "Windows"
    else:
        os_label = os_name

    is_arm64 = arch in ("arm64", "aarch64")
    arch_label = "Apple Silicon (ARM64)" if (os_name == "darwin" and is_arm64) else arch.upper()

    print(f" ✓ Sistema Operativo : [bold white]{os_label}[/bold white]" if HAS_RICH else f" ✓ Sistema Operativo : {os_label}")
    print(f" ✓ Architettura CPU  : [bold white]{arch_label}[/bold white]" if HAS_RICH else f" ✓ Architettura CPU  : {arch_label}")
    print(f" ✓ Versione Python   : {platform.python_version()} ({sys.executable})")

    if sys.version_info < (3, 11):
        print("\n ❌ ERRORE: Q - Test Arsenal richiede Python 3.11 o superiore!")
        sys.exit(1)

    return {"os": os_name, "os_label": os_label, "arch": arch, "arch_label": arch_label, "is_arm64": is_arm64}


def step_2_virtualenv_setup():
    print_section("FASE 2: GESTIONE AMBIENTE VIRTUALE PYTHON (.venv)")
    in_venv = (sys.prefix != sys.base_prefix)
    venv_dir = Path(".venv")

    if in_venv:
        print(f" ✓ Ambiente virtuale attivo: {sys.prefix}")
        return

    if venv_dir.exists():
        print(f" ✓ Cartella '.venv' già presente in {venv_dir.resolve()}")
        return

    print(" ℹ️  Attualmente non sei all'interno di un ambiente virtuale attivo.")
    if prompt_yes_no("Vuoi creare l'ambiente virtuale '.venv' nella cartella corrente?", default=True):
        print(" ⏳ Creazione dell'ambiente virtuale '.venv' in corso...")
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print(" 🎉 Ambiente virtuale '.venv' creato con successo!")
        print("\n ⚠️ NOTA: Per attivare l'ambiente nella tua shell corrente esegui:")
        if sys.platform in ("win32", "cygwin"):
            print("   .\\.venv\\Scripts\\Activate.ps1")
        else:
            print("   source .venv/bin/activate\n")


def step_3_install_dependencies():
    print_section("FASE 3: INSTALLAZIONE DIPENDENZE E PACCHETTO")
    venv_python = Path(".venv/bin/python") if Path(".venv/bin/python").exists() else Path(sys.executable)
    venv_pip = Path(".venv/bin/pip") if Path(".venv/bin/pip").exists() else Path(sys.executable).parent / "pip"

    pip_cmd = str(venv_pip) if venv_pip.exists() else f"{sys.executable} -m pip"

    if prompt_yes_no("Installare/aggiornare le dipendenze Python ed il pacchetto 'q-test-arsenal' in modalità editable?", default=True):
        print(" ⏳ Installazione dipendenze via pip...")
        try:
            subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
        except Exception:
            print(" ℹ️  Nessun requirements.txt oppure installazione diretta tramite pyproject.toml...")

        print(" ⏳ Installazione del pacchetto 'q-test-arsenal' in modalità editable (pip install -e .)...")
        subprocess.run([pip_cmd, "install", "-e", "."], check=True)
        print(" 🎉 Dipendenze installate correttamente!")


def step_4_check_system_tools(sys_info: Dict[str, str]):
    print_section("FASE 4: VERIFICA ED INSTALLAZIONE STRUMENTI DI SISTEMA (ADB & llama-server)")

    # 1. Check ADB
    adb_path = shutil.which("adb")
    if adb_path:
        print(f" ✓ Android Debug Bridge (ADB) trovato: {adb_path}")
    else:
        print(" ⚠️  Android Debug Bridge (ADB) NON trovato nel PATH.")
        if sys_info["os"] == "darwin":
            if prompt_yes_no("Installare ADB tramite Homebrew (brew install android-platform-tools)?", default=True):
                subprocess.run(["brew", "install", "android-platform-tools"])
        elif sys_info["os"].startswith("linux"):
            print(" 👉 Per installare ADB su Ubuntu/Debian esegui: sudo apt install -y android-tools-adb")
        elif sys_info["os"] in ("win32", "cygwin"):
            print(" 👉 Per installare ADB su Windows esegui: winget install Google.PlatformTools")

    # 2. Check llama-server
    llama_path = shutil.which("llama-server") or shutil.which("/opt/homebrew/bin/llama-server")
    if llama_path:
        print(f" ✓ Llama VLM Engine (llama-server) trovato: {llama_path}")
    else:
        print(" ⚠️  Eseguibile 'llama-server' NON trovato nel PATH.")
        if sys_info["os"] == "darwin":
            if prompt_yes_no("Installare llama.cpp con accelerazione GPU Metal tramite Homebrew (brew install llama.cpp)?", default=True):
                subprocess.run(["brew", "install", "llama.cpp"])
        else:
            print(" 👉 Scarica l'eseguibile precompilato 'llama-server' da GitHub Releases:")
            print("    https://github.com/ggerganov/llama.cpp/releases")


def download_file_with_progress(url: str, dest_path: Path):
    """Downloads a file with resumable streaming progress indicator."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    initial_size = temp_path.stat().st_size if temp_path.exists() else 0

    req = urllib.request.Request(url)
    if initial_size > 0:
        req.add_header("Range", f"bytes={initial_size}-")

    try:
        response = urllib.request.urlopen(req)
        content_length = response.headers.get("Content-Length")
        total_size = int(content_length) + initial_size if content_length else None

        mode = "ab" if initial_size > 0 else "wb"

        print(f" 📥 Scaricamento: {dest_path.name}")
        print(f"    URL: {url}")

        start_time = time.time()
        downloaded = initial_size

        if HAS_RICH and console:
            with Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(dest_path.name, total=total_size, completed=initial_size)
                with open(temp_path, mode) as f:
                    while True:
                        buffer = response.read(1024 * 1024) # 1MB chunks
                        if not buffer:
                            break
                        f.write(buffer)
                        downloaded += len(buffer)
                        progress.update(task, completed=downloaded)
        else:
            with open(temp_path, mode) as f:
                last_print = time.time()
                while True:
                    buffer = response.read(1024 * 1024)
                    if not buffer:
                        break
                    f.write(buffer)
                    downloaded += len(buffer)
                    now = time.time()
                    if now - last_print > 1.0:
                        mb = downloaded / (1024 * 1024)
                        tot_mb = f"{total_size / (1024 * 1024):.1f} MB" if total_size else "?? MB"
                        speed = (downloaded - initial_size) / (now - start_time) / (1024 * 1024)
                        print(f"    Progress: {mb:.1f} / {tot_mb} ({speed:.2f} MB/s)")
                        last_print = now

        temp_path.rename(dest_path)
        print(f" 🎉 Scaricamento completato: {dest_path}")

    except Exception as e:
        print(f" ❌ Errore durante il download di {dest_path.name}: {e}")


def step_5_download_vlm_models():
    print_section("FASE 5: DOWNLOAD MODELLI VLM CONSIGLIATI (UI-TARS 7B GGUF)")

    models_dir = Path(os.path.expanduser("~/.modelli_llm"))
    models_dir.mkdir(parents=True, exist_ok=True)

    model_file = models_dir / "UI-TARS-7B-DPO.Q4_K_M.gguf"
    mmproj_file = models_dir / "UI-TARS-7B-DPO.mmproj-fp16.gguf"

    model_exists = model_file.exists() and model_file.stat().st_size > 1000000000
    mmproj_exists = mmproj_file.exists() and mmproj_file.stat().st_size > 100000000

    if model_exists and mmproj_exists:
        print(f" ✓ Modello VLM trovato: {model_file} ({model_file.stat().st_size / (1024**3):.2f} GB)")
        print(f" ✓ Proiettore mmproj trovato: {mmproj_file} ({mmproj_file.stat().st_size / (1024**2):.1f} MB)")
        return

    print(" Per eseguire il grounding visivo locale senza cloud, è richiesto il modello multimodale GGUF.")
    print(" Modello consigliato: UI-TARS 7B DPO (Q4_K_M) + Proiettore mmproj (~5.8 GB totale).\n")

    print(" 1. Scarica automaticamente UI-TARS 7B DPO da HuggingFace in ~/.modelli_llm/")
    print(" 2. Salta il download (userò modelli già presenti su disco o li scaricherò in seguito)")

    choice = prompt_input("Seleziona un'opzione", default_val="1")

    if choice == "1":
        model_url = "https://huggingface.co/mradermacher/UI-TARS-7B-DPO-GGUF/resolve/main/UI-TARS-7B-DPO.Q4_K_M.gguf"
        mmproj_url = "https://huggingface.co/mradermacher/UI-TARS-7B-DPO-GGUF/resolve/main/UI-TARS-7B-DPO.mmproj-fp16.gguf"

        if not model_exists:
            download_file_with_progress(model_url, model_file)
        else:
            print(f" ✓ Modello GGUF già presente: {model_file}")

        if not mmproj_exists:
            download_file_with_progress(mmproj_url, mmproj_file)
        else:
            print(f" ✓ Proiettore mmproj già presente: {mmproj_file}")


def step_6_configure_unified_setup():
    print_section("FASE 6: CONFIGURAZIONE UNIFICATA & CREDENZIALI DI TEST")

    config_path = Path("q_test_arsenal/config/default_config.yaml")
    if not config_path.exists():
        print(f" ⚠️ File di configurazione {config_path} non trovato. Verrà creato.")

    import yaml
    config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    credentials = config.get("credentials", {})
    device_cfg = config.get("device", {})

    if prompt_yes_no("Vuoi configurare interattivamente le credenziali ed il serial ADB?", default=True):
        current_serial = device_cfg.get("serial", "R52M904J1QM")
        new_serial = prompt_input("Serial dispositivo ADB (lascia vuoto per menu di selezione interattivo ad ogni avvio)", default_val=current_serial)

        curr_email = credentials.get("USER_EMAIL", "test_user@example.com")
        curr_pass = credentials.get("USER_PASSWORD", "secure_password_123")
        curr_api = credentials.get("API_URL", "betacc.planetps.it")
        curr_shop = credentials.get("SHOP_CODE", "dev2")

        new_email = prompt_input("USER_EMAIL per i test dell'applicazione", default_val=curr_email)
        new_pass = prompt_input("USER_PASSWORD per i test dell'applicazione", default_val=curr_pass)
        new_api = prompt_input("API_URL di backend", default_val=curr_api)
        new_shop = prompt_input("SHOP_CODE di configurazione", default_val=curr_shop)

        # Update config dictionary
        config.setdefault("device", {})["serial"] = new_serial
        config["credentials"] = {
            "USER_EMAIL": new_email,
            "USER_PASSWORD": new_pass,
            "API_URL": new_api,
            "SHOP_CODE": new_shop
        }

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        print(f" 🎉 Configurazione salvata in {config_path}!")


def step_7_run_validation():
    print_section("FASE 7: ESECUZIONE DIAGNOSTICA DI VALIDAZIONE FINALE")
    venv_python = Path(".venv/bin/python") if Path(".venv/bin/python").exists() else Path(sys.executable)
    py_cmd = str(venv_python)

    print(" ⏳ Avvio script di diagnostica validate_setup.py...\n")
    res = subprocess.run([py_cmd, "validate_setup.py"])
    if res.returncode == 0:
        print("\n" + "=" * 70)
        print(" 🎉 SETUP COMPLETATO CON SUCCESSO!")
        print("=" * 70)
        print(" Puoi ora lanciare i tuoi test mobile con il comando:")
        print("   q-test scenarios/login_flow.yaml --use-macro\n")
    else:
        print("\n ⚠️  Setup completato con avvertenze. Controlla i punti contrassegnati sopra.")


def main():
    print_banner()
    sys_info = step_1_system_detection()
    step_2_virtualenv_setup()
    step_3_install_dependencies()
    step_4_check_system_tools(sys_info)
    step_5_download_vlm_models()
    step_6_configure_unified_setup()
    step_7_run_validation()


if __name__ == "__main__":
    main()
