"""
===============================================================================
[Design] SERVER MANAGER: Background llama-server process lifecycle controller.
1. Reuses active server instance on 127.0.0.1:8080 if healthy.
2. Spawns daemon with Metal GPU (-ngl 99), Flash Attention (-fa on), -t 8.
===============================================================================
"""

import os
import shutil
import subprocess
import time
import urllib.request
from typing import Optional, Dict, Any
from q_test_arsenal.core.logger import GetLogger


class LlamaServerManager:
    """[Teacher] Subprocess manager for local llama-server VLM daemon."""

    # === [ SECTION 1: INIT & HEALTH ] ===

    def __init__(self, config: Dict[str, Any]):
        cfg = config.get("server", {})
        self.binary = os.path.expanduser(cfg.get("binary", "llama-server"))
        self.model_path = os.path.expanduser(cfg.get("model_path", ""))
        self.mmproj_path = os.path.expanduser(cfg.get("mmproj_path", ""))
        self.host = cfg.get("host", "127.0.0.1")
        self.port = cfg.get("port", 8080)
        self.context_size = cfg.get("context_size", 4096)
        self.gpu_layers = cfg.get("gpu_layers", 99)
        self.threads = cfg.get("threads", 8)
        self.flash_attn = cfg.get("flash_attn", True)
        self.cache_reuse = cfg.get("cache_reuse", 256)
        self.auto_start = cfg.get("auto_start", True)
        self.timeout = cfg.get("startup_timeout_seconds", 60)
        
        self.base_url = f"http://{self.host}:{self.port}"
        self.process: Optional[subprocess.Popen] = None

    def IsServerHealthy(self) -> bool:
        """[Function] Checks /health endpoint status 200."""
        try:
            req = urllib.request.Request(f"{self.base_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    # === [ SECTION 2: LIFECYCLE ] ===

    def StartLlamaServer(self) -> bool:
        """[Function] Spawns llama-server daemon with hardware acceleration flags."""
        logger = GetLogger()
        if self.IsServerHealthy():
            logger.info(f"llama-server already running on {self.base_url}")
            return True

        if not self.auto_start:
            logger.warning(f"llama-server auto_start disabled and server unready at {self.base_url}")
            return False

        bin_path = shutil.which(self.binary) or self.binary
        cmd = [
            bin_path, "-m", self.model_path, "--mmproj", self.mmproj_path,
            "--host", self.host, "--port", str(self.port), "-c", str(self.context_size),
            "-ngl", str(self.gpu_layers), "-fa", "on" if self.flash_attn else "off",
            "--cache-reuse", str(self.cache_reuse), "-t", str(self.threads)
        ]

        logger.info(f"Launching llama-server: {' '.join(cmd)}")
        self.process = subprocess.Popen(cmd, stdout=open("/tmp/llama_server.log", "w"), stderr=subprocess.STDOUT, text=True)

        start_time = time.time()
        while time.time() - start_time < self.timeout:
            if self.IsServerHealthy():
                logger.info(f"llama-server ready on {self.base_url}")
                return True
            time.sleep(1.5)

        self.StopLlamaServer()
        return False

    def StopLlamaServer(self):
        """[Function] Terminates spawned llama-server daemon process."""
        if self.process:
            logger = GetLogger()
            logger.info("Stopping llama-server daemon...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    # Aliases
    def start(self) -> bool:
        return self.StartLlamaServer()

    def stop(self):
        self.StopLlamaServer()
