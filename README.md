<p align="center">
  <img src="docs/assets/Q_logo.jpeg" alt="Q - Test Arsenal Logo" width="360" style="border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
</p>

# Q - Test Arsenal

**Q - Test Arsenal** is an autonomous, end-to-end visual testing framework for mobile applications (**Flutter & Native Android**), powered by Vision-Language Models (**VLMs**) executed either locally (via `llama-server`) or through Cloud Providers (OpenAI, Google Gemini, OpenRouter, Groq).

The system performs two-stage visual grounding (**Coarse + Fine Bounding Box Zoom Crop**) and interacts directly with Android devices via ADB, eliminating the need for hardcoded element IDs or fragile XPaths.

---

### Ian Fleming Tribute

In the novels and films created by **Ian Fleming**, **Q** is the iconic *Quartermaster* of the secret branch: the brilliant mind who crafts extraordinary gadgets to safeguard agent 007 during mission-critical assignments.

**Q - Test Arsenal** is built with the same spirit: it quietly validates every screen and interaction flow before launch, delivering a reliable test arsenal before your code hits production.

**Fast, clean, accurate.**

---

## Table of Contents
1. [Required System Components](#required-system-components)
2. [Local VLM Models & Automatic Scanner](#local-vlm-models--automatic-scanner)
3. [Supported VLM Providers](#supported-vlm-providers)
4. [Quick Setup Wizard (`setup_wizard.py` / `q-setup`)](#quick-setup-wizard-setup_wizardpy--q-setup)
5. [Automated Diagnostic Check (`validate_setup.py`)](#automated-diagnostic-check-validate_setuppy)
6. [Framework Configuration (`default_config.yaml`)](#framework-configuration-default_configyaml)
7. [Application Credentials (`scenarios/env.yaml`)](#application-credentials-scenariosenvyaml)
8. [Pre-flight Variable Validation](#pre-flight-variable-validation)
9. [Interactive Model Selection (`--select-model` / `-m`)](#interactive-model-selection---select-model--m)
10. [Writing Test Scenarios (YAML)](#writing-test-scenarios-yaml)
11. [Suite Manifests & Error Control](#suite-manifests--error-control)
12. [Running Tests (CLI `q-test`)](#running-tests-cli-q-test)
13. [Telemetry, Debugging & Executive HTML Reports](#telemetry-debugging--executive-html-reports)
14. [Credits & Acknowledgments](#credits--acknowledgments)
15. [License](#license)

---

## Required System Components

Before launching **Q - Test Arsenal**, ensure the following system components are installed:

### 1. Android Debug Bridge (ADB)
Required for communicating with physical Android devices or emulators.

* **macOS**:
  ```bash
  brew install android-platform-tools
  ```
* **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install -y android-tools-adb
  ```
* **Windows**:
  ```powershell
  winget install Google.PlatformTools
  # Or via Scoop:
  scoop install adb
  ```

### 2. llama.cpp (`llama-server`) *(Optional for local inference)*
Required when running local VLM model inference with GPU acceleration.

* **macOS (Metal GPU acceleration)**:
  ```bash
  brew install llama.cpp
  ```
* **Linux / Windows**:
  Download prebuilt binaries from the official [llama.cpp GitHub Releases](https://github.com/ggerganov/llama.cpp/releases).

---

## Local VLM Models & Automatic Scanner

The framework includes an **automatic model directory scanner** (`server.models_dir`) with a **dynamic token matching algorithm** (`_ExtractTokens`) that pairs `.gguf` model files with their corresponding `.mmproj` multimodal projectors.

| VLM Model (GGUF) | Multimodal Projector (mmproj) | Description |
| :--- | :--- | :--- |
| `UI-TARS-7B-DPO-Q4_K_M.gguf` | `mmproj-UI-TARS-7B-f16.gguf` | Specialized GUI & mobile interface grounding model. |
| `Muse-Glimmer-30B-Q4_1.gguf` | `mmproj-Muse-Glimmer-30B-f16.gguf` | High-capacity vision model for complex mobile layouts. |
| `Qwen2.5-7B-Instruct-Q4_K_L.gguf` | `Qwen2.5-VL-7B-Instruct.mmproj.gguf` | General-purpose high-precision Vision-Language model. |

### Model Directory Setup
Set the model directory path in `default_config.yaml` (`server.models_dir`):
* **macOS / Linux**: `~/.modelli_llm/`
* **Windows**: `C:\modelli_llm\`

> [!NOTE]
> The scanner automatically filters out text-only LLMs that do not have a paired `.mmproj` projector.

---

## Supported VLM Providers

**Q - Test Arsenal** supports local models as well as leading Cloud VLM Providers using OpenAI-compatible endpoints:

1. **Local llama-server** (Local GPU inference via `llama-server`).
2. **OpenAI Cloud Vision** (`gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`).
3. **Google Gemini Cloud Vision** (`gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash-exp`).
4. **OpenRouter Multi-Model Cloud** (`qwen/qwen-2-vl-7b-instruct`, `google/gemini-flash-1.5`, `anthropic/claude-3.5-sonnet`).
5. **Groq Fast Vision Cloud** (`llama-3.2-11b-vision-preview`, `llama-3.2-90b-vision-preview`).
6. **Ollama Local Vision** (`qwen2-vl`, `llava`, `minicpm-v`).

---

## Quick Setup Wizard (`setup_wizard.py` / `q-setup`)

An interactive wizard configures the development environment:

```bash
# Launch interactive setup wizard:
python3 setup_wizard.py  # Or CLI alias: q-setup

# Activate virtual environment:
source .venv/bin/activate
```

---

## Automated Diagnostic Check (`validate_setup.py`)

Run the comprehensive diagnostic utility ([`validate_setup.py`](validate_setup.py)) to verify Python dependencies, ADB connectivity, VLM server availability, and model files:

```bash
python validate_setup.py
```

---

## Framework Configuration (`default_config.yaml`)

Global framework settings reside in:
👉 **[`q_test_arsenal/config/default_config.yaml`](q_test_arsenal/config/default_config.yaml)**

```yaml
# Language for CLI terminal output ("en" for English default, "it" for Italian)
language: "en"

provider:
  type: "local"
  model_name: "UI-TARS-7B-DPO-Q4_K_M.gguf"
  api_url: "http://127.0.0.1:8080/v1/chat/completions"

server:
  models_dir: "~/.modelli_llm"
  host: "127.0.0.1"
  port: 8080
  model_path: "~/.modelli_llm/UI-TARS-7B-DPO-Q4_K_M.gguf"
  mmproj_path: "~/.modelli_llm/mmproj-UI-TARS-7B-f16.gguf"
  binary: "llama-server"
  context_size: 4096
  gpu_layers: 99
  threads: 8
  flash_attn: true
  auto_start: true

device:
  serial: "R52M904J1QM"
  show_touches: true

runner:
  default_max_retries: 3
  debug_screenshots_dir: "reports/screenshots"
  reports_dir: "reports"
  check_missing_env_vars: true

credentials:
  OPENAI_API_KEY: ""
  GEMINI_API_KEY: ""
  OPENROUTER_API_KEY: ""
  GROQ_API_KEY: ""
```

---

## Application Credentials (`scenarios/env.yaml`)

Application credentials and variables are decoupled from system settings and reside in:
👉 **[`scenarios/env.yaml`](scenarios/env.yaml)**

```yaml
# scenarios/env.yaml
API_URL: "api.example.com"
SHOP_CODE: "demo"
USER_EMAIL: "test_user@example.com"
USER_PASSWORD: "secure_password_123"
```

To switch test environments or target user accounts, update or swap this single file.

---

## Pre-flight Variable Validation

Before executing steps on the mobile device, the runner performs a pre-flight validation check:
1. Extracts all `${VAR_NAME}` placeholders referenced in the scenario.
2. Verifies that each variable is defined in `scenarios/env.yaml` or `os.environ`.
3. If variables are missing, displays a terminal warning and prompts for confirmation before proceeding.

---

## Interactive Model Selection (`--select-model` / `-m`)

To switch VLM models or providers at any time:

```bash
q-test scenarios/login_flow.yaml --select-model
# Or short alias:
q-test -m
```

---

## Writing Test Scenarios (YAML)

Place test scenarios in the **[`scenarios/`](scenarios/)** folder:

```yaml
name: "Login Flow Scenario - Production Suite"
description: "Automated test scenario for API configuration and login verification"

steps:
  - type: "action_until"
    target: "Settings gear icon at top right"
    until_condition: "Dialog with title 'Insert API URL' is visible."
    max_retries: 3

  - type: "type_text"
    target: "API URL text field"
    value: "${API_URL}"

  - type: "type_text"
    target: "Shop Code text field"
    value: "${SHOP_CODE}"

  - type: "action"
    target: "'Save' button"

  - type: "type_text"
    target: "Username or Email input field"
    value: "${USER_EMAIL}"

  - type: "type_text"
    target: "Password input field"
    value: "${USER_PASSWORD}"

  - type: "wait"
    seconds: 2

  - type: "action"
    target: "Blue 'Login' button"

assertion:
  wait_seconds: 2
  description: "Login screen is dismissed and main app dashboard is visible."
```

---

## Running Tests (CLI `q-test`)

### 1. Batch Suite Run (All scenarios)
```bash
q-test
```

### 2. Specific Scenario Run
```bash
q-test scenarios/login_flow.yaml
```

### 3. Hybrid Macro Execution (`--save-macro` / `--use-macro`)
* **Record Macro**:
  ```bash
  q-test scenarios/login_flow.yaml --save-macro
  ```
* **Run Hybrid Fast-Path (~100ms with VLM Fallback)**:
  ```bash
  q-test scenarios/login_flow.yaml --use-macro
  ```

---

## Telemetry, Debugging & Executive HTML Reports

Execution summaries automatically generate standalone HTML reports in `reports/`:

1. **Executive Dashboard & Scenario Reports**: Standalone HTML dashboards with one-click navigation between master overview and scenario details.
2. **Latency Telemetry Breakdown**: Millisecond-accurate measurements for `ADB Capture`, `VLM Coarse`, `VLM Zoom Fine`, and `ADB Action`.
3. **Root Cause Diagnostic Analysis**: Failed steps include raw VLM JSON payloads, attempted coordinates, and target area zoom crops.

---

## Credits & Acknowledgments

This project is an evolution and extension of **[MobileRun (droidrun)](https://github.com/droidrun/mobilerun)**, created by **[Niels Schmidt](https://github.com/niels-schmidt)** ([DroidRun](https://droidrun.ai/)).

### Contribution of `mobilerun`:
* **Mobile Tooling Infrastructure**: Provided foundational ADB/device interaction, VLM endpoint dispatch, and macro telemetry architecture.
* **Q - Test Arsenal**: Developed by **Emanuele Coltro**, extending the original codebase into an autonomous visual E2E testing framework with YAML suite manifests, 2-stage **2-Pass Zoom Crop** grounding, executive HTML reporting, decoupled environment management (`scenarios/env.yaml`), pre-flight variable validation, i18n localization, and the `q-test` CLI.

Special thanks to Niels Schmidt and the DroidRun team.

---

## License

Distributed under the [MIT License](LICENSE).
