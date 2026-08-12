# 🚀 MobileRun Tester

**MobileRun Tester** è un framework di testing automatizzato E2E visivo per applicazioni mobile (**Flutter & Native Android**), basato su modelli Vision-Language (**VLM**) eseguiti in locale.

Il sistema esegue un grounding visivo a due livelli (**Coarse + Fine Bounding Box Zoom**) ed interagisce direttamente con il dispositivo Android via ADB, senza dipendere da servizi cloud esterni o ID di elemento hardcodati nel codice.

---

## 📋 Indice
1. [Componenti di Sistema Richiesti](#-componenti-di-sistema-richiesti)
2. [Modelli VLM Consigliati](#-modelli-vlm-consigliati)
3. [Setup dell'Ambiente e Dipendenze](#-setup-dellambiente-e-dipendenze)
4. [Validazione Automatica dell'Ambiente](#-validazione-automatica-dellambiente)
5. [Dove Impostare la Configurazione](#-dove-impostare-la-configurazione)
6. [Dove Inserire e Creare gli Scenari di Test](#-dove-inserire-e-creare-gli-scenari-di-test)
7. [Esecuzione dei Test (CLI)](#-esecuzione-dei-test-cli)
8. [Report ed Ispezione Log](#-report-ed-ispezione-log)
9. [Riconoscimenti e Crediti](#-riconoscimenti-e-crediti)

---

## 🛠️ Componenti di Sistema Richiesti

Prima di avviare **MobileRun Tester**, assicurati che siano installati i seguenti componenti di sistema sul tuo computer:

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

### 2. llama.cpp (`llama-server`)
Richiesto per eseguire l'infezezza locale multimodale dei modelli VLM con accelerazione GPU.

* **macOS (con accelerazione Metal GPU)**:
  ```bash
  brew install llama.cpp
  ```
* **Linux / Windows**:
  Scarica l'eseguibile precompilato `llama-server` dalle [Release Ufficiali di llama.cpp su GitHub](https://github.com/ggerganov/llama.cpp/releases) ed inseriscilo nel `PATH` di sistema o specifica il percorso completo nel file di configurazione.

---

## 🧠 Modelli VLM Consigliati

Per garantire la massima precisione nell'individuazione visiva dei bottoni e campi di testo (Grounding), si consiglia l'uso dei seguenti modelli multimodali in formato GGUF:

| Tipo | Modello Consigliato | Descrizione |
| :--- | :--- | :--- |
| **Modello VLM (GGUF)** | `UI-TARS-7B-DPO-Q4_K_M.gguf` | Modello specializzato per il grounding di interfacce GUI e mobile. |
| **Proiettore Multimodale (mmproj)** | `mmproj-UI-TARS-7B-f16.gguf` | Proiettore di visione associato al modello UI-TARS. |
| **Alternativa VLM** | `Qwen2-VL-7B-Instruct-Q4_K_M.gguf` | Modello generico per Vision-Language di alta qualità. |

### 📁 Dove Posizionare i Modelli
Si consiglia di creare una cartella dedicata nella directory home utente, ad esempio:
* **macOS / Linux**: `~/.modelli_llm/` (es: `/Users/nomeutente/.modelli_llm/UI-TARS-7B-DPO-Q4_K_M.gguf`)
* **Windows**: `C:\modelli_llm\`

---

## 📦 Setup dell'Ambiente e Dipendenze

### 1. Creazione del Virtual Environment
Crea ed attiva un ambiente virtuale Python (versione Python $\ge 3.11$):

```bash
# Su macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate

# Su Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

*(In alternativa puoi usare `uv venv` per una creazione istantanea).*

### 2. Installazione delle Dipendenze Python
Installa tutti i pacchetti necessari specificati nel file [`requirements.txt`](requirements.txt):

```bash
pip install -r requirements.txt
```

---

## 🔍 Validazione Automatica dell'Ambiente

Il progetto include uno script di diagnostica completo ([`validate_setup.py`](validate_setup.py)) che controlla se tutti i componenti di sistema, l'ambiente Python, l'eseguibile `llama-server`, la connessione ADB ed i file `.gguf` dei modelli sono pronti all'uso:

```bash
python validate_setup.py
```

### Controlli effettuati da `validate_setup.py`:
1. **Dipendenze Python**: `PyYAML`, `Pillow`, `ImageHash`, `Rich`, `HTTPX`.
2. **Moduli Interni Framework**: `mobilerun_tester.core`, `runner`, `cli`.
3. **ADB & Dispositivi**: Presenza del comando `adb` e presenza di uno smartphone/emulatore Android connesso.
4. **VLM Engine**: Presenza dell'eseguibile `llama-server` e relativo stato health.
5. **Modelli VLM**: Verifica esistenza su disco dei file `.gguf` del modello e dell'mmproj configurati.
6. **Scenari**: Presenza di file `.yaml` validi nella cartella `scenarios/`.

---

## ⚙️ Dove Impostare la Configurazione

La configurazione globale del framework si trova in:
👉 **[`mobilerun_tester/config/default_config.yaml`](mobilerun_tester/config/default_config.yaml)**

### Parametri Principali

```yaml
server:
  host: "127.0.0.1"
  port: 8080
  model_path: "~/.modelli_llm/UI-TARS-7B-DPO-Q4_K_M.gguf"       # Percorso al modello GGUF
  mmproj_path: "~/.modelli_llm/mmproj-UI-TARS-7B-f16.gguf"      # Percorso al proiettore mmproj
  binary: "llama-server"                                        # Nome o percorso all'eseguibile
  context_size: 4096
  gpu_layers: 99                                                # Layer da caricare su GPU (-ngl 99)
  threads: 8
  flash_attn: true                                              # Flash Attention (-fa on)
  auto_start: true                                              # Avvia il server automaticamente se non attivo

device:
  serial: ""                                                    # Serial ADB (se vuoto o non connesso, si avvia il menu interattivo)
  show_touches: true                                            # Attiva l'indicatore bianco dei tocchi a schermo

runner:
  default_max_retries: 3
  debug_screenshots_dir: "reports/screenshots"
  reports_dir: "reports"
```

### 📱 Selezione Interattiva Dispositivo ADB & Autosalvataggio Preferenze
Quando il framework viene avviato:
1. Se il parametro `device.serial` nel file di configurazione è vuoto (`""`) oppure il dispositivo salvato **non è attualmente connesso** via USB/ADB:
   - Il sistema scansiona i dispositivi Android ed emulatori collegati.
   - Viene mostrato un **menu di selezione interattivo** da terminale.
2. Una volta selezionato il dispositivo desiderato (es. `R52M904J1QM`), il suo serial viene **salvato automaticamente nelle preferenze** ([`mobilerun_tester/config/default_config.yaml`](mobilerun_tester/config/default_config.yaml)).
3. Per le esecuzioni successive, il sistema utilizzerà direttamente il dispositivo salvato senza più richiedere l'intervento dell'utente!

---

## 📂 Dove Inserire e Creare gli Scenari di Test

Tutti gli scenari di test in formato YAML vanno inseriti nella cartella:
👉 **[`scenarios/`](scenarios/)** (es: `scenarios/login_flow.yaml`)

### Struttura di uno Scenario YAML

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
    value: "betacc.planetps.it"

  - type: "action"
    target: "Pulsante 'Save' per salvare le impostazioni"

  - type: "type_text"
    target: "Area di testo per lo Username o Email"
    value: "${USER_EMAIL}"                                      # Supporta variabili d'ambiente

  - type: "type_text"
    target: "Area di testo per la Password"
    value: "${USER_PASSWORD}"

  - type: "action"
    target: "Pulsante azzurro con scritto 'Login'"

assertion:
  description: "La schermata di Login è scomparsa e si è aperto il catalogo dell'applicazione."
```

### Tipi di Step Disponibili:
* `action`: Grounding VLM + Tap singolo sull'elemento specificato in `target`.
* `type_text`: Grounding VLM + Selezione + Pulizia automatica + Inserimento del testo specificato in `value`.
* `action_until`: Ripete il tap fino a quando la condizione `until_condition` non risulta vera.
* `long_press_until`: Esegue la pressione prolungata (Long Press) fino al soddisfacimento di `until_condition`.

---

## 🏃 Esecuzione dei Test (CLI)

### 1. Esecuzione Batch (Tutti gli scenari in `scenarios/`)
```bash
python -m mobilerun_tester.cli.main
```

### 2. Esecuzione di uno Scenario Specifico
```bash
python -m mobilerun_tester.cli.main scenarios/login_flow.yaml
```

### 3. ⚡ Registrazione ed Esecuzione Ibrida con Macro (`--save-macro` e `--use-macro`)
Per registrare i tocchi e velocizzare l'esecuzione saltando le chiamate VLM quando la schermata è invariata:

* **Registrazione ed esportazione Macro JSON**:
  ```bash
  python -m mobilerun_tester.cli.main scenarios/login_flow.yaml --save-macro
  ```
  Salva la sequenza delle azioni, coordinate percentuali ed hash visivi in `scenarios/macros/login_flow.macro.json`.

* **Esecuzione Ibrida (Fast-Path + Fallback VLM)**:
  ```bash
  python -m mobilerun_tester.cli.main scenarios/login_flow.yaml --use-macro
  ```
  Confronta lo schermo attuale con l'hash salvato: se la schermata coincide ($\ge 85\%$), esegue il tocco in **~100ms** senza impegnare il VLM; se lo schermo differisce, passa automaticamente la palla all'IA visiva (**VLM 2-Pass Zoom Crop**).

---

## 📊 Report ed Ispezione Log

Dopo l'esecuzione di un test, il framework genera automaticamente:
1. **Report HTML Interattivi**: Salvati nella cartella `reports/` (es: `reports/login_flow_report.html` e dashboard `reports/master_report.html`). Contengono gli screenshot con l'overlay del mirino rosso e le etichette dei tocchi.
2. **File di Log Dettagliati**: Salvati nella cartella `logs/run_YYYYMMDD_HHMMSS.log` (automaticamente ignorata da git), contenenti tutte le chiamate ADB, risposte JSON dei modelli e stack trace per il debugging.

---

## 🙏 Riconoscimenti e Crediti

Questo progetto nasce ed è stato sviluppato come evoluzione ed estensione di **[MobileRun (droidrun)](https://github.com/droidrun/mobilerun)**, creato da **[Niels Schmidt](https://github.com/niels-schmidt)** ([DroidRun](https://droidrun.ai/)).

### 💡 Il contributo di `mobilerun` a questo progetto:
* **Infrastruttura Agenti & Tooling Mobile**: `mobilerun` fornisce l'architettura di base per l'interazione con i dispositivi (ADB/iOS), il supporto multimodale per i provider LLM/VLM ed il sistema di macro/telemetria.
* **MobileRun Tester**: Sviluppato da **Emanuele Coltro**, estende l'infrastruttura originale trasformandola in un framework autonomo di testing E2E basato su scenari YAML visivi, motore di grounding a due livelli (**2-Pass Zoom Crop**), report HTML interattivi e CLI avanzata con spinner.

Un sentito ringraziamento a Niels Schmidt e al team di DroidRun per lo straordinario lavoro svolto nel progetto originale.

---

## 📄 Licenza

Distribuito sotto licenza **MIT License**. Per maggiori dettagli, consulta il file [LICENSE](LICENSE).
