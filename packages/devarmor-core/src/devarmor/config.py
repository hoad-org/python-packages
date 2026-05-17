"""Configuration loading with 4-level hierarchy support."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional, cast

import yaml

from .errors import ConfigurationError
from .models import PolicyConfig

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load configuration from 4-level hierarchy.

    Hierarchy (lowest to highest priority):
    1. Code defaults
    2. Master config (~/.devarmor/config.yaml)
    3. Repo config (.devarmor/config.yaml)
    4. Environment variables (DEVARMOR_*)
    """

    DEFAULT_MASTER_CONFIG_DIR = Path.home() / ".devarmor"
    DEFAULT_REPO_CONFIG_DIR = Path(".devarmor")

    def __init__(self, repo_config_dir: Optional[Path] = None, master_config_dir: Optional[Path] = None):
        """Initialize config loader.

        Args:
            repo_config_dir: Path to repo config directory (default: .devarmor)
            master_config_dir: Path to master config directory (default: ~/.devarmor)
        """
        self.repo_config_dir = repo_config_dir or self.DEFAULT_REPO_CONFIG_DIR
        self.master_config_dir = master_config_dir or self.DEFAULT_MASTER_CONFIG_DIR
        self._config_cache: dict[str, Any] = {}

    def load_policy_config(self) -> PolicyConfig:
        """Load policy configuration from hierarchy.

        Returns:
            PolicyConfig: Validated policy configuration

        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Start with code defaults
            config = self._get_code_defaults()

            # Apply master config if exists
            master_config = self._load_master_config()
            if master_config:
                config = self._deep_merge(config, master_config)
                logger.debug("Applied master configuration")

            # Apply repo config if exists
            repo_config = self._load_repo_config()
            if repo_config:
                config = self._deep_merge(config, repo_config)
                logger.debug("Applied repo configuration")

            # Apply environment variables
            env_config = self._load_env_config()
            if env_config:
                config = self._deep_merge(config, env_config)
                logger.debug("Applied environment configuration")

            # Validate and return
            return PolicyConfig(**config)
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Failed to load policy configuration: {str(e)}", details={"error": str(e)})

    def load_json(self, path: Path) -> dict[str, Any]:
        """Load JSON configuration file.

        Args:
            path: Path to JSON file

        Returns:
            Parsed JSON dictionary

        Raises:
            ConfigurationError: If file cannot be loaded
        """
        try:
            if not path.exists():
                raise ConfigurationError(f"Configuration file not found: {path}")
            with open(path) as f:
                return cast(dict[str, Any], json.load(f))
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in {path}: {str(e)}", details={"path": str(path)})

    def load_yaml(self, path: Path) -> dict[str, Any]:
        """Load YAML configuration file.

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML dictionary

        Raises:
            ConfigurationError: If file cannot be loaded
        """
        try:
            if not path.exists():
                raise ConfigurationError(f"Configuration file not found: {path}")
            with open(path) as f:
                data = yaml.safe_load(f)
                return data if data else {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {path}: {str(e)}", details={"path": str(path)})

    def _get_code_defaults(self) -> dict[str, Any]:
        """Get hardcoded default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "version": "1.0.0",
            "cost_control": {
                "enabled": True,
                "global_limit": None,
                "service_limits": {},
                "auto_shutdown_enabled": False,
                "auto_shutdown_threshold": 1.0,
            },
            "security": {
                "enabled": True,
                "require_approval": True,
                "forbidden_patterns": [],
                "allowed_domains": None,
                "block_external_api_calls": False,
            },
            "skill_permissions": {
                "enabled": True,
                "default_permissions": [],
                "skill_allowlist": [],
                "skill_blocklist": [],
                "require_signature_verification": False,
                "max_total_concurrent_skills": 5,
            },
            "custom_policies": {},
        }

    def _load_master_config(self) -> Optional[dict[str, Any]]:
        """Load master configuration from home directory.

        Returns:
            Master config or None if not found
        """
        config_file = self.master_config_dir / "config.yaml"
        if config_file.exists():
            return self.load_yaml(config_file)
        return None

    def _load_repo_config(self) -> Optional[dict[str, Any]]:
        """Load repo configuration from local directory.

        Returns:
            Repo config or None if not found
        """
        config_file = self.repo_config_dir / "config.yaml"
        if config_file.exists():
            return self.load_yaml(config_file)
        return None

    def _load_env_config(self) -> Optional[dict[str, Any]]:
        """Load configuration from environment variables.

        Environment variables follow pattern: DEVARMOR_<PATH>_<TO>_<KEY>=value
        Example: DEVARMOR_COST_CONTROL_ENABLED=true

        Returns:
            Environment config or None if no variables set
        """
        config: dict[str, Any] = {}

        for key, value in os.environ.items():
            if not key.startswith("DEVARMOR_"):
                continue

            # Parse variable path (e.g., COST_CONTROL_ENABLED -> cost_control.enabled)
            path_parts = key[9:].lower().split("_")  # Strip "DEVARMOR_" prefix
            if not path_parts:
                continue

            # Try to parse as JSON for structured values
            try:
                parsed_value: Any = json.loads(value)
            except json.JSONDecodeError:
                # Fallback to string or boolean
                if value.lower() in ("true", "false"):
                    parsed_value = value.lower() == "true"
                else:
                    parsed_value = value

            # Construct nested dictionary
            current = config
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                if not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
            current[path_parts[-1]] = parsed_value

        return config if config else None

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge override into base.

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration with override taking precedence
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result


def load_config(repo_config_dir: Optional[Path] = None) -> PolicyConfig:
    """Load policy configuration using 4-level hierarchy.

    This is the main public interface for configuration loading.

    Args:
        repo_config_dir: Optional custom repo config directory

    Returns:
        Loaded and validated PolicyConfig

    Raises:
        ConfigurationError: If configuration is invalid
    """
    loader = ConfigLoader(repo_config_dir=repo_config_dir)
    return loader.load_policy_config()
