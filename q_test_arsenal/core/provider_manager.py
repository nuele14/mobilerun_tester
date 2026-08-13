"""
===============================================================================
[Design] PROVIDER MANAGER: Multi-Provider VLM Registry & Vision Model Picker
1. Manages Local (llama-server, Ollama) and Cloud (OpenAI, Gemini, OpenRouter, Groq) providers.
2. Resolves API Keys from unified setup config or process environment.
3. Displays Rich interactive terminal menu ONLY when `--select-model` is explicitly passed.
4. Auto-saves selected provider preference to default_config.yaml.
===============================================================================
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from q_test_arsenal.core.logger import GetLogger, console

# Supported VLM Providers Registry
VLM_PROVIDERS = {
    "local": {
        "name": "Local llama-server",
        "type": "local",
        "api_url": "http://127.0.0.1:8080/v1/chat/completions",
        "api_key_env": "",
        "default_model": "UI-TARS-7B-DPO.Q4_K_M.gguf",
        "models": ["UI-TARS-7B-DPO.Q4_K_M.gguf", "Qwen2-VL-7B-Instruct-Q4_K_M.gguf"],
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
    """[Teacher] Manages VLM Provider API keys and interactive Vision model selection."""

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
        p_cfg = config.get("provider", {})
        p_type = p_cfg.get("type", "local")

        p_info = VLM_PROVIDERS.get(p_type, VLM_PROVIDERS["local"])
        api_key = ProviderManager.GetConfiguredApiKey(p_type, config)

        api_url = p_cfg.get("api_url") or p_info.get("api_url")
        model_name = p_cfg.get("model_name") or p_info.get("default_model")

        # Fallback for local server config
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
    def InteractiveSelectVisionModel(config_path: str) -> Dict[str, Any]:
        """
        [Function] Displays interactive selection menu ONLY when --select-model flag is passed.
        Saves updated choice to default_config.yaml.
        """
        p = Path(config_path)
        config = {}
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        current_prov_cfg = ProviderManager.GetProviderConfig(config)
        current_type = current_prov_cfg["type"]
        current_model = current_prov_cfg["model_name"]

        console.print("\n[bold cyan]============================================================[/bold cyan]")
        console.print("[bold white]🎯 SELEZIONE INTERATTIVA MODELLO VISION (VLM)[/bold white]")
        console.print("[bold cyan]============================================================[/bold cyan]")

        console.print(
            "\n[bold yellow]👁️  ATTENZIONE:[/bold yellow] [italic white]Il modello selezionato DEVE supportare "
            "funzionalità Multimodali / Vision (input di immagini) per eseguire il grounding visivo degli screenshot![/italic white]\n"
        )

        console.print(
            f"📌 [bold green]Modello Attivo Attualmente:[/bold green] "
            f"[bold white]{current_prov_cfg['name']}[/bold white] -> [bold yellow]{current_model}[/bold yellow]\n"
        )

        # Build list of choices
        choices = []
        # Option 0: Keep current
        choices.append({"id": "0", "label": f"Mantieni attivo ({current_prov_cfg['name']} - {current_model})", "action": "keep"})

        # Build menu options for configured providers
        idx = 1
        provider_menu_map = {}

        for p_id, p_info in VLM_PROVIDERS.items():
            key = ProviderManager.GetConfiguredApiKey(p_id, config)
            has_key = bool(key)
            is_local = p_info["is_local"]

            status_tag = "[bold green][PRONTO][/bold green]" if (is_local or has_key) else "[dim red][SERVE API KEY][/dim red]"
            label = f"{p_info['name']} {status_tag}"
            
            choices.append({"id": str(idx), "label": label, "provider_id": p_id, "has_key": has_key, "is_local": is_local})
            provider_menu_map[str(idx)] = p_id
            idx += 1

        console.print("[bold white]Seleziona un Provider VLM:[/bold white]")
        for c in choices:
            console.print(f"  [bold cyan][{c['id']}][/bold cyan] {c['label']}")

        console.print("  [bold cyan][K][/bold cyan] Inserisci / Configura una nuova Chiave API Provider")

        user_choice = console.input("\n👉 Seleziona un'opzione [default=0]: ").strip().lower()

        if not user_choice or user_choice == "0":
            console.print(" ✓ Mantenuta la configurazione attuale.\n")
            return current_prov_cfg

        if user_choice == "k":
            console.print("\n[bold white]Configurazione Nuova Chiave API:[/bold white]")
            console.print("1. OPENAI_API_KEY\n2. GEMINI_API_KEY\n3. OPENROUTER_API_KEY\n4. GROQ_API_KEY")
            k_choice = console.input("Seleziona provider (1-4): ").strip()
            k_map = {"1": "OPENAI_API_KEY", "2": "GEMINI_API_KEY", "3": "OPENROUTER_API_KEY", "4": "GROQ_API_KEY"}
            env_key = k_map.get(k_choice)
            if env_key:
                new_key = console.input(f"Inserisci la chiave API per {env_key}: ").strip()
                if new_key:
                    config.setdefault("credentials", {})[env_key] = new_key
                    with open(p, "w", encoding="utf-8") as f:
                        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                    console.print(f" 🎉 Chiave API {env_key} salvata con successo in {config_path}!")
            return ProviderManager.InteractiveSelectVisionModel(config_path)

        selected_p_id = provider_menu_map.get(user_choice)
        if not selected_p_id:
            console.print(" ⚠️  Scelta non valida. Mantenuta la configurazione attuale.")
            return current_prov_cfg

        selected_info = VLM_PROVIDERS[selected_p_id]

        if selected_info["requires_key"] and not ProviderManager.GetConfiguredApiKey(selected_p_id, config):
            console.print(f"\n ⚠️  Manca la chiave API per {selected_info['name']}.")
            new_key = console.input(f" Inserisci la chiave API ({selected_info['api_key_env']}): ").strip()
            if new_key:
                config.setdefault("credentials", {})[selected_info['api_key_env']] = new_key
            else:
                console.print(" ❌ Operazione annullata. Mantenuta configurazione precedente.")
                return current_prov_cfg

        # Sub-menu for model selection
        console.print(f"\n[bold white]Modelli Vision disponibili per {selected_info['name']}:[/bold white]")
        for m_idx, m_name in enumerate(selected_info["models"], 1):
            console.print(f"  [{m_idx}] {m_name}")
        console.print(f"  [C] Nome Modello Personalizzato")

        m_choice = console.input(f"Seleziona modello [default=1]: ").strip().lower()
        if m_choice == "c":
            selected_model = console.input("Inserisci il nome esatto del modello Vision: ").strip()
        elif m_choice.isdigit() and 1 <= int(m_choice) <= len(selected_info["models"]):
            selected_model = selected_info["models"][int(m_choice) - 1]
        else:
            selected_model = selected_info["default_model"]

        # Update config file with choice
        config["provider"] = {
            "type": selected_p_id,
            "model_name": selected_model,
            "api_url": selected_info["api_url"]
        }

        with open(p, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        console.print(
            f"\n 🎉 [bold green]Configurazione Aggiornata e Salvata![/bold green] "
            f"Provider: [bold white]{selected_info['name']}[/bold white] | Modello: [bold yellow]{selected_model}[/bold yellow]\n"
        )

        return ProviderManager.GetProviderConfig(config)
