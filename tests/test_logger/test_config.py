from pathlib import Path

import pytest

from logger.config import LoggerConfig, LoggerConfigError


def test_logger_config_valid(tmp_path: Path):
    """
    Test that a valid LoggerConfig instance is created successfully.

    Verifies that:
      - The log_level is converted to uppercase.
      - The log directory is created if it does not exist.
      - The default values for max_bytes and backup_count are used.
    """
    # Use a temporary directory for the log directory.
    log_dir = tmp_path / "logs"
    # Ensure the directory does not exist before instantiation.
    assert not log_dir.exists()

    config = LoggerConfig(
        log_dir=log_dir,
        log_level="debug",  # lower case intentionally to test uppercase conversion
        log_verbose=True,
    )
    # Check that the log_level is uppercased.
    assert config.log_level == "DEBUG"
    # Check that the log directory was created.
    assert log_dir.exists()
    # Check that default values are set.
    assert config.max_bytes == 1 * 1024 * 1024
    assert config.backup_count == 0
    # Verify the log_verbose value.
    assert config.log_verbose is True


def test_logger_config_invalid():
    """
    Test that LoggerConfig raises a LoggerConfigError when the configuration is invalid.

    Here, an invalid type is provided for log_dir.
    The BaseConfig constructor catches the Pydantic ValidationError and re-raises it
    as a LoggerConfigError with a message prefixed by "Invalid configuration:".
    """
    with pytest.raises(LoggerConfigError) as exc_info:
        LoggerConfig(
            log_dir=15,  # Invalid type: expecting a Path.
            log_level="debug",
            log_verbose=True,
        )
    # Check that the error message indicates an invalid configuration.
    assert "Invalid configuration:" in str(exc_info.value)


def test_logger_config_invalid_log_level(tmp_path: Path):
    """Test that an invalid log_level raises a LoggerConfigError."""
    log_dir = tmp_path / "logs"
    with pytest.raises(LoggerConfigError) as exc_info:
        LoggerConfig(
            log_dir=log_dir,
            log_level="INVALID_LEVEL",
            log_verbose=False,
        )
    # Check that the exception message mentions the log_level validation failure.
    assert "LoggerConfig validation failed for log_level" in str(exc_info.value)


def test_logger_config_creates_directory(tmp_path: Path):
    """Test that the LoggerConfig ensures the log directory exists."""
    # Use a directory that doesn't exist yet.
    log_dir = tmp_path / "nonexistent_logs"
    config = LoggerConfig(
        log_dir=log_dir,
        log_level="INFO",
        log_verbose=False,
    )
    # The validator should have created the directory.
    assert config.log_dir.exists()


def test_logger_config_defaults(tmp_path: Path):
    """Test that LoggerConfig correctly uses default values for optional fields."""
    log_dir = tmp_path / "logs"
    config = LoggerConfig(
        log_dir=log_dir,
        log_level="WARNING",
        log_verbose=False,
    )
    # Defaults: max_bytes = 1MB, backup_count = 0.
    assert config.max_bytes == 1 * 1024 * 1024
    assert config.backup_count == 0
