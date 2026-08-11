"""
===============================================================================
[Design] SCENARIO PARSER: Loads YAML scenarios and resolves ${ENV_VAR} placeholders.
===============================================================================
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List


class ScenarioParser:
    """[Teacher] Validates and parses YAML scenario and configuration files."""

    @staticmethod
    def LoadYamlDocument(yaml_path: str) -> Dict[str, Any]:
        """[Function] Loads unconstrained YAML dictionary."""
        p = Path(yaml_path)
        if not p.exists():
            return {}
        with open(p, "r", encoding="utf-8") as f:
            d = yaml.safe_load(f)
        return d if isinstance(d, dict) else {}

    @staticmethod
    def LoadConfigurationFile(config_path: str) -> Dict[str, Any]:
        """[Function] Loads global configuration dictionary."""
        return ScenarioParser.LoadYamlDocument(config_path)

    @staticmethod
    def LoadTestScenario(scenario_path: str) -> Dict[str, Any]:
        """[Function] Loads scenario YAML enforcing 'steps' block presence."""
        p = Path(scenario_path)
        if not p.exists():
            raise FileNotFoundError(f"Scenario not found: {scenario_path}")
        d = ScenarioParser.LoadYamlDocument(scenario_path)
        if not isinstance(d, dict) or "steps" not in d:
            raise ValueError(f"Invalid scenario in {scenario_path}: missing 'steps' block.")
        d["steps"] = ScenarioParser.ResolveEnvironmentVariables(d["steps"])
        return d

    @staticmethod
    def ResolveEnvironmentVariables(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """[Function] Replaces ${VAR_NAME} placeholders with OS environment values."""
        res = []
        for step in steps:
            s = step.copy()
            if isinstance(s.get("value"), str) and s["value"].startswith("${") and s["value"].endswith("}"):
                s["value"] = os.getenv(s["value"][2:-1], s["value"])
            res.append(s)
        return res

    # Aliases
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        return ScenarioParser.LoadConfigurationFile(config_path)

    @staticmethod
    def load_scenario(scenario_path: str) -> Dict[str, Any]:
        return ScenarioParser.LoadTestScenario(scenario_path)
