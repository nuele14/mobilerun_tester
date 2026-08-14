"""
===============================================================================
[Design] PROVIDER MANAGER: Multi-Provider VLM Registry & Smart Local GGUF Scanner
1. Reads `server.models_dir` setting to locate local model folder.
2. Dynamically token-matches VLM .gguf models with their paired mmproj projectors.
3. Supports models like Muse-Glimmer, UI-TARS, Qwen2.5-VL, LLaVA, MiniCPM, etc.
4. Auto-prompts for selection if no model is configured or if `--select-model` is passed.
5. Auto-saves selected provider & server paths to default_config.yaml.
6. Fully localized via `q_test_arsenal.core.i18n`.
===============================================================================
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from q_test_arsenal.core.logger import GetLogger, console
from q_test_arsenal.core.i18n import I18n, t

# Supported VLM Providers Registry
VLM_PROVIDERS = {
    "local": {
        "name": "Local llama-server",
        "type": "local",
        "api_url": "http://127.0.0.1:8080/v1/chat/completions",
        "api_key_env": "",
        "default_model": "UI-TARS-7B-DPO-Q4_K_M.gguf",
        "models": ["UI-TARS-7B-DPO-Q4_K_M.gguf", "Qwen2-VL-7B-Instruct-Q4_K_M.gguf"],
        "requires_key": False,
        "is_local": True,
    },
    "openai": {
        "name": "OpenAI Cloud Vision",
        "type": "openai",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        "requires_key": True,
        "is_local": False,
    },
    "gemini": {
        "name": "Google Gemini Cloud Vision",
        "type": "gemini",
        "api_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "api_key_env": "GEMINI_API_KEY",
        "default_model": "gemini-1.5-flash",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
        "requires_key": True,
        "is_local": False,
    },
    "openrouter": {
        "name": "OpenRouter Multi-Model Cloud",
        "type": "openrouter",
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "qwen/qwen-2-vl-7b-instruct",
        "models": [
            "qwen/qwen-2-vl-7b-instruct",
            "google/gemini-flash-1.5",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
        ],
        "requires_key": True,
        "is_local": False,
    },
    "groq": {
        "name": "Groq Fast Vision Cloud",
        "type": "groq",
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "llama-3.2-11b-vision-preview",
        "models": ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"],
        "requires_key": True,
        "is_local": False,
    },
    "ollama": {
        "name": "Ollama Local Vision",
        "type": "ollama",
        "api_url": "http://127.0.0.1:11434/v1/chat/completions",
        "api_key_env": "",
        "default_model": "qwen2-vl",
        "models": ["qwen2-vl", "llava", "minicpm-v"],
        "requires_key": False,
        "is_local": True,
    },
}


class ProviderManager:
    """[Teacher] Manages VLM Provider API keys, local GGUF directory scanning, and model selection."""

    @staticmethod
    def _ExtractTokens(filename: str) -> set:
        """Extract meaningful model name tokens for dynamic mmproj matching."""
        clean = re.sub(r'[_\.-]', ' ', filename.lower())
        clean = re.sub(r'\b(gguf|f16|fp16|q4|q5|q8|q2|k|m|s|l|instruct|dpo|mmproj|bge|rerank)\b', '', clean)
        return set(t for t in clean.split() if len(t) >= 3)

    @staticmethod
    def ScanLocalGgufModels(models_dir: str) -> List[Dict[str, Any]]:
        """
        [Function] Scans configured models_dir for all VLM .gguf models dynamically paired with their mmproj projector.
        Supports Muse-Glimmer, UI-TARS, Qwen2.5-VL, LLaVA, MiniCPM, and any custom VLM GGUF models.
        """
        if not models_dir:
            return []

        clean_dir = os.path.expanduser(models_dir)
        dir_path = Path(clean_dir)
        if not dir_path.exists() or not dir_path.is_dir():
            return []

        all_gguf = list(dir_path.glob("*.gguf"))
        projectors = [f for f in all_gguf if "mmproj" in f.name.lower()]
        models = [f for f in all_gguf if "mmproj" not in f.name.lower() and "bge" not in f.name.lower() and "rerank" not in f.name.lower()]

        if not projectors:
            return []

        res = []
        for m_path in sorted(models, key=lambda p: p.name.lower()):
            size_gb = m_path.stat().st_size / (1024 ** 3)
            m_tokens = ProviderManager._ExtractTokens(m_path.stem)

            matched_mmproj = None
            best_score = 0

            # Dynamic token overlap matching
            for p in projectors:
                p_tokens = ProviderManager._ExtractTokens(p.stem)
                overlap = len(m_tokens & p_tokens)
                if overlap > best_score:
                    best_score = overlap
                    matched_mmproj = p

            # If no token overlap match, check fallback if only 1 projector exists
            if not matched_mmproj and len(projectors) == 1:
                matched_mmproj = projectors[0]
                best_score = 1

            # Only include models that have a valid matched mmproj projector
            if not matched_mmproj:
                continue

            clean_models_dir = models_dir.rstrip("/")
            mmproj_rel_path = f"{clean_models_dir}/{matched_mmproj.name}"
            model_rel_path = f"{clean_models_dir}/{m_path.name}"

            res.append({
                "filename": m_path.name,
                "model_path": model_rel_path,
                "abs_model_path": str(m_path),
                "mmproj_filename": matched_mmproj.name,
                "mmproj_path": mmproj_rel_path,
                "abs_mmproj_path": str(matched_mmproj),
                "size_gb": size_gb,
                "display_name": f"{m_path.name} ({size_gb:.2f} GB)"
            })

        return res

    @staticmethod
    def GetConfiguredApiKey(provider_id: str, config: Dict[str, Any]) -> str:
        """[Function] Resolves API Key from config['credentials'] or OS environment."""
        p_info = VLM_PROVIDERS.get(provider_id, {})
        env_name = p_info.get("api_key_env", "")
        if not env_name:
            return ""

        credentials = config.get("credentials", {})
        key_val = credentials.get(env_name, "")
        if not key_val or key_val.startswith("sk-your") or key_val.startswith("AIzaSy-your"):
            key_val = os.environ.get(env_name, "")

        return str(key_val)

    @staticmethod
    def GetProviderConfig(config: Dict[str, Any]) -> Dict[str, Any]:
        """[Function] Builds complete runtime provider configuration dictionary."""
        I18n.set_language(config.get("language", "en"))
        p_cfg = config.get("provider", {})
        p_type = p_cfg.get("type", "local")

        p_info = VLM_PROVIDERS.get(p_type, VLM_PROVIDERS["local"])
        api_key = ProviderManager.GetConfiguredApiKey(p_type, config)

        api_url = p_cfg.get("api_url") or p_info.get("api_url")
        model_name = p_cfg.get("model_name") or p_info.get("default_model")

        if p_type == "local":
            server_cfg = config.get("server", {})
            host = server_cfg.get("host", "127.0.0.1")
            port = server_cfg.get("port", 8080)
            api_url = f"http://{host}:{port}/v1/chat/completions"

        return {
            "type": p_type,
            "name": p_info.get("name", "Unknown Provider"),
            "api_url": api_url,
            "api_key": api_key,
            "model_name": model_name,
            "is_local": p_info.get("is_local", True),
        }

    @staticmethod
    def NeedsModelSelection(config_path: str) -> bool:
        """
        [Function] Returns True if no valid provider or local model path has been configured yet,
        or if the configured local model GGUF file is missing.
        """
        p = Path(config_path)
        if not p.exists():
            return True

        try:
            with open(p, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            
            p_type = config.get("provider", {}).get("type")
            model_name = config.get("provider", {}).get("model_name")

            if not p_type or not model_name:
                return True

            if p_type == "local":
                m_path = config.get("server", {}).get("model_path", "")
                if not m_path or not Path(os.path.expanduser(m_path)).exists():
                    return True

            return False
        except Exception:
            return True

    @staticmethod
    def InteractiveSelectVisionModel(config_path: str) -> Dict[str, Any]:
        """
        [Function] Displays interactive selection menu (scans `server.models_dir` for local GGUF models paired with mmproj).
        Saves updated choice to default_config.yaml.
        """
        p = Path(config_path)
        config = {}
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        I18n.set_language(config.get("language", "en"))
        current_prov_cfg = ProviderManager.GetProviderConfig(config)
        current_model = current_prov_cfg["model_name"]
        models_dir = config.get("server", {}).get("models_dir", "~/.modelli_llm")

        console.print("\n[bold cyan]============================================================[/bold cyan]")
        console.print(f"[bold white]{t('model_select_title')}[/bold white]")
        console.print("[bold cyan]============================================================[/bold cyan]")

        console.print(
            f"\n[bold yellow]{t('model_select_warn')}[/bold yellow]\n"
        )

        console.print(
            f"📌 [bold green]{t('active_model')}[/bold green] "
            f"[bold white]{current_prov_cfg['name']}[/bold white] -> [bold yellow]{current_model}[/bold yellow]\n"
        )

        local_ggufs = ProviderManager.ScanLocalGgufModels(models_dir)

        menu_items = []

        # Option 0: Keep current if valid
        keep_label = t("keep_active", name=current_prov_cfg['name'], model=current_model)
        menu_items.append({"id": "0", "type": "keep", "label": keep_label})

        idx = 1
        # Section 1: Discovered Local GGUF Models with Paired mmproj
        if local_ggufs:
            console.print(f"[bold white]{t('local_models_found', dir=models_dir)}[/bold white]")
            for lm in local_ggufs:
                label = f"Local GGUF: [bold yellow]{lm['filename']}[/bold yellow] ({lm['size_gb']:.2f} GB) [dim]-> mmproj: {lm['mmproj_filename']}[/dim]"
                menu_items.append({"id": str(idx), "type": "local_gguf", "data": lm, "label": label})
                console.print(f"  [bold cyan][{idx}][/bold cyan] {label}")
                idx += 1
            console.print("")
        else:
            console.print(f"[bold yellow]{t('no_local_models', dir=models_dir)}[/bold yellow]")
            console.print(f"[dim]{t('models_dir_note')}[/dim]\n")

        # Section 2: Cloud Providers
        console.print(f"[bold white]{t('cloud_providers')}[/bold white]")
        cloud_map = {}
        for p_id, p_info in VLM_PROVIDERS.items():
            if p_id == "local":
                continue # Handled by local GGUF scan above
            key = ProviderManager.GetConfiguredApiKey(p_id, config)
            has_key = bool(key)
            status_tag = f"[bold green]{t('tag_ready')}[/bold green]" if (p_info["is_local"] or has_key) else f"[dim red]{t('tag_key_required')}[/dim red]"
            label = f"{p_info['name']} {status_tag}"
            
            menu_items.append({"id": str(idx), "type": "provider", "provider_id": p_id, "label": label})
            cloud_map[str(idx)] = p_id
            console.print(f"  [bold cyan][{idx}][/bold cyan] {label}")
            idx += 1

        console.print(f"  [bold cyan][K][/bold cyan] {t('option_new_key')}")

        user_choice = console.input(f"\n{t('prompt_select_option')} ").strip().lower()

        if not user_choice or user_choice == "0":
            console.print(f"{t('choice_kept')}\n")
            return current_prov_cfg

        if user_choice == "k":
            console.print("\n[bold white]Provider API Key Setup:[/bold white]")
            console.print("1. OPENAI_API_KEY\n2. GEMINI_API_KEY\n3. OPENROUTER_API_KEY\n4. GROQ_API_KEY")
            k_choice = console.input("Select provider (1-4): ").strip()
            k_map = {"1": "OPENAI_API_KEY", "2": "GEMINI_API_KEY", "3": "OPENROUTER_API_KEY", "4": "GROQ_API_KEY"}
            env_key = k_map.get(k_choice)
            if env_key:
                new_key = console.input(f"Enter API Key for {env_key}: ").strip()
                if new_key:
                    config.setdefault("credentials", {})[env_key] = new_key
                    with open(p, "w", encoding="utf-8") as f:
                        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                    console.print(t("key_saved", key=env_key, path=config_path))
            return ProviderManager.InteractiveSelectVisionModel(config_path)

        # Find chosen item
        selected_item = next((item for item in menu_items if item["id"] == user_choice), None)

        if not selected_item:
            console.print(t("invalid_choice"))
            return current_prov_cfg

        # Case A: Selected a Local GGUF Model
        if selected_item["type"] == "local_gguf":
            lm = selected_item["data"]
            config["provider"] = {
                "type": "local",
                "model_name": lm["filename"],
                "api_url": "http://127.0.0.1:8080/v1/chat/completions"
            }
            config.setdefault("server", {})["model_path"] = lm["model_path"]
            config["server"]["mmproj_path"] = lm["mmproj_path"]

            with open(p, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            console.print(
                f"\n{t('local_selected', model=lm['filename'], mmproj=lm['mmproj_filename'])}\n"
            )
            return ProviderManager.GetProviderConfig(config)

        # Case B: Selected a Provider
        selected_p_id = selected_item.get("provider_id")
        selected_info = VLM_PROVIDERS[selected_p_id]

        if selected_info["requires_key"] and not ProviderManager.GetConfiguredApiKey(selected_p_id, config):
            console.print(t("missing_key_warn", provider=selected_info['name']))
            new_key = console.input(t("prompt_enter_key", env_name=selected_info['api_key_env'])).strip()
            if new_key:
                config.setdefault("credentials", {})[selected_info['api_key_env']] = new_key
            else:
                console.print(t("op_canceled"))
                return current_prov_cfg

        console.print(f"\n[bold white]{t('available_models', provider=selected_info['name'])}[/bold white]")
        for m_idx, m_name in enumerate(selected_info["models"], 1):
            console.print(f"  [{m_idx}] {m_name}")
        console.print(f"  [C] {t('custom_model_option')}")

        m_choice = console.input(f"{t('prompt_select_model')} ").strip().lower()
        if m_choice == "c":
            selected_model = console.input(f"{t('prompt_exact_model')} ").strip()
        elif m_choice.isdigit() and 1 <= int(m_choice) <= len(selected_info["models"]):
            selected_model = selected_info["models"][int(m_choice) - 1]
        else:
            selected_model = selected_info["default_model"]

        config["provider"] = {
            "type": selected_p_id,
            "model_name": selected_model,
            "api_url": selected_info["api_url"]
        }

        with open(p, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        console.print(
            f"\n{t('config_saved', provider=selected_info['name'], model=selected_model)}\n"
        )

        return ProviderManager.GetProviderConfig(config)
