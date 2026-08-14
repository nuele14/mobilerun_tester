#!/usr/bin/env python3
"""
===============================================================================
Q - TEST ARSENAL ENVIRONMENT & RUNTIME DIAGNOSTIC VALIDATOR
===============================================================================
Verifies:
1. Python Dependencies (PyYAML, Pillow, ImageHash, Rich, httpx).
2. Internal Framework Modules.
3. Global Configuration File & YAML Test Scenarios.
4. System Tools: ADB & Connected Android Devices.
5. VLM Engine: llama-server executable & server health.
6. Local LLM/VLM Model Files (.gguf and mmproj.gguf).
===============================================================================
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import yaml
from pathlib import Path
from typing import Tuple, Dict, Any

from q_test_arsenal.core.i18n import I18n, t


def load_language_config() -> str:
    """Reads language setting from default_config.yaml."""
    cfg_path = Path("q_test_arsenal/config/default_config.yaml")
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
                return d.get("language", "en")
        except Exception:
            pass
    return "en"


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def check_python_packages() -> bool:
    print_header(t("sec_deps"))
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
            status = t("installed")
            print(f" ✓ {label:<30} [{status}]")
        except ImportError:
            status = t("not_installed")
            print(f" ❌ {label:<30} [{status}] -> Install via: pip install {pkg_name}")
            all_ok = False

    return all_ok


def check_project_modules() -> bool:
    print_header(t("sec_modules"))
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

    for mod_name, label in modules:
        try:
            __import__(mod_name)
            status = t("ok")
            print(f" ✓ {label:<35} [{status}]")
        except Exception as e:
            print(f" ❌ {label:<35} [ERROR] -> {e}")
            all_ok = False

    return all_ok


def check_config_and_scenarios() -> Tuple[bool, Dict[str, Any]]:
    print_header(t("sec_config"))
    all_ok = True
    config = {}

    config_path = Path("q_test_arsenal/config/default_config.yaml")
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            print(t("config_found", path=str(config_path)))
        except Exception as e:
            print(f" ❌ Error reading {config_path}: {e}")
            all_ok = False
    else:
        print(f" ❌ Configuration file NOT found: {config_path}")
        all_ok = False

    scenarios_dir = Path("scenarios")
    if scenarios_dir.exists():
        scenario_files = list(scenarios_dir.glob("*.yaml")) + list(scenarios_dir.glob("*.yml"))
        scenario_files = [sf for sf in scenario_files if sf.name not in ("env.yaml", "env_example.yaml") and not sf.name.startswith("env_")]
        if scenario_files:
            print(t("scenarios_found", count=len(scenario_files)))
            for sf in scenario_files:
                print(f"   • {sf.name}")
        else:
            print(t("no_scenarios"))
    else:
        print(" ⚠️ Folder 'scenarios/' not found.")

    return all_ok, config


def check_adb_and_devices() -> bool:
    print_header(t("sec_adb"))
    all_ok = True

    adb_path = shutil.which("adb")
    if adb_path:
        print(t("adb_found", path=adb_path))
    else:
        print(" ❌ Command 'adb' NOT found in system PATH!")
        print("   Install Android Platform Tools (e.g. brew install android-platform-tools)")
        return False

    try:
        res = subprocess.run([adb_path, "devices"], capture_output=True, text=True, check=True)
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip() and not line.startswith("List of devices")]
        devices = [line.split()[0] for line in lines if "device" in line]

        if devices:
            for dev in devices:
                print(t("device_connected", serial=dev))
        else:
            print(" ⚠️  No Android devices or emulators currently connected via ADB!")
            print("   Connect a physical smartphone via USB (with USB Debugging ON) or start an emulator.")
            all_ok = False
    except Exception as e:
        print(f" ❌ Error executing 'adb devices': {e}")
        all_ok = False

    return all_ok


def check_vlm_engine_and_models(config: Dict[str, Any]) -> bool:
    print_header(t("sec_vlm"))
    all_ok = True

    server_cfg = config.get("server", {})
    binary_name = server_cfg.get("binary", "llama-server")
    llama_path = shutil.which(binary_name) or shutil.which("llama-server")

    if llama_path:
        print(t("llama_found", path=llama_path))
    else:
        print(f" ⚠️ Executable '{binary_name}' NOT found in system PATH!")
        print("   Install llama.cpp (e.g. brew install llama.cpp) or specify the exact path in default_config.yaml.")
        all_ok = False

    host = server_cfg.get("host", "127.0.0.1")
    port = server_cfg.get("port", 8080)
    health_url = f"http://{host}:{port}/health"

    try:
        req = urllib.request.Request(health_url)
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                print(f" ✓ llama-server active and healthy on http://{host}:{port}")
    except Exception:
        print(t("llama_not_listening"))

    model_path_str = server_cfg.get("model_path", "~/.modelli_llm/UI-TARS-7B-DPO-Q4_K_M.gguf")
    mmproj_path_str = server_cfg.get("mmproj_path", "~/.modelli_llm/mmproj-UI-TARS-7B-f16.gguf")

    model_path = Path(os.path.expanduser(model_path_str))
    mmproj_path = Path(os.path.expanduser(mmproj_path_str))

    if model_path.exists():
        size_gb = round(model_path.stat().st_size / (1024 ** 3), 2)
        print(t("model_found", path=str(model_path), size=size_gb))
    else:
        print(f" ❌ VLM Model NOT found: {model_path}")
        print(f"   Configured path in default_config.yaml: '{model_path_str}'")
        all_ok = False

    if mmproj_path.exists():
        size_mb = round(mmproj_path.stat().st_size / (1024 ** 2), 2)
        print(t("mmproj_found", path=str(mmproj_path), size=size_mb))
    else:
        print(f" ❌ File mmproj NOT found: {mmproj_path}")
        print(f"   Configured path in default_config.yaml: '{mmproj_path_str}'")
        all_ok = False

    return all_ok


def main():
    lang = load_language_config()
    I18n.set_language(lang)

    print("=" * 60)
    print(f" {t('valid_title')}")
    print("=" * 60)

    p_ok = check_python_packages()
    m_ok = check_project_modules()
    c_ok, config = check_config_and_scenarios()
    a_ok = check_adb_and_devices()
    v_ok = check_vlm_engine_and_models(config)

    print("\n" + "=" * 60)
    if p_ok and m_ok and c_ok and a_ok and v_ok:
        print(f" {t('validation_success')}")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f" {t('validation_failed')}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()