import logging
import re
from io import StringIO
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from logger.config import LoggerConfig
from logger.custom_logger import ColoredFormatter, CustomLogger


# Fixture to set up environment variables and a temporary log directory.
@pytest.fixture
def temp_log_dir(tmp_path):
    # Use a temporary directory for logs.
    log_dir = tmp_path / "logs"
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
