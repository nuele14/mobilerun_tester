<p align="center">
  <img src="docs/assets/Q_logo.jpeg" alt="Q - Test Arsenal Logo" width="360" style="border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
</p>

# 🚀 Q - Test Arsenal

**Q - Test Arsenal** è un framework autonomo di testing automatizzato E2E visivo per applicazioni mobile (**Flutter & Native Android**), basato su modelli Vision-Language (**VLM**) eseguiti sia completamente in locale (via `llama-server`) che tramite Provider Cloud (OpenAI, Gemini, OpenRouter, Groq).

Il sistema esegue un grounding visivo a due livelli (**Coarse + Fine Bounding Box Zoom Crop**) ed interagisce direttamente con il dispositivo Android via ADB, senza dipendere da servizi cloud esterni o ID di elemento hardcodati nel codice.

---

### 🕵️‍♂️ Perché "Q"? — Un tributo a Ian Fleming

Nei romanzi e nei film ideati da **Ian Fleming**, **Q** è l'iconico *Quartermaster* del laboratorio segreto: la mente geniale che non scende sul campo di battaglia al posto dell'agente 007, ma lavora nell'ombra per forgiargli i gadget ed i dispositivi straordinari capaci di salvarlo nelle missioni più impossibili.

**Q - Test Arsenal** nasce con lo stesso spirito artigianale e romantico: non sostituisce il lavoro dello sviluppatore, ma presidia silenziosamente ogni angolo dell'interfaccia mobile prima del lancio, testa visivamente ogni scenario e ti consegna l'arsenale perfetto prima che il tuo codice affronti la produzione.

**Veloce, essenziale, letale contro i bug.**

---

