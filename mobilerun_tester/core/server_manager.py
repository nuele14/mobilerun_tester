import os
import shutil
import subprocess
import time
import urllib.request
from typing import Optional, Dict, Any


class LlamaServerManager:
    """Gestisce il ciclo di vita del server VLM locale (llama-server) ad alte prestazioni."""

    def __init__(self, config: Dict[str, Any]):
        server_cfg = config.get("server", {})
        self.binary = os.path.expanduser(server_cfg.get("binary", "llama-server"))
        self.model_path = os.path.expanduser(server_cfg.get("model_path", ""))
        self.mmproj_path = os.path.expanduser(server_cfg.get("mmproj_path", ""))
        self.host = server_cfg.get("host", "127.0.0.1")
        self.port = server_cfg.get("port", 8080)
        self.context_size = server_cfg.get("context_size", 4096)
        self.gpu_layers = server_cfg.get("gpu_layers", 99)
        self.threads = server_cfg.get("threads", 8)
        self.flash_attn = server_cfg.get("flash_attn", True)
        self.cache_reuse = server_cfg.get("cache_reuse", 256)
        self.auto_start = server_cfg.get("auto_start", True)
        self.timeout = server_cfg.get("startup_timeout_seconds", 60)
        
        self.base_url = f"http://{self.host}:{self.port}"
        self.process: Optional[subprocess.Popen] = None

    def is_server_running(self) -> bool:
        """Verifica se llama-server è già in ascolto ed operativo."""
        try:
            url = f"{self.base_url}/health"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        return False

    def start(self) -> bool:
        """Avvia llama-server con accelerazione Metal GPU e Flash Attention se non è attivo."""
        if self.is_server_running():
            print(f"🟢 [llama.cpp] Server già attivo su {self.base_url}")
            return True

        if not self.auto_start:
            print(f"🔴 [llama.cpp] Server non attivo su {self.base_url} e 'auto_start' è disabilitato.")
            return False

        binary_path = shutil.which(self.binary) or self.binary
        if not os.path.exists(binary_path) and not shutil.which(self.binary):
            raise FileNotFoundError(f"Eseguibile llama-server non trovato in: {self.binary}")

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"File modello GGUF non trovato: {self.model_path}")

        if not os.path.exists(self.mmproj_path):
            raise FileNotFoundError(f"File mmproj GGUF non trovato: {self.mmproj_path}")

        cmd = [
            binary_path,
            "-m", self.model_path,
            "--mmproj", self.mmproj_path,
            "--host", self.host,
            "--port", str(self.port),
            "-c", str(self.context_size),
            "-ngl", str(self.gpu_layers),
            "-fa", "on" if self.flash_attn else "off",
            "--cache-reuse", str(self.cache_reuse),
            "-t", str(self.threads)
        ]

        print(f"🚀 [llama.cpp] Avvio in corso di llama-server ad alte prestazioni...")
        print(f"   Comando: {' '.join(cmd)}")

        log_file = open("/tmp/llama_server.log", "w")
        self.process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True
        )

        start_time = time.time()
        print("⏳ Attesa dell'inizializzazione del modello Vision...")
        while time.time() - start_time < self.timeout:
            if self.is_server_running():
                print(f"✅ [llama.cpp] Server avviato ed operativo su {self.base_url}")
                return True
            time.sleep(1.5)

        print(f"❌ [llama.cpp] Timeout durante l'avvio del server ({self.timeout}s).")
        self.stop()
        return False

    def stop(self):
        """Interrompe il processo llama-server se avviato dal framework."""
        if self.process:
            print("🛑 [llama.cpp] Arresto di llama-server in corso...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            print("✅ [llama.cpp] Server arrestato.")
