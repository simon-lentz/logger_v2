# tests/test_shared/test_logger.py
import logging
import re
from io import StringIO
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from scraper.internal.errors import LoggerConfigError
from scraper.internal.logger import (
    ColoredFormatter,
    CustomLogger,
    LoggerConfig,
)


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


# Fixture to set up environment variables and a temporary log directory.
@pytest.fixture
def temp_log_dir(tmp_path, monkeypatch):
    # Use a temporary directory for logs.
    log_dir = tmp_path / "logs"
    monkeypatch.setenv("LOG_DIR", str(log_dir))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_VERBOSE", "True")
    monkeypatch.setenv("LOG_MAX_BYTES", "1024")  # 1 KB for testing rotation.
    monkeypatch.setenv("LOG_BACKUP_COUNT", "1")
    return log_dir


# Fixture to create a CustomLogger instance.
@pytest.fixture
def custom_logger(tmp_path):
    # Instantiate the custom logger with a test name.
    test_cfg = LoggerConfig(
        log_dir=tmp_path / "logs",
        log_level="DEBUG",
        log_verbose=True,
        max_bytes=1024,  # 1 KB for testing rotation.
        backup_count=2,
    )
    logger = CustomLogger("test_logger", test_cfg)
    yield logger  # Keep the log file for the test session
    logger.log_file.unlink()  # Remove the default log file created by the logger.


def test_custom_logger_configuration(custom_logger):
    """
    Verify that the CustomLogger instance is initialized with:
      - The correct log level.
      - Exactly two handlers (a StreamHandler and a RotatingFileHandler).
      - Propagation disabled.
    """
    assert custom_logger.level == logging.DEBUG
    assert not custom_logger.propagate
    assert len(custom_logger.handlers) == 2

    handler_types = {type(handler) for handler in custom_logger.handlers}
    assert StreamHandler in handler_types
    assert RotatingFileHandler in handler_types


def test_colored_formatter_output():
    """
    Verify that the ColoredFormatter adds ANSI escape codes to the log level.
    For an ERROR level, the ANSI code for red (\033[91m) should appear.
    """
    formatter = ColoredFormatter("%(levelname_colored)s: %(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="An error occurred",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    # Check that ANSI escape sequences for red and reset are present.
    assert "\033[91m" in output
    assert "\033[0m" in output
    # Verify that the log message is present.
    assert "An error occurred" in output


def test_console_logging_output(custom_logger, monkeypatch):
    """
    Verify that the console (StreamHandler) logs messages with ANSI color codes.
    This is done by replacing the handler's stream with a StringIO and checking the output.
    """
    # Identify the console handler.
    console_handler = next(
        (h for h in custom_logger.handlers if isinstance(h, StreamHandler)), None
    )
    assert console_handler is not None

    # Replace its stream with a StringIO for capturing output.
    stream = StringIO()
    console_handler.stream = stream

    # Log a test message.
    custom_logger.info("Test console log")
    console_handler.flush()
    output = stream.getvalue()

    # For INFO level, the ANSI color is blue (\033[94m).
    assert "\033[94m" in output
    assert "Test console log" in output


def test_file_logging_output(custom_logger):
    """
    Verify that the file (RotatingFileHandler) logs messages using the standard formatter
    (i.e., without ANSI escape codes). Read the log file and check the contents.
    """
    # Log a test message.
    custom_logger.warning("Test file log")

    # Get the file path from the logger.
    log_file = Path(custom_logger.log_file)
    # Ensure the log file exists.
    assert log_file.exists()

    # Read the file content.
    content = log_file.read_text(encoding="utf-8")
    # Check that the plain log level "WARNING" appears.
    assert "WARNING" in content
    # Verify that there are no ANSI escape codes.
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    assert not ansi_escape.search(content)


def test_rotating_file_handler_config(custom_logger):
    """
    Verify that the RotatingFileHandler is configured with the correct maxBytes and backupCount.
    """
    file_handler = next(
        (h for h in custom_logger.handlers if isinstance(h, RotatingFileHandler)), None
    )
    assert file_handler is not None
    assert file_handler.maxBytes == custom_logger.max_bytes
    assert file_handler.backupCount == custom_logger.backup_count
