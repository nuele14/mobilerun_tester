#!/usr/bin/env python3
"""
Runner per l'esecuzione di test usando MobileAgent

Questo script dimostra come eseguire test autonomi tramite l'Agent ReAct.
"""

import asyncio
import yaml
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Aggiungiamo la directory del progetto al path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Scenario:
    def __init__(self, path: str):
        self.data = self._load_scenario(path)
    
    def _load_scenario(self, path: str):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_steps(self):
        return self.data.get('steps', []) or []
    
    def get_postconditions(self):
        return self.data.get('postconditions', []) or []
    
    def get_result(self):
        return self.data.get('expected_result', 'success')

class MobileAgentRunner:
    def __init__(self, scenario_path: str):
        self.scenario = Scenario(scenario_path)
        self.agent = None
        self.device_serial = None
        
    async def setup_agent(self):
        # Configurazione agente con reasoning=True (modo planning)
        try:
            from mobilerun.agent.droid.droid_agent import MobileAgent
            from mobilerun.config_manager.config import AgentConfig
            
            agent_config = AgentConfig(
                name="droidrun",
                reasoning=True,
                max_steps=10
            )
            
            # Configurazione logging
            import mobilerun.log_handlers
            mobilerun.log_handlers.configure_logging(debug=True)
            
            self.agent = MobileAgent(
                goal=f"Eseguire test: {self.scenario.data.get('name')}",
                config=AgentConfig(
                    agent=agent_config,
                    device=None,
                    tools=None,
                    logging=mobilerun.config_manager.config.LoggingConfig(),
                    telemetry=mobilerun.config_manager.config.TelemetryConfig()
                )
            )
            logger.info("Agent configurato")
            return True
        except Exception as e:
            logger.error(f"Configurazione agente fallita: {e}")
            return False
        
    async def run(self):
        if not await self.setup_agent():
            return False
        
        # Memorizza informazioni del test
        self.agent.shared_state.custom_vars = {
            "scenario_name": self.scenario.data.get('name'),
            "steps": self.scenario.get_steps(),
            "postconditions": self.scenario.get_postconditions(),
            "expected_result": self.scenario.get_result()
        }
        
        # Esecuzione con reasoning mode
        logger.info("Avvio dell'Eseurore MobileAgent")
        try:
            result = await self.agent.run()
            success = result.success if hasattr(result, 'success') else True
            reason = result.reason if hasattr(result, 'reason') else "Successo"
            
            # Verifica post-condizioni
            if self.scenario.get_postconditions():
                post_ok = True
                for pc in self.scenario.get_postconditions():
                    try:
                        # Implementare logica di verifica
                        post_ok &= self._check_condition(pc)
                    except Exception as e:
                        logger.error(f"Errore controllo post-condizione {pc}: {e}")
                        post_ok = False
                success = post_ok and success
                reason = ("Successo" if success else "Fallimento post-condizioni")
            
            logger.info(f"Risultato: {success} ({reason})")
            return success
        except Exception as e:
            logger.error(f"Errore durante esecuzione: {e}")
            return False
        
    def _check_condition(self, condition):
        # Placeholder per verificare le condizioni
        # In produzione: implementare controlli specifici
        logger.info(f"Verifica: {condition.get('name')}")
        return True

async def main():
    parser = argparse.ArgumentParser(description="Test Runner con MobileAgent")
    parser.add_argument("--scenario", type=str, required=True,
                       help="Percorso del file YAML dello scenario")
    parser.add_argument("--device", type=str, default="emulator-5554",
                       help="Serial del dispositivo (default: emulator-5554)")
    
    args = parser.parse_args()
    
    runner = MobileAgentRunner(args.scenario)
    success = await runner.run()
    
    if success:
        print("✅ TEST COMPLETATO CON SUCCESSO")
    else:
        print("❌ TEST FALLITO")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))