"""
===============================================================================
[Design] SCENARIO PARSER: Loads YAML scenarios, resolves ${ENV_VAR} placeholders,
parses suite manifests, and expands included sub-scenarios.
===============================================================================
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List


class ScenarioParser:
    """[Teacher] Validates and parses YAML scenario, suite manifests, and configuration files."""

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
    def IsSuiteScenario(scenario_path: str) -> bool:
        """[Function] Checks if YAML document is a meta-suite manifest containing multiple scenarios."""
        d = ScenarioParser.LoadYamlDocument(scenario_path)
        return bool(isinstance(d, dict) and ("scenarios" in d or "include_scenarios" in d) and "steps" not in d)

    @staticmethod
    def LoadSuiteManifest(scenario_path: str) -> Dict[str, Any]:
        """[Function] Parses a suite manifest YAML containing ordered sub-scenarios."""
        p = Path(scenario_path)
        if not p.exists():
            raise FileNotFoundError(f"Suite manifest not found: {scenario_path}")
        d = ScenarioParser.LoadYamlDocument(scenario_path)
        raw_list = d.get("scenarios") or d.get("include_scenarios") or []
        suite_continue_on_failure = bool(d.get("continue_on_failure", False))
        scenarios_list = []

        for item in raw_list:
            if isinstance(item, str):
                scenarios_list.append({
                    "file": item,
                    "use_macro": False,
                    "save_macro": False,
                    "continue_on_failure": suite_continue_on_failure
                })
            elif isinstance(item, dict):
                file_path = item.get("file") or item.get("scenario") or item.get("path", "")
                scenarios_list.append({
                    "file": file_path,
                    "use_macro": bool(item.get("use_macro", False)),
                    "save_macro": bool(item.get("save_macro", False)),
                    "continue_on_failure": bool(item.get("continue_on_failure", suite_continue_on_failure))
                })

        return {
            "name": d.get("name", p.stem),
            "description": d.get("description", ""),
            "continue_on_failure": suite_continue_on_failure,
            "scenarios": scenarios_list
        }

    @staticmethod
    def LoadTestScenario(scenario_path: str) -> Dict[str, Any]:
        """[Function] Loads scenario YAML enforcing 'steps' block presence and expanding included sub-scenarios."""
        p = Path(scenario_path)
        if not p.exists():
            raise FileNotFoundError(f"Scenario not found: {scenario_path}")
        d = ScenarioParser.LoadYamlDocument(scenario_path)
        if not isinstance(d, dict) or "steps" not in d:
            raise ValueError(f"Invalid scenario in {scenario_path}: missing 'steps' block.")
        
        expanded_steps = ScenarioParser.ExpandIncludedScenarioSteps(d["steps"], base_dir=p.parent)
        d["steps"] = ScenarioParser.ResolveEnvironmentVariables(expanded_steps)
        d["continue_on_failure"] = bool(d.get("continue_on_failure", False))
        return d

    @staticmethod
    def ExpandIncludedScenarioSteps(steps: List[Dict[str, Any]], base_dir: Path) -> List[Dict[str, Any]]:
        """[Function] Recursively expands steps with type 'include_scenario' or 'run_scenario'."""
        res = []
        for step in steps:
            stype = step.get("type")
            if stype in ("include_scenario", "run_scenario"):
                sub_path = step.get("scenario") or step.get("file") or step.get("path")
                if sub_path:
                    resolved_path = Path(sub_path)
                    if not resolved_path.is_absolute():
                        candidate = base_dir / sub_path
                        if candidate.exists():
                            resolved_path = candidate

                    if resolved_path.exists():
                        sub_data = ScenarioParser.LoadTestScenario(str(resolved_path))
                        res.extend(sub_data.get("steps", []))
                    else:
                        res.append(step)
            else:
                res.append(step)
        return res

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
