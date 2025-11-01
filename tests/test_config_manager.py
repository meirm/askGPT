"""
Unit tests for ConfigManager module
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml
from askgpt.modules.config_manager import (ConfigManager, ModelConfig,
                                    NanoAgentConfig, ProviderConfig,
                                    get_config, get_config_manager)


class TestModelConfig:
    """Test ModelConfig dataclass"""

    def test_model_config_creation(self):
        """Test creating a ModelConfig"""
        model = ModelConfig(
            name="gpt-5",
            aliases=["gpt5", "GPT-5"],
            max_tokens=4096,
            temperature=0.7,
            description="GPT-5 model",
        )

        assert model.name == "gpt-5"
        assert model.aliases == ["gpt5", "GPT-5"]
        assert model.max_tokens == 4096
        assert model.temperature == 0.7
        assert model.description == "GPT-5 model"
        assert model.deprecated is False

    def test_model_config_deprecated(self):
        """Test deprecated model configuration"""
        model = ModelConfig(
            name="old-model",
            deprecated=True,
            deprecation_message="Use new-model instead",
        )

        assert model.deprecated is True
        assert model.deprecation_message == "Use new-model instead"


class TestProviderConfig:
    """Test ProviderConfig dataclass"""

    def test_provider_config_creation(self):
        """Test creating a ProviderConfig"""
        provider = ProviderConfig(
            name="openai",
            api_base="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            known_models=["gpt-5", "gpt-4"],
            allow_unknown_models=True,
            discover_models=False,
        )

        assert provider.name == "openai"
        assert provider.api_base == "https://api.openai.com/v1"
        assert provider.api_key_env == "OPENAI_API_KEY"
        assert provider.known_models == ["gpt-5", "gpt-4"]
        assert provider.allow_unknown_models is True
        assert provider.discover_models is False

    def test_provider_with_models(self):
        """Test provider with model configurations"""
        model1 = ModelConfig(name="model1", max_tokens=1000)
        model2 = ModelConfig(name="model2", temperature=0.5)

        provider = ProviderConfig(
            name="custom", models={"model1": model1, "model2": model2}
        )

        assert len(provider.models) == 2
        assert provider.models["model1"].max_tokens == 1000
        assert provider.models["model2"].temperature == 0.5


class TestNanoAgentConfig:
    """Test NanoAgentConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values (offline-first)"""
        config = NanoAgentConfig()

        assert config.default_provider == "ollama"
        assert config.default_model == "gpt-oss:20b"
        assert config.log_level == "INFO"
        assert config.cache_enabled is True
        assert config.validate_ssl is True
        assert config.max_turns == 20

    def test_config_to_dict(self):
        """Test converting config to dictionary"""
        config = NanoAgentConfig(
            default_provider="ollama", default_model="gpt-oss:20b", log_level="DEBUG"
        )

        config_dict = config.to_dict()

        assert config_dict["default_provider"] == "ollama"
        assert config_dict["default_model"] == "gpt-oss:20b"
        assert config_dict["log_level"] == "DEBUG"

    def test_config_from_dict(self):
        """Test creating config from dictionary"""
        config_dict = {
            "default_provider": "anthropic",
            "default_model": "claude-3-haiku",
            "providers": {
                "anthropic": {
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "known_models": ["claude-3-haiku"],
                    "models": {
                        "claude-3-haiku": {"name": "claude-3-haiku", "max_tokens": 4096}
                    },
                }
            },
        }

        config = NanoAgentConfig.from_dict(config_dict)

        assert config.default_provider == "anthropic"
        assert config.default_model == "claude-3-haiku"
        assert "anthropic" in config.providers
        assert config.providers["anthropic"].api_key_env == "ANTHROPIC_API_KEY"
        assert "claude-3-haiku" in config.providers["anthropic"].models


class TestConfigManager:
    """Test ConfigManager class"""

    def test_default_config_loading(self):
        """Test loading default configuration"""
        manager = ConfigManager()
        config = manager.load_config()

        assert config.default_provider == "openai"
        assert config.default_model == "gpt-5-mini"
        assert "openai" in config.providers
        assert "anthropic" in config.providers
        assert "ollama" in config.providers

    def test_config_file_loading_yaml(self):
        """Test loading configuration from YAML file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "default_provider": "custom",
                    "default_model": "custom-model",
                    "log_level": "DEBUG",
                },
                f,
            )
            temp_path = Path(f.name)

        try:
            manager = ConfigManager(config_path=temp_path)
            config = manager.load_config()

            assert config.default_provider == "custom"
            assert config.default_model == "custom-model"
            assert config.log_level == "DEBUG"
        finally:
            temp_path.unlink()

    def test_config_file_loading_json(self):
        """Test loading configuration from JSON file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "default_provider": "json-provider",
                    "default_model": "json-model",
                    "cache_ttl": 7200,
                },
                f,
            )
            temp_path = Path(f.name)

        try:
            manager = ConfigManager(config_path=temp_path)
            config = manager.load_config()

            assert config.default_provider == "json-provider"
            assert config.default_model == "json-model"
            assert config.cache_ttl == 7200
        finally:
            temp_path.unlink()

    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables"""
        with patch.dict(
            os.environ,
            {
                "ASKGPT_DEFAULT_PROVIDER": "env-provider",
                "ASKGPT_DEFAULT_MODEL": "env-model",
                "ASKGPT_LOG_LEVEL": "WARNING",
                "ASKGPT_CACHE_TTL": "1800",
                "ASKGPT_PROVIDER_OLLAMA_API_BASE": "http://custom:11434",
            },
        ):
            manager = ConfigManager()
            config = manager.load_config()

            assert config.default_provider == "env-provider"
            assert config.default_model == "env-model"
            assert config.log_level == "WARNING"
            assert config.cache_ttl == 1800
            assert config.providers["ollama"].api_base == "http://custom:11434"

    def test_config_merging(self):
        """Test configuration merging from multiple sources"""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "default_provider": "file-provider",
                    "log_level": "ERROR",
                    "cache_ttl": 3600,
                },
                f,
            )
            temp_path = Path(f.name)

        try:
            # Set environment variables that should override file
            with patch.dict(
                os.environ,
                {
                    "ASKGPT_DEFAULT_MODEL": "env-model",
                    "ASKGPT_CACHE_TTL": "7200",
                },
            ):
                manager = ConfigManager(config_path=temp_path)
                config = manager.load_config()

                # File overrides default
                assert config.default_provider == "file-provider"
                assert config.log_level == "ERROR"

                # Environment overrides file
                assert config.default_model == "env-model"
                assert config.cache_ttl == 7200
        finally:
            temp_path.unlink()

    def test_project_config_discovery(self):
        """Test finding project configuration file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / ".askgpt" / "config.yaml"
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, "w") as f:
                yaml.dump(
                    {
                        "default_provider": "project-provider",
                        "default_model": "project-model",
                    },
                    f,
                )

            # Change to temp directory
            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir_path)

                manager = ConfigManager()
                config = manager.load_config()

                assert config.default_provider == "project-provider"
                assert config.default_model == "project-model"
            finally:
                os.chdir(original_cwd)

    def test_resolve_model_alias(self):
        """Test model alias resolution"""
        manager = ConfigManager()
        manager.load_config()

        # Test existing aliases
        assert manager.resolve_model_alias("gpt5") == "gpt-5"
        assert manager.resolve_model_alias("gpt5mini") == "gpt-5-mini"
        assert manager.resolve_model_alias("claude3haiku") == "claude-3-haiku-20240307"

        # Test non-alias returns as-is
        assert manager.resolve_model_alias("unknown-model") == "unknown-model"

    def test_is_model_allowed(self):
        """Test checking if model is allowed for provider"""
        manager = ConfigManager()
        manager.load_config()

        # Known models should be allowed
        assert manager.is_model_allowed("openai", "gpt-5-mini") is True
        assert manager.is_model_allowed("anthropic", "claude-3-haiku-20240307") is True

        # Unknown models should be allowed if provider allows them
        assert manager.is_model_allowed("openai", "gpt-6-future") is True
        assert manager.is_model_allowed("ollama", "custom-model") is True

        # Non-existent provider should return False
        assert manager.is_model_allowed("nonexistent", "any-model") is False

    def test_get_provider_config(self):
        """Test getting provider configuration"""
        manager = ConfigManager()
        manager.load_config()

        openai_config = manager.get_provider_config("openai")
        assert openai_config is not None
        assert openai_config.api_key_env == "OPENAI_API_KEY"

        ollama_config = manager.get_provider_config("ollama")
        assert ollama_config is not None
        assert ollama_config.api_base == "http://localhost:11434/v1"

        nonexistent = manager.get_provider_config("nonexistent")
        assert nonexistent is None

    def test_save_user_config(self):
        """Test saving configuration to user config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock the user config directory
            mock_user_dir = Path(tmpdir) / ".askgpt"
            mock_user_file = mock_user_dir / "config.yaml"

            manager = ConfigManager()
            manager.USER_CONFIG_DIR = mock_user_dir
            manager.USER_CONFIG_PATH = mock_user_file

            # Create and save a config
            config = NanoAgentConfig(
                default_provider="saved-provider", default_model="saved-model"
            )
            manager.save_user_config(config)

            # Verify file was created and contains correct data
            assert mock_user_file.exists()

            with open(mock_user_file) as f:
                saved_data = yaml.safe_load(f)

            assert saved_data["default_provider"] == "saved-provider"
            assert saved_data["default_model"] == "saved-model"

    def test_save_project_config(self):
        """Test saving configuration to project config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)

                manager = ConfigManager()
                config = NanoAgentConfig(
                    default_provider="project-saved", log_level="DEBUG"
                )
                manager.save_project_config(config)

                # Verify file was created
                config_file = Path(tmpdir) / ".askgpt.yaml"
                assert config_file.exists()

                with open(config_file) as f:
                    saved_data = yaml.safe_load(f)

                assert saved_data["default_provider"] == "project-saved"
                assert saved_data["log_level"] == "DEBUG"
            finally:
                os.chdir(original_cwd)

    def test_get_config_sources(self):
        """Test getting configuration sources"""
        manager = ConfigManager()
        manager.load_config()

        sources = manager.get_config_sources()
        assert "defaults" in sources

        # With environment variables
        with patch.dict(os.environ, {"ASKGPT_DEFAULT_MODEL": "test"}):
            manager2 = ConfigManager()
            manager2.load_config()
            sources2 = manager2.get_config_sources()
            assert "environment" in sources2


class TestGlobalFunctions:
    """Test global convenience functions"""

    def test_get_config_manager(self):
        """Test getting global ConfigManager instance"""
        manager1 = get_config_manager()
        manager2 = get_config_manager()

        # Should return same instance
        assert manager1 is manager2

    def test_get_config(self):
        """Test getting current configuration"""
        config = get_config()

        assert isinstance(config, NanoAgentConfig)
        assert config.default_provider is not None
        assert config.default_model is not None
