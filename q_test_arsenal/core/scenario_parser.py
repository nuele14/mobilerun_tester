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
    def LoadTestScenario(scenario_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """[Function] Loads scenario YAML enforcing 'steps' block presence and expanding included sub-scenarios."""
        p = Path(scenario_path)
        if not p.exists():
            raise FileNotFoundError(f"Scenario not found: {scenario_path}")
        d = ScenarioParser.LoadYamlDocument(scenario_path)
        if not isinstance(d, dict) or "steps" not in d:
            raise ValueError(f"Invalid scenario in {scenario_path}: missing 'steps' block.")
        
        expanded_steps = ScenarioParser.ExpandIncludedScenarioSteps(d["steps"], base_dir=p.parent, config=config)
        d["steps"] = ScenarioParser.ResolveEnvironmentVariables(expanded_steps, config=config)
        d["continue_on_failure"] = bool(d.get("continue_on_failure", False))
        return d

    @staticmethod
    def ExpandIncludedScenarioSteps(steps: List[Dict[str, Any]], base_dir: Path, config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
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
                        sub_data = ScenarioParser.LoadTestScenario(str(resolved_path), config=config)
                        res.extend(sub_data.get("steps", []))
                    else:
                        res.append(step)
            else:
                res.append(step)
        return res

    @staticmethod
    def LoadEnvironmentFile(env_path: str = "scenarios/env.yaml") -> Dict[str, Any]:
        """[Function] Loads test environment variables from scenarios/env.yaml."""
        p = Path(env_path)
        if not p.exists():
            return {}
        return ScenarioParser.LoadYamlDocument(str(p))

    @staticmethod
    def ExtractReferencedVariables(steps: List[Dict[str, Any]]) -> List[str]:
        """[Function] Finds all unique ${VAR_NAME} placeholders referenced in scenario steps."""
        import re
        vars_found = set()

        def _scan(obj: Any):
            if isinstance(obj, str):
                for match in re.findall(r"\$\{([^}]+)\}", obj):
                    vars_found.add(match)
            elif isinstance(obj, dict):
                for v in obj.values():
                    _scan(v)
            elif isinstance(obj, list):
                for item in obj:
                    _scan(item)

        for step in steps:
            _scan(step)
        return sorted(list(vars_found))

    @staticmethod
    def ValidateScenarioEnvironmentVariables(steps: List[Dict[str, Any]], config: Dict[str, Any] = None, env_path: str = "scenarios/env.yaml") -> List[str]:
        """[Function] Returns list of missing variable names not found in scenarios/env.yaml, config credentials, or os.environ."""
        referenced = ScenarioParser.ExtractReferencedVariables(steps)
        if not referenced:
            return []

        env_vars = ScenarioParser.LoadEnvironmentFile(env_path)
        credentials = (config or {}).get("credentials", {})

        missing = []
        for var_name in referenced:
            if var_name not in env_vars and var_name not in credentials and var_name not in os.environ:
                missing.append(var_name)

        return missing

    @staticmethod
    def ResolveEnvironmentVariables(steps: List[Dict[str, Any]], config: Dict[str, Any] = None, env_path: str = "scenarios/env.yaml") -> List[Dict[str, Any]]:
        """
        [Function] Replaces ${VAR_NAME} placeholders checking scenarios/env.yaml first,
        falling back to config credentials, and finally process environment variables (os.environ).
        """
        env_vars = ScenarioParser.LoadEnvironmentFile(env_path)
        credentials = (config or {}).get("credentials", {})
        res = []

        def _resolve_val(v: Any) -> Any:
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                var_name = v[2:-1]
                if var_name in env_vars:
                    return str(env_vars[var_name])
                if var_name in credentials:
                    return str(credentials[var_name])
                return os.getenv(var_name, v)
            return v

        for step in steps:
            s = step.copy()
            for key, val in s.items():
                s[key] = _resolve_val(val)
            res.append(s)
        return res

    # Aliases
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        return ScenarioParser.LoadConfigurationFile(config_path)

    @staticmethod
    def load_scenario(scenario_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        return ScenarioParser.LoadTestScenario(scenario_path, config=config)
