"""Tests for configuration loading."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from devarmor.config import ConfigLoader
from devarmor.errors import ConfigurationError
from devarmor.models import PolicyConfig


class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_code_defaults(self) -> None:
        """Test that code defaults are available."""
        loader = ConfigLoader()
        defaults = loader._get_code_defaults()

        assert defaults["version"] == "1.0.0"
        assert "cost_control" in defaults
        assert "security" in defaults
        assert "skill_permissions" in defaults

    def test_load_master_config_not_found(self, tmp_path: Path) -> None:
        """Test loading master config when file doesn't exist."""
        loader = ConfigLoader(master_config_dir=tmp_path)
        config = loader._load_master_config()

        assert config is None

    def test_load_master_config_yaml(self, tmp_path: Path) -> None:
        """Test loading master config from YAML."""
        config_dir = tmp_path / ".devarmor"
        config_dir.mkdir()

        config_file = config_dir / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "cost_control": {
                        "enabled": False,
                    }
                }
            )
        )

        loader = ConfigLoader(master_config_dir=config_dir)
        config = loader._load_master_config()

        assert config is not None
        assert config["cost_control"]["enabled"] is False

    def test_load_repo_config_not_found(self, tmp_path: Path) -> None:
        """Test loading repo config when file doesn't exist."""
        loader = ConfigLoader(repo_config_dir=tmp_path)
        config = loader._load_repo_config()

        assert config is None

    def test_load_repo_config_yaml(self, tmp_path: Path) -> None:
        """Test loading repo config from YAML."""
        config_dir = tmp_path / ".devarmor"
        config_dir.mkdir()

        config_file = config_dir / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "security": {
                        "require_approval": False,
                    }
                }
            )
        )

        loader = ConfigLoader(repo_config_dir=config_dir)
        config = loader._load_repo_config()

        assert config is not None
        assert config["security"]["require_approval"] is False

    def test_load_env_config_simple(self, monkeypatch) -> None:
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("DEVARMOR_COST_CONTROL_ENABLED", "false")
        monkeypatch.setenv("DEVARMOR_SECURITY_REQUIRE_APPROVAL", "true")

        loader = ConfigLoader()
        config = loader._load_env_config()

        assert config is not None
        assert config["cost_control"]["enabled"] is False
        assert config["security"]["require_approval"] is True

    def test_load_env_config_none(self, monkeypatch) -> None:
        """Test loading config when no env vars are set."""
        # Clear any existing DEVARMOR_ vars
        for key in list(os.environ.keys()):
            if key.startswith("DEVARMOR_"):
                monkeypatch.delenv(key)

        loader = ConfigLoader()
        config = loader._load_env_config()

        assert config is None or len(config) == 0

    def test_deep_merge(self) -> None:
        """Test deep merging of configurations."""
        loader = ConfigLoader()

        base = {
            "level1": {
                "level2": {"a": 1, "b": 2},
                "c": 3,
            },
            "d": 4,
        }

        override = {
            "level1": {
                "level2": {"a": 999},
                "e": 5,
            },
            "f": 6,
        }

        result = loader._deep_merge(base, override)

        assert result["level1"]["level2"]["a"] == 999  # Overridden
        assert result["level1"]["level2"]["b"] == 2  # Unchanged
        assert result["level1"]["c"] == 3  # Unchanged
        assert result["level1"]["e"] == 5  # New
        assert result["d"] == 4  # Unchanged
        assert result["f"] == 6  # New

    def test_load_json_success(self, tmp_path: Path) -> None:
        """Test loading JSON file."""
        json_file = tmp_path / "config.json"
        data = {"test": "value", "number": 42}
        json_file.write_text(json.dumps(data))

        loader = ConfigLoader()
        result = loader.load_json(json_file)

        assert result == data

    def test_load_json_not_found(self, tmp_path: Path) -> None:
        """Test loading JSON file that doesn't exist."""
        json_file = tmp_path / "nonexistent.json"

        loader = ConfigLoader()
        with pytest.raises(ConfigurationError, match="not found"):
            loader.load_json(json_file)

    def test_load_json_invalid(self, tmp_path: Path) -> None:
        """Test loading invalid JSON file."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{invalid json")

        loader = ConfigLoader()
        with pytest.raises(ConfigurationError, match="Invalid JSON"):
            loader.load_json(json_file)

    def test_load_yaml_success(self, tmp_path: Path) -> None:
        """Test loading YAML file."""
        yaml_file = tmp_path / "config.yaml"
        data = {"test": "value", "number": 42}
        yaml_file.write_text(yaml.dump(data))

        loader = ConfigLoader()
        result = loader.load_yaml(yaml_file)

        assert result == data

    def test_load_yaml_not_found(self, tmp_path: Path) -> None:
        """Test loading YAML file that doesn't exist."""
        yaml_file = tmp_path / "nonexistent.yaml"

        loader = ConfigLoader()
        with pytest.raises(ConfigurationError, match="not found"):
            loader.load_yaml(yaml_file)

    def test_load_yaml_invalid(self, tmp_path: Path) -> None:
        """Test loading invalid YAML file."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("{ invalid: yaml: content: }")

        loader = ConfigLoader()
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            loader.load_yaml(yaml_file)

    def test_load_policy_config_defaults(self) -> None:
        """Test loading policy config with just defaults."""
        loader = ConfigLoader(repo_config_dir=Path("/nonexistent"))

        config = loader.load_policy_config()

        assert config.version == "1.0.0"
        assert isinstance(config, PolicyConfig)
        assert config.cost_control.enabled is True
        assert config.security.enabled is True

    def test_load_policy_config_with_master_and_repo(self) -> None:
        """Test loading policy config with master and repo config."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create master config
            master_dir = tmp_path / "master"
            master_dir.mkdir()
            master_config = master_dir / "config.yaml"
            master_config.write_text(yaml.dump({"cost_control": {"enabled": False}}))

            # Create repo config
            repo_dir = tmp_path / "repo"
            repo_dir.mkdir()
            repo_config = repo_dir / "config.yaml"
            repo_config.write_text(yaml.dump({"security": {"require_approval": False}}))

            loader = ConfigLoader(master_config_dir=master_dir, repo_config_dir=repo_dir)
            config = loader.load_policy_config()

            assert config.cost_control.enabled is False  # From master
            assert config.security.require_approval is False  # From repo

    def test_config_hierarchy_priority(self, monkeypatch) -> None:
        """Test that configuration hierarchy respects priority."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create master config
            master_dir = tmp_path / "master"
            master_dir.mkdir()
            master_config = master_dir / "config.yaml"
            master_config.write_text(yaml.dump({"cost_control": {"enabled": False}}))

            # Create repo config that overrides master
            repo_dir = tmp_path / "repo"
            repo_dir.mkdir()
            repo_config = repo_dir / "config.yaml"
            repo_config.write_text(yaml.dump({"cost_control": {"enabled": True}}))

            # Set env var to override repo
            monkeypatch.setenv("DEVARMOR_COST_CONTROL_ENABLED", "false")

            loader = ConfigLoader(master_config_dir=master_dir, repo_config_dir=repo_dir)
            config = loader.load_policy_config()

            # Env var should have highest priority
            assert config.cost_control.enabled is False

    def test_load_policy_config_invalid_version(self) -> None:
        """Test that invalid policy config version is rejected."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = tmp_path / ".devarmor"
            config_dir.mkdir()

            config_file = config_dir / "config.yaml"
            config_file.write_text(yaml.dump({"version": "invalid"}))

            loader = ConfigLoader(repo_config_dir=config_dir)

            with pytest.raises(ConfigurationError):
                loader.load_policy_config()


class TestLoadConfigFunction:
    """Test the load_config convenience function."""

    def test_load_config_returns_policy_config(self) -> None:
        """Test that load_config returns PolicyConfig."""
        config = PolicyConfig()
        assert isinstance(config, PolicyConfig)

    def test_load_config_with_custom_dir(self) -> None:
        """Test load_config with custom directory."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = tmp_path / ".devarmor"
            config_dir.mkdir()

            config_file = config_dir / "config.yaml"
            config_file.write_text(yaml.dump({"cost_control": {"enabled": False}}))

            from devarmor.config import load_config

            config = load_config(repo_config_dir=config_dir)

            assert config.cost_control.enabled is False
