# 🚀 MobileRun Tester

**MobileRun Tester** è un framework di testing E2E visivo ed autonomo per applicazioni mobile (**Flutter & Native Android**), alimentato da modelli di Vision-Language (**VLM**) eseguiti in locale.

---

## ⚡ Caratteristiche Principali

- 🧠 **Grounding Visivo Locale (VLM)**: Utilizza `llama-server` in locale con modelli come **Qwen2-VL** e **UI-TARS-7B**, senza costi API o dipendenze da server cloud esterni.
- 🚀 **Accelerazione Hardware GPU**: Sfrutta le opzioni Metal GPU per macOS (`-ngl 99`), **Flash Attention** (`-fa on`) e riutilizzo della cache KV (`--cache-reuse 256`).
- 📐 **Adattamento Dinamico dello Schermo**: Rileva l'orientamento reale dello schermo ad ogni screenshot per garantire la precisione sia in **Landscape ($1920 \times 1200$)** sia in **Portrait ($1200 \times 1920$)**.
- 🧹 **Sanitizzazione del Testo**: Pulizia avanzata dei campi prima di ogni digitazione mediante sequenza da tastiera nativa (`MOVE_END` $\rightarrow$ `CTRL+A` $\rightarrow$ `DELETE`).
- 📊 **Report HTML Visivi & Master Dashboard**: Generazione automatica di report HTML interattivi con KPI, evidenziatori rossi dei tocchi ed esiti delle asserzioni.

---

## 🏗️ Architettura del Framework

```text
mobilerun_tester/
├── config/
│   └── default_config.yaml       # Configurazione globale (VLM, ADB, Timeouts)
├── core/
│   ├── adb_engine.py             # Primitive ADB native e dinamica schermi
│   ├── vision_engine.py          # Grounding Single-Pass, Zoom Crop ed Asserzioni
│   ├── server_manager.py         # Lifecycle del daemon llama-server
│   └── scenario_parser.py        # Parser YAML con sostituzione ${ENV_VAR}
├── runner/
│   ├── test_runner.py            # Orchestratore step di test e telemetria
│   └── report_generator.py       # Generatore di Report HTML e Dashboard
├── cli/
│   └── main.py                   # CLI ed esecutore Batch di test
└── scenarios/                    # Cartella degli scenari di test YAML
    └── login_flow.yaml
```

---

## 🚀 Quickstart & Utilizzo

### 1. Esecuzione Batch Predefinita (Tutti gli scenari)

Per eseguire automaticamente tutti i file `.yaml` contenuti nella cartella `scenarios/`:

```bash
python -m mobilerun_tester.main
```

Alla fine dell'esecuzione verranno generati i report individuali e la dashboard globale in `reports/master_report.html`.

### 2. Esecuzione di uno Scenario Singolo

Per eseguire uno specifico scenario YAML:

```bash
python -m mobilerun_tester.main scenarios/login_flow.yaml
```

---

## 📝 Esempio di Scenario (`scenarios/login_flow.yaml`)

```yaml
name: "Login Flow Scenario"
description: "Configurazione URL API ed autenticazione utente"

steps:
  - type: "action_until"
    target: "Icona dell'ingranaggio (Impostazioni) in alto a destra dello schermo"
    until_condition: "È visibile a schermo il dialogo 'Insert API URL and store code'."

  - type: "type_text"
    target: "Campo di testo per l'URL API nel dialogo"
    value: "betacc.planetps.it"

  - type: "action"
    target: "Pulsante 'Save' nel dialogo"

  - type: "type_text"
    target: "Area di testo per Username"
    value: "${USER_EMAIL}"

  - type: "type_text"
    target: "Area di testo per Password"
    value: "${USER_PASSWORD}"

  - type: "action"
    target: "Pulsante azzurro 'Login'"

assertion:
  description: "Si è aperto il catalogo/home page dell'applicazione."
```

---

## 📄 Licenza

Questo progetto è distribuito sotto la licenza **MIT License**.
Per maggiori dettagli, consulta il file [LICENSE](LICENSE).

Copyright (c) 2026 Emanuele Coltro  
Copyright (c) 2025 Niels Schmidt
