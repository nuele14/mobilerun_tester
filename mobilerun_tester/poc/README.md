# Mobilerun Tester - Proof of Concept (PoC) con `llama.cpp`

Questo modulo fornisce un **Proof of Concept (PoC)** per l'automazione ed il testing di app Android (incluso le app sviluppate con **Flutter**) utilizzando la visione tramite un LLM locale (es. **Qwen2-VL** o **Qwen2.5-VL**) gestito autonomamente tramite `llama.cpp`.

---

## 🛠️ Prerequisiti e Setup dell'Ambiente

### 1. Requisiti di Sistema
- **Python**: `>= 3.11`
- **ADB (Android Debug Bridge)**: Installato e configurato nelle variabili d'ambiente (`PATH`).
- **Dispositivo Android**: Emulatore o dispositivo fisico connesso con **Debug USB abilitato**.
- **`llama.cpp`**: Installato ed accessibile (eseguibile `llama-server`).

### 2. Download dei Modelli Vision per `llama.cpp`
Per il rilevamento delle coordinate (UI Grounding) e le asserzioni visive sulle app Flutter, si consiglia il modello **Qwen2-VL-7B-Instruct** (o la versione 2B / Qwen2.5-VL).

Scarica da HuggingFace i seguenti due file:
1. **Modello Principale GGUF**: ad esempio `qwen2-vl-7b-instruct-q4_k_m.gguf`
2. **Proiettore Multimodale (mmproj)**: ad esempio `mmproj-qwen2-vl-7b-instruct-f16.gguf`

---

## ⚙️ Configurazione di `poc_config.yaml`

Apri il file [`poc_config.yaml`](file:///Users/emanuelecoltro/Documents/Lavoro/Planet%20Soluzioni/Progetti/mobilerun_tester/mobilerun_tester/poc/poc_config.yaml) e imposta i percorsi corretti:

```yaml
llama_cpp:
  # Nome o percorso assoluto dell'eseguibile llama-server
  server_binary: "llama-server"
  
  # Percorso assoluto al modello GGUF scaricato
  model_path: "/Users/tuo_utente/models/qwen2-vl-7b-instruct-q4_k_m.gguf"
  
  # Percorso assoluto al file mmproj scaricato
  mmproj_path: "/Users/tuo_utente/models/mmproj-qwen2-vl-7b-instruct-f16.gguf"
  
  # Configurazione di rete
  host: "127.0.0.1"
  port: 8080
  
  # Offload sulla GPU (99 carica tutti i layer su GPU/Metal)
  gpu_layers: 99
  
  # Avvia automaticamente llama-server se non è già attivo
  auto_start_server: true
```

---

## 🚀 Avvio del Proof of Concept

1. **Collega il dispositivo Android**:
   Verifica che il dispositivo sia riconosciuto da ADB:
   ```bash
   adb devices
   ```

2. **Esegui lo script del PoC**:
   Puoi avviare lo script Python in completa autonomia. Se `llama-server` non è ancora attivo, lo script provvederà ad avviarlo automaticamente in background ed a fare il check finché il modello non è pronto.

   ```bash
   python mobilerun_tester/poc/poc_runner.py
   ```

---

## 📜 Come funziona lo Scenario di Test YAML

Lo scenario di test (es. [`poc_scenario.yaml`](file:///Users/emanuelecoltro/Documents/Lavoro/Planet%20Soluzioni/Progetti/mobilerun_tester/mobilerun_tester/poc/poc_scenario.yaml)) definisce una sequenza di azioni in linguaggio naturale:

```yaml
name: "PoC Flutter Login Test"
description: "Test di login basato su Vision + LLM Locale (llama.cpp)"

steps:
  - type: "action"
    target: "Pulsante 'Accedi' o 'Sign In'"

  - type: "type_text"
    target: "Campo di testo per inserire l'email"
    value: "test@example.com"

assertion:
  description: "La schermata attuale mostra la pagina del profilo o la richiesta OTP"
```

### Flusso di Esecuzione:
1. **Screenshot ADB**: Scatta uno screenshot della schermata corrente.
2. **UI Grounding**: Invia lo screenshot a `llama-server` e chiede le coordinate $(x, y)$ dell'elemento target.
3. **ADB Interaction**: Converte le coordinate percentuali nelle dimensioni reali dello schermo ed esegue il `tap` o `input text`.
4. **Visual Assertion**: Scatta uno screenshot finale e chiede all'LLM di validare se l'asserzione è superata (ritornando JSON con `pass: true/false` e la motivazione).

---

## 🔮 Evoluzioni Future dal PoC
Dopo aver validato il PoC con il tuo ambiente locale `llama.cpp`:
- **Retry automatizzato**: Gestione di tentativi multipli per elementi dinamici.
- **Reporting JUnit XML / HTML**: Integrazione nei report di test per CI/CD.
- **Supporto multi-dispositivo**: Esecuzione parallela di test su più telefoni.