## 📋 Indice
1. [Componenti di Sistema Richiesti](#-componenti-di-sistema-richiesti)
2. [Modelli VLM Locali e Scansione Automatica](#-modelli-vlm-locali-e-scansione-automatica)
3. [Provider VLM Cloud e Locali Supportati](#-provider-vlm-cloud-e-locali-supportati)
4. [Quick Setup Guidato (`setup_wizard.py` / `q-setup`)](#-quick-setup-guidato-in-2-comandi)
5. [Validazione Automatica dell'Ambiente (`validate_setup.py`)](#-validazione-automatica-dellambiente)
6. [Configurazione del Framework (`default_config.yaml`)](#-configurazione-del-framework)
7. [Dati dell'Applicazione e Credenziali (`scenarios/env.yaml`)](#-dati-dellapplicazione-e-credenziali-scenariosenvyaml)
8. [Controllo Preventivo a Priori delle Variabili (Pre-flight Check)](#-controllo-preventivo-a-priori-delle-variabili-pre-flight-check)
9. [Selezione Interattiva Modello (`--select-model` / `-m`)](#-selezione-interattiva-modello---select-model--m)
10. [Creazione degli Scenari di Test YAML](#-creazione-degli-scenari-di-test-yaml)
11. [Suite Manifest & Gestione Errori](#-suite-manifest--gestione-errori-continue_on_failure)
12. [Esecuzione dei Test (CLI `q-test`)](#-esecuzione-dei-test-cli-q-test)
13. [Telemetria, Root Cause Debugging e Report HTML](#-telemetria-root-cause-debugging-e-report-html)
14. [Riconoscimenti e Crediti](#-riconoscimenti-e-crediti)
15. [Licenza](#-licenza)

---

## 🛠️ Componenti di Sistema Richiesti

Prima di avviare **Q - Test Arsenal**, assicurati che siano installati i seguenti componenti di sistema sul tuo computer:

### 1. Android Debug Bridge (ADB)
Richiesto per comunicare con dispositivi fisici o emulatori Android.

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
  # Oppure tramite Scoop:
  scoop install adb
  ```

### 2. llama.cpp (`llama-server`) *(Facoltativo per esecuzione locale)*
Richiesto se desideri eseguire l'inferenza locale multimodale dei modelli VLM con accelerazione GPU senza usare API Cloud.

* **macOS (con accelerazione Metal GPU)**:
  ```bash
  brew install llama.cpp
  ```
* **Linux / Windows**:
  Scarica l'eseguibile precompilato `llama-server` dalle [Release Ufficiali di llama.cpp su GitHub](https://github.com/ggerganov/llama.cpp/releases) ed inseriscilo nel `PATH` di sistema o specifica il percorso completo nel file di configurazione.

---

## 🧠 Modelli VLM Locali e Scansione Automatica

Il framework include uno **scanner automatico della cartella modelli** ([`server.models_dir`](q_test_arsenal/config/default_config.yaml)) con un **algoritmo dinamico di matching dei token** (`_ExtractTokens`) che rileva tutti i modelli `.gguf` e li accoppia automaticamente al rispettivo proiettore multimodale `mmproj`.

| Modello VLM (GGUF) | Proiettore Multimodale (mmproj) | Descrizione |
| :--- | :--- | :--- |
| `UI-TARS-7B-DPO-Q4_K_M.gguf` | `mmproj-UI-TARS-7B-f16.gguf` | Specializzato per il grounding di interfacce GUI e mobile. |
| `Muse-Glimmer-30B-Q4_1.gguf` | `mmproj-Muse-Glimmer-30B-f16.gguf` | VLM avanzato ad alta capacità visiva per interfacce complesse. |
| `Qwen2.5-7B-Instruct-Q4_K_L.gguf` | `Qwen2.5-VL-7B-Instruct.mmproj.gguf` | Modello generico Vision-Language di alta qualità. |

### 📁 Dove Posizionare i Modelli
Imposta il percorso della cartella modelli in `default_config.yaml` (`server.models_dir`):
* **macOS / Linux**: `~/.modelli_llm/`
* **Windows**: `C:\modelli_llm\`

*Nota: Lo scanner filtra ed esclude automaticamente gli LLM solo-testo che non possiedono un proiettore visuale `.mmproj` accoppiato.*

---

## ☁️ Provider VLM Cloud e Locali Supportati

**Q - Test Arsenal** supporta sia modelli locali che i principali Provider Cloud VLM con supporto per le API OpenAI Vision:

1. **Local llama-server** (Inference locale via `llama-server` con GPU Metal/CUDA/Vulkan).
2. **OpenAI Cloud Vision** (`gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`).
3. **Google Gemini Cloud Vision** (`gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash-exp`).
4. **OpenRouter Multi-Model Cloud** (`qwen/qwen-2-vl-7b-instruct`, `google/gemini-flash-1.5`, `anthropic/claude-3.5-sonnet`).
5. **Groq Fast Vision Cloud** (`llama-3.2-11b-vision-preview`, `llama-3.2-90b-vision-preview`).
6. **Ollama Local Vision** (`qwen2-vl`, `llava`, `minicpm-v`).

---

## ⚡ Quick Setup Guidato (In 2 Comandi)

Il progetto include uno script di wizard interattivo che configura l'intero ambiente in modo guidato:

```bash
# Avvia il wizard di setup interattivo:
python3 setup_wizard.py  # Oppure il comando CLI: q-setup

# Attiva l'ambiente virtuale:
source .venv/bin/activate
```

### 🧙‍♂️ Cosa fa automaticamente `setup_wizard.py`:
1. **Verifica versione Python ed Architettura CPU** (macOS Apple Silicon / Intel, Linux, Windows).
2. **Crea l'ambiente virtuale `.venv`** se non già presente.
3. **Installa le dipendenze Python ed il pacchetto `q-test-arsenal`** in modalità editable (`pip install -e .`).
4. **Verifica gli strumenti di sistema (`adb` e `llama-server`)** guidando l'installazione via Homebrew/System.
5. **Scarica i modelli VLM consigliati (UI-TARS 7B GGUF + mmproj)** in `~/.modelli_llm/` con barra di avanzamento in tempo reale e ripresa download.
6. **Configura interattivamente il file di setup unificato** [`q_test_arsenal/config/default_config.yaml`](q_test_arsenal/config/default_config.yaml) ed il file credenziali [`scenarios/env.yaml`](scenarios/env.yaml).
7. **Esegue la validazione diagnostica finale** ([`validate_setup.py`](validate_setup.py)).

---

## 🔍 Validazione Automatica dell'Ambiente

Questo progetto include uno script di diagnostica completo ([`validate_setup.py`](validate_setup.py)) che controlla se tutti i componenti di sistema, l'ambiente Python, l'eseguibile `llama-server`, la connessione ADB ed i file dei modelli sono pronti all'uso:

```bash
python validate_setup.py
```

---

## ⚙️ Configurazione del Framework

La configurazione globale di infrastruttura del framework si trova in:
👉 **[`q_test_arsenal/config/default_config.yaml`](q_test_arsenal/config/default_config.yaml)**

```yaml
provider:
  type: "local"                                                 # local | openai | gemini | openrouter | groq | ollama
  model_name: "UI-TARS-7B-DPO-Q4_K_M.gguf"
  api_url: "http://127.0.0.1:8080/v1/chat/completions"

server:
  models_dir: "~/.modelli_llm"                                  # Cartella dei modelli locali .gguf (Obbligatoria per llama-server)
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
  serial: "R52M904J1QM"                                         # Serial ADB (se vuoto, avvia il menu interattivo)
  show_touches: true

runner:
  default_max_retries: 3
  debug_screenshots_dir: "reports/screenshots"
  reports_dir: "reports"
  check_missing_env_vars: true                                  # Controllo preventivo: avvisa se mancano variabili in env.yaml

credentials:
  OPENAI_API_KEY: ""
  GEMINI_API_KEY: ""
  OPENROUTER_API_KEY: ""
  GROQ_API_KEY: ""
```

---

## 🔑 Dati dell'Applicazione e Credenziali (`scenarios/env.yaml`)

Per garantire massima flessibilità e pulizia, le utenze ed i parametri dell'applicazione di test sono disaccoppiati dalla configurazione del framework e risiedono nel singolo file:
👉 **[`scenarios/env.yaml`](scenarios/env.yaml)**

```yaml
# scenarios/env.yaml
API_URL: "api.example.com"
SHOP_CODE: "demo"
USER_EMAIL: "test_user@example.com"
USER_PASSWORD: "secure_password_123"
```

Per testare con un'altra utenza o cambiare ambiente (es. Dev / Staging / Prod), ti basterà modificare o sostituire questo singolo file.

---

## 🛡️ Controllo Preventivo a Priori delle Variabili (Pre-flight Check)

Prima di avviare qualsiasi tocco o digitazione sullo smartphone, il motore esegue un controllo di sicurezza a priori:
1. Analizza gli step dello scenario ed estrae tutti i segnaposto `${VAR_NAME}`.
2. Verifica che ogni variabile sia definita in `scenarios/env.yaml` o nell'ambiente di sistema (`os.environ`).
3. Se individua variabili mancano (es. `${USER_PASSWORD}` dimenticata), interrompe il test e mostra un box di avviso chiedendo conferma prima di interagire col telefono:

```text
⚠️ VARIABILI DI AMBIENTE MANCANTI:
Le seguenti variabili non sono state trovate in scenarios/env.yaml o nell'ambiente:
  • ${SHOP_CODE}
  • ${USER_PASSWORD}

👉 Continuare comunque l'esecuzione dello scenario? [y/N]:
```

---

## 🎯 Selezione Interattiva Modello (`--select-model` / `-m`)

Per cambiare modello VLM locale o passare ad un provider cloud in qualsiasi momento:

```bash
q-test scenarios/login_flow.yaml --select-model
# Oppure la scorciatoia breve:
q-test -m
```

### Come funziona:
1. Scansione automatica dei modelli GGUF in `server.models_dir` (`~/.modelli_llm/`).
2. Elenco dei modelli locali con proiettore `mmproj` accoppiato e dei Provider Cloud pronti all'uso.
3. Al primo avvio (se nessun modello è stato ancora scelto), il menu si apre automaticamente.
4. La scelta viene salvata in `default_config.yaml` per le esecuzioni successive.

---

## 📂 Creazione degli Scenari di Test YAML

Tutti gli scenari di test in formato YAML vanno inseriti nella cartella:
👉 **[`scenarios/`](scenarios/)** (es: `scenarios/login_flow.yaml`)

```yaml
name: "Login Flow Scenario - Production Suite"
description: "Scenario di test automatico per la configurazione dell'URL API ed il login"

steps:
  - type: "action_until"
    target: "Icona dell'ingranaggio (Impostazioni) in alto a destra dello schermo"
    until_condition: "È visibile a schermo un dialogo con titolo 'Insert API URL'."
    max_retries: 3

  - type: "type_text"
    target: "Campo di testo per l'URL API"
    value: "${API_URL}"

  - type: "type_text"
    target: "Campo di testo per lo Shop Code"
    value: "${SHOP_CODE}"

  - type: "action"
    target: "Pulsante 'Save' per salvare le impostazioni"

  - type: "type_text"
    target: "Area di testo per lo Username o Email"
    value: "${USER_EMAIL}"

  - type: "type_text"
    target: "Area di testo per la Password"
    value: "${USER_PASSWORD}"

  - type: "wait"
    seconds: 2

  - type: "action"
    target: "Pulsante azzurro con scritto 'Login'"

assertion:
  wait_seconds: 2
  description: "La schermata di Login è scomparsa ed è visibile la schermata di caricamento/sincronizzazione o il carrello principale."
```

---

## 🏆 Suite Manifest & Gestione Errori (`continue_on_failure`)

### 1. Scenari che contengono altri Scenari
Puoi creare un file YAML di Suite (es: `scenarios/master_suite.yaml`) per ordinare ed eseguire in sequenza varie suite di test:

```yaml
name: "E2E Complete Test Suite"
description: "Suite principale che ordina ed esegue in sequenza la configurazione, il login ed il checkout"
continue_on_failure: true

scenarios:
  - file: "scenarios/login_flow.yaml"
    use_macro: true
    continue_on_failure: false

  - file: "scenarios/checkout_flow.yaml"
    use_macro: false
```

Per eseguire l'intera suite ordinata dal manifest:
```bash
q-test scenarios/master_suite.yaml
```

---

## 🏃 Esecuzione dei Test (CLI `q-test`)

Il framework fornisce il pratico comando CLI **`q-test`**:

### 1. Esecuzione Batch (Tutti gli scenari in `scenarios/`)
```bash
q-test
```

### 2. Esecuzione di uno Scenario Specifico
```bash
q-test scenarios/login_flow.yaml
```

### 3. ⚡ Registrazione ed Esecuzione Ibrida con Macro (`--save-macro` e `--use-macro`)
* **Registrazione ed esportazione Macro JSON**:
  ```bash
  q-test scenarios/login_flow.yaml --save-macro
  ```
* **Esecuzione Ibrida (Fast-Path ~100ms + Fallback VLM)**:
  ```bash
  q-test scenarios/login_flow.yaml --use-macro
  ```

---

## 📊 Telemetria, Root Cause Debugging e Report HTML

Dopo l'esecuzione di un test, il framework genera automaticamente:

1. **Dashboard Master & Report Singoli Interattivi**: Salvati nella cartella `reports/` (es: `reports/login_flow_report.html` e `reports/master_report.html`) con navigazione 1-click tra la Master Dashboard ed i report singoli.
2. **Telemetria delle Latenze & KPI Performance**: Misurazione al millisecondo per `Screencap`, `VLM Pass 1 (Coarse)`, `VLM Pass 2 (Zoom Crop Fine)`, `ADB Input`.
3. **🔍 Root Cause Debug Analysis per Step Falliti**: Genera una card speciale di debug con la risposta JSON raw del VLM, le coordinate tentate, le note di retry ed il ritaglio zoom sull'area bersaglio.

---

## 🙏 Riconoscimenti e Crediti

Questo progetto nasce ed è stato sviluppato come evoluzione ed estensione di **[MobileRun (droidrun)](https://github.com/droidrun/mobilerun)**, creato da **[Niels Schmidt](https://github.com/niels-schmidt)** ([DroidRun](https://droidrun.ai/)).

### 💡 Il contributo di `mobilerun` a questo progetto:
* **Infrastruttura Agenti & Tooling Mobile**: `mobilerun` fornisce l'architettura di base per l'interazione con i dispositivi (ADB/iOS), il supporto multimodale per i provider LLM/VLM ed il sistema di macro/telemetria.
* **Q - Test Arsenal**: Sviluppato in autonomia da **Emanuele Coltro**, estende l'infrastruttura originale trasformandola in un framework autonomo di testing E2E visivo basato su scenari YAML, motore di grounding a due livelli (**2-Pass Zoom Crop**), report HTML interattivi con telemetria avanzata, Fast-Path Macro, disaccoppiamento credenziali `scenarios/env.yaml`, pre-flight variable check ed il comando CLI `q-test`.

Un sentito ringraziamento a Niels Schmidt e al team di DroidRun per lo straordinario lavoro svolto nel progetto originale.

---

## 📄 Licenza

Distribuito sotto licenza **MIT License**. Per maggiori dettagli, consulta il file [LICENSE](LICENSE).
