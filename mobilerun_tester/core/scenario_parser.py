import os
import yaml
from pathlib import Path
from typing import Dict, Any, List


class ScenarioParser:
    """Carica, valida e risolve gli scenari di test da file YAML."""

    @staticmethod
    def load_yaml(yaml_path: str) -> Dict[str, Any]:
        path = Path(yaml_path)
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}

    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        return ScenarioParser.load_yaml(config_path)

    @staticmethod
    def load_scenario(scenario_path: str) -> Dict[str, Any]:
        path = Path(scenario_path)
        if not path.exists():
            raise FileNotFoundError(f"File scenario non trovato: {scenario_path}")

        data = ScenarioParser.load_yaml(scenario_path)

        if not isinstance(data, dict) or "steps" not in data:
            raise ValueError(f"Formato scenario non valido in {scenario_path}: manca il blocco 'steps'.")

        data["steps"] = ScenarioParser._resolve_variables(data["steps"])
        return data

    @staticmethod
    def _resolve_variables(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Risolve eventuali variabili di ambiente (es. ${ENV_VAR}) presenti nei valori degli step."""
        resolved_steps = []
        for step in steps:
            resolved_step = step.copy()
            if "value" in resolved_step and isinstance(resolved_step["value"], str):
                val = resolved_step["value"]
                if val.startswith("${") and val.endswith("}"):
                    env_name = val[2:-1]
                    resolved_step["value"] = os.getenv(env_name, val)
            resolved_steps.append(resolved_step)
        return resolved_steps
