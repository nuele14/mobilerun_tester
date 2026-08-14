"""
===============================================================================
[Design] I18N ENGINE: Internationalization & Dual-Language Support (English/Italian)
1. English ("en") is the default primary language for all CLI outputs and logs.
2. Configurable via `language: "en"` or `language: "it"` in default_config.yaml.
3. Provides simple `t(key, **kwargs)` lookup helper.
===============================================================================
"""

from typing import Dict, Any

DEFAULT_LANGUAGE = "en"

MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        # System & CLI Header
        "cli_title": "Q - TEST ARSENAL",
        "cli_subtitle": "Mobile E2E Visual Testing Framework",
        "sys_info_header": "Q - TEST ARSENAL SYSTEM INFORMATION",
        "ver_info": "  • Framework Version : {version} ({name})",
        "release_date": "  • Release Date      : {date}",
        "author": "  • Author            : {author}",
        "license": "  • License           : {license}",
        "copyright": "  • Copyright         : {copyright}",

        # Model Selection Menu
        "model_select_title": "INTERACTIVE VISION MODEL (VLM) SELECTION",
        "model_select_warn": "[ATTENTION] The selected model MUST support Multimodal/Vision features (image input) for screenshot grounding.",
        "active_model": "Active Model:",
        "local_models_found": "Local GGUF VLM Models (.gguf + mmproj) in '{dir}':",
        "no_local_models": "[WARN] No local VLM model with paired .mmproj projector found in '{dir}'.",
        "models_dir_note": "  Note: Set 'server.models_dir' in default_config.yaml to specify local GGUF model path.",
        "cloud_providers": "Cloud VLM Providers & Local Daemons:",
        "keep_active": "Keep current ({name} - {model})",
        "tag_ready": "[READY]",
        "tag_key_required": "[API KEY REQUIRED]",
        "option_new_key": "Configure / Enter a new Provider API Key",
        "prompt_select_option": "Select an option [default=0]:",
        "choice_kept": "✓ Current configuration maintained.",
        "invalid_choice": "[WARN] Invalid selection. Current configuration maintained.",
        "key_saved": "[SUCCESS] API Key {key} successfully saved to {path}.",
        "local_selected": "[SUCCESS] Local Model Selected: {model} | Projector: {mmproj}",
        "config_saved": "[SUCCESS] Configuration Updated: Provider {provider} | Model: {model}",
        "missing_key_warn": "[WARN] Missing API Key for {provider}.",
        "prompt_enter_key": "Enter API Key ({env_name}):",
        "op_canceled": "[CANCELED] Operation canceled. Previous configuration maintained.",
        "available_models": "Available Vision models for {provider}:",
        "custom_model_option": "Custom Model Name",
        "prompt_select_model": "Select model [default=1]:",
        "prompt_exact_model": "Enter exact Vision model name:",

        # Pre-flight Variable Validation
        "missing_vars_title": "[WARNING] MISSING ENVIRONMENT VARIABLES:",
        "missing_vars_sub": "The following variables were not found in scenarios/env.yaml or system environment:",
        "strict_abort": "[ERROR] Execution aborted due to strict_missing_env_vars mode.",
        "prompt_continue": "Continue scenario execution anyway?",
        "aborted_by_user": "[CANCELED] Execution canceled by user.",

        # Runner & Test Execution
        "starting_scenario": "Starting test scenario: '{name}' ({path})",
        "scenario_label": "Scenario:",
        "macro_fastpath_active": "[MACRO] Hybrid Execution Active: Fast-path enabled with automatic VLM fallback.",
        "macro_not_found": "[INFO] Macro file not found: Full VLM execution in progress.",
        "step_exec": "Step {index}/{total}: {type} -> {target}",
        "step_passed": "  ✓ Step passed in {time:.2f}s",
        "step_failed": "  ✗ Step failed: {error}",
        "step_retrying": "  [RETRY] Step failed (attempt {attempt}/{max}). Retrying in {pause}s...",
        "final_assertion_checking": "Evaluating final visual assertion...",
        "final_assertion_passed": "[SUCCESS] VISUAL ASSERTION PASSED",
        "final_assertion_failed": "[FAIL] VISUAL ASSERTION FAILED",
        "scenario_passed": "[SUCCESS] SCENARIO COMPLETED SUCCESSFULLY",
        "scenario_failed": "[FAIL] SCENARIO FAILED",

        # Diagnostics & Setup Validation
        "valid_title": "Q - TEST ARSENAL - SYSTEM DIAGNOSTICS & VALIDATION",
        "sec_deps": "1. PYTHON DEPENDENCIES CHECK",
        "sec_modules": "2. Q - TEST ARSENAL MODULES CHECK",
        "sec_config": "3. CONFIGURATION & SCENARIOS CHECK",
        "sec_adb": "4. ADB SYSTEM TOOLS CHECK",
        "sec_vlm": "5. VLM ENGINE & GGUF MODELS CHECK (llama-server)",
        "installed": "INSTALLED",
        "not_installed": "NOT INSTALLED",
        "ok": "OK",
        "config_found": "✓ Configuration file found: {path}",
        "scenarios_found": "✓ Found {count} test scenario(s) in 'scenarios/':",
        "no_scenarios": "[WARN] No .yaml scenario files found in 'scenarios/'.",
        "adb_found": "✓ ADB executable found in PATH: {path}",
        "device_connected": "✓ Connected Android Device/Emulator: {serial}",
        "llama_found": "✓ Executable llama-server found: {path}",
        "llama_not_listening": "[INFO] llama-server is not currently listening on http://127.0.0.1:8080/health (will auto-start during test execution).",
        "model_found": "✓ VLM Model found: {path} ({size:.2f} GB)",
        "mmproj_found": "✓ Multimodal Projector (mmproj) found: {path} ({size:.2f} MB)",
        "validation_success": "[SUCCESS] DIAGNOSTICS COMPLETED. System environment is fully operational.",
        "validation_failed": "[ERROR] DIAGNOSTICS INCOMPLETE OR FAILED. Review the items above.",
    },
    "it": {
        # System & CLI Header
        "cli_title": "Q - TEST ARSENAL",
        "cli_subtitle": "Framework di Testing Mobile E2E Visivo",
        "sys_info_header": "INFORMAZIONI DI SISTEMA Q - TEST ARSENAL",
        "ver_info": "  • Versione Framework : {version} ({name})",
        "release_date": "  • Data di Rilascio  : {date}",
        "author": "  • Autore             : {author}",
        "license": "  • Licenza            : {license}",
        "copyright": "  • Copyright          : {copyright}",

        # Model Selection Menu
        "model_select_title": "SELEZIONE INTERATTIVA MODELLO VISION (VLM)",
        "model_select_warn": "[ATTENZIONE] Il modello selezionato DEVE supportare funzionalità Multimodali / Vision (input di immagini) per eseguire il grounding visivo.",
        "active_model": "Modello Attivo Attualmente:",
        "local_models_found": "Modelli VLM Locali (.gguf + mmproj) trovati in '{dir}':",
        "no_local_models": "[AVVISO] Nessun modello VLM locale con proiettore .mmproj appaiato trovato in '{dir}'.",
        "models_dir_note": "  Nota: Imposta 'server.models_dir' in default_config.yaml per specificare il percorso dei modelli GGUF.",
        "cloud_providers": "Provider Cloud VLM & Local Daemon:",
        "keep_active": "Mantieni attuale ({name} - {model})",
        "tag_ready": "[PRONTO]",
        "tag_key_required": "[SERVE API KEY]",
        "option_new_key": "Inserisci / Configura una nuova Chiave API Provider",
        "prompt_select_option": "Seleziona un'opzione [default=0]:",
        "choice_kept": "✓ Mantenuta la configurazione attuale.",
        "invalid_choice": "[AVVISO] Scelta non valida. Mantenuta la configurazione attuale.",
        "key_saved": "[SUCCESS] Chiave API {key} salvata con successo in {path}.",
        "local_selected": "[SUCCESS] Modello Locale Selezionato: {model} | Proiettore: {mmproj}",
        "config_saved": "[SUCCESS] Configurazione Aggiornata: Provider {provider} | Modello: {model}",
        "missing_key_warn": "[AVVISO] Manca la chiave API per {provider}.",
        "prompt_enter_key": "Inserisci la chiave API ({env_name}):",
        "op_canceled": "[ANNULLATO] Operazione annullata. Mantenuta configurazione precedente.",
        "available_models": "Modelli Vision disponibili per {provider}:",
        "custom_model_option": "Nome Modello Personalizzato",
        "prompt_select_model": "Seleziona modello [default=1]:",
        "prompt_exact_model": "Inserisci il nome esatto del modello Vision:",

        # Pre-flight Variable Validation
        "missing_vars_title": "[ATTENZIONE] VARIABILI DI AMBIENTE MANCANTI:",
        "missing_vars_sub": "Le seguenti variabili non sono state trovate in scenarios/env.yaml o nell'ambiente:",
        "strict_abort": "[ERRORE] Esecuzione interrotta per modalità strict_missing_env_vars.",
        "prompt_continue": "Continuare comunque l'esecuzione dello scenario?",
        "aborted_by_user": "[ANNULLATO] Esecuzione annullata dall'utente.",

        # Runner & Test Execution
        "starting_scenario": "Avvio scenario di test: '{name}' ({path})",
        "scenario_label": "Scenario:",
        "macro_fastpath_active": "[MACRO] Esecuzione Ibrida Attiva: Fast-path abilitato con fallback automatico a VLM.",
        "macro_not_found": "[INFO] Macro non trovata: Esecuzione completa VLM in corso.",
        "step_exec": "Step {index}/{total}: {type} -> {target}",
        "step_passed": "  ✓ Step completato in {time:.2f}s",
        "step_failed": "  ✗ Step fallito: {error}",
        "step_retrying": "  [RETRY] Step fallito (tentativo {attempt}/{max}). Riprovo tra {pause}s...",
        "final_assertion_checking": "Valutazione dell'asserzione visiva finale...",
        "final_assertion_passed": "[SUCCESS] ASSERZIONE VISIVA SUPERATA",
        "final_assertion_failed": "[FAIL] ASSERZIONE VISIVA FALLITA",
        "scenario_passed": "[SUCCESS] SCENARIO COMPLETED SUCCESSFULLY",
        "scenario_failed": "[FAIL] SCENARIO FALLITO",

        # Diagnostics & Setup Validation
        "valid_title": "Q - TEST ARSENAL - DIAGNOSTICA E VALIDAZIONE SISTEMA",
        "sec_deps": "1. VERIFICA DIPENDENZE PYTHON",
        "sec_modules": "2. VERIFICA MODULI PROGETTO Q - TEST ARSENAL",
        "sec_config": "3. VERIFICA CONFIGURAZIONE E SCENARI",
        "sec_adb": "4. VERIFICA STRUMENTI DI SISTEMA (ADB)",
        "sec_vlm": "5. VERIFICA ENGINE VLM E MODELLI GGUF (llama-server)",
        "installed": "INSTALLATO",
        "not_installed": "NON INSTALLATO",
        "ok": "OK",
        "config_found": "✓ File di configurazione trovato: {path}",
        "scenarios_found": "✓ Trovati {count} scenari di test in 'scenarios/':",
        "no_scenarios": "[AVVISO] Nessun file .yaml trovato nella cartella 'scenarios/'.",
        "adb_found": "✓ ADB installato nel PATH: {path}",
        "device_connected": "✓ Dispositivo/Emulatore Android connesso: {serial}",
        "llama_found": "✓ Eseguibile llama-server trovato: {path}",
        "llama_not_listening": "[INFO] llama-server non è in ascolto su http://127.0.0.1:8080/health (verrà avviato automaticamente al lancio del test).",
        "model_found": "✓ Modello VLM trovato: {path} ({size:.2f} GB)",
        "mmproj_found": "✓ Proiettore Multimodale (mmproj) trovato: {path} ({size:.2f} MB)",
        "validation_success": "[SUCCESS] DIAGNOSTICA COMPLETATA. L'ambiente è pronto all'uso.",
        "validation_failed": "[ERRORE] DIAGNOSTICA INCOMPLETA O FALLITA. Verificare i punti sopra.",
    }
}


class I18n:
    """[Teacher] Lightweight Internationalization Engine for English and Italian UI outputs."""

    _language: str = DEFAULT_LANGUAGE

    @classmethod
    def set_language(cls, lang: str) -> None:
        """Sets active language ("en" or "it"). Defaults to "en"."""
        if lang and isinstance(lang, str) and lang.lower() in MESSAGES:
            cls._language = lang.lower()
        else:
            cls._language = DEFAULT_LANGUAGE

    @classmethod
    def get_language(cls) -> str:
        """Returns active language code."""
        return cls._language

    @classmethod
    def t(cls, key: str, **kwargs) -> str:
        """[Function] Resolves translated string for given key in active language."""
        lang_dict = MESSAGES.get(cls._language, MESSAGES[DEFAULT_LANGUAGE])
        text = lang_dict.get(key, MESSAGES[DEFAULT_LANGUAGE].get(key, key))
        return text.format(**kwargs) if kwargs else text


def t(key: str, **kwargs) -> str:
    """Shortcut helper for I18n.t(key, **kwargs)."""
    return I18n.t(key, **kwargs)
