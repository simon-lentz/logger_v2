"""
scraper.internal.logger

This module provides a custom logging configuration for the web scraper project.
It defines:
    - `LoggerConfig`: A configuration class that validates logger-related configuration values.
    - `ColoredFormatter`: A custom logging formatter that injects ANSI color codes into log messages.
    - `CustomLogger`: A custom Logger class that inherits from logging.Logger and is configured using
      a Pydantic LoggerConfig model (loaded from environment variables).
"""

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, ClassVar, Type

from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationError

# Global configuration options for all controller models.
model_config: ConfigDict = ConfigDict(
    extra="forbid",
    validate_assignment=True,
    str_strip_whitespace=True,
    str_min_length=1,
)


class BaseConfig(BaseModel):
    # _error_type is declared as a ClassVar to ensure that it is treated as a class-level
    # attribute rather than as a Pydantic model field. This prevents Pydantic from processing it
    # as part of the model schema and allows subclasses to override _error_type with a custom exception type.
    _error_type: ClassVar[Type[Exception]]  # Override in subclass, never used directly

    def __init__(self, **data):
        """
        Initializes the configuration model with the provided data. If any validation error occurs
        during initialization, the Pydantic ValidationError is caught and re-raised as a custom
        error defined by the subclass's _error_type attribute.

        Note on `self.__class__._error_type`:
            - We use `self.__class__` to dynamically reference the class of the current instance.
              This ensures that if a subclass overrides `_error_type`, the overridden value is used,
              rather than a value from the base class.
            - This pattern leverages the fact that _error_type is a class-level variable (declared with ClassVar)
              and should not be part of the instance's attributes.
        """
        try:
            super().__init__(**data)
        except ValidationError as e:
            # Raise the custom exception defined at the class level by using self.__class__ to
            # look up the _error_type in the subclass.
            raise self.__class__._error_type(f"Invalid configuration: {e}") from e


class LoggerConfigError(Exception):
    """Exception raised when the logger configuration is invalid or missing.

    Attributes:
        message (str): Explanation of the error.
        error (Exception, optional): The original exception that caused this error, if any.
    """

    def __init__(self, message: str, *, error: Exception | None = None):
        """Initialize the LoggerConfigError.

        Args:
            message (str): Explanation of the error.
            error (Exception, optional): The original exception that led to this error.
        """
        self.message = message
        self.error = error
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return a string representation of the exception."""
        if self.error is None:
            return self.message
        return f"{self.message}: {self.error}"

    def __repr__(self) -> str:
        """Return a detailed string representation of the exception."""
        return f"LoggerConfigError(message={self.message!r}, error={self.error!r})"


class LoggerConfig(BaseConfig):
    """Pydantic model for logger configuration.

    Attributes:
        log_dir (Path): Directory where log files will be stored.
        log_level (str): Logging level (e.g., 'DEBUG', 'INFO').
        log_verbose (bool): Whether verbose logging is enabled.
        max_bytes (int): Maximum size (in bytes) for a log file before rotation.
        backup_count (int): Number of backup log files to keep.
    """

    model_config = model_config
    _error_type = LoggerConfigError

    log_dir: Path
    log_level: str
    log_verbose: bool
    max_bytes: int = Field(default=1 * 1024 * 1024)  # 1MB by default.
    backup_count: int = Field(default=0)

    @field_validator("log_dir")
    def ensure_log_dir_exists(cls, v: Path) -> Path:
        """Ensure the log directory exists; create it if it doesn't.

        Args:
            v (Path): The path representing the log directory.
        Returns:
            Path: The validated log directory, guaranteed to exist.
        Raises:
            LoggerConfigError: If the directory cannot be created.
        """
        try:
            v.mkdir(parents=True, exist_ok=True)
            return v
        except OSError as e:
            raise LoggerConfigError(
                f"LoggerConfig validation failed for log_dir: {v}",
                error=e,
            )

    @field_validator("log_level")
    def check_log_level(cls, v: str) -> str:
        """Validate that log_level is one of the allowed values.

        Args:
            v (str): The logging level.

        Returns:
            str: The validated logging level in uppercase.

        Raises:
            LoggerConfigError: If the logging level is not one of the allowed values.
        """
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise LoggerConfigError(
                "LoggerConfig validation failed for log_level",
                error=ValueError(f"log_level must be one of {', '.join(allowed)}"),
            )
        return v


class ColoredFormatter(logging.Formatter):
    """A custom logging formatter that adds ANSI color codes to log level names.

    This formatter enhances log messages by inserting color codes around the log level
    names based on their severity. This is especially useful for console outputs where
    visual cues can help in quickly identifying log messages of different levels.
    """

    COLORS = {
        "DEBUG": "\033[92m",  # Green
        "INFO": "\033[94m",  # Blue
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: Any) -> str:
        """Format the log record by adding color to the log level name.

        Args:
            record (Any): The log record to be formatted.

        Returns:
            str: The formatted log message with the colored log level name.
        """
        levelname = record.levelname
        # Remove any stray reset codes and then get the proper color.
        levelname_stripped = levelname.strip(self.RESET)
        log_color = self.COLORS.get(levelname_stripped, self.RESET)
        record.levelname_colored = f"{log_color}{levelname_stripped}{self.RESET}"
        return super().format(record)


class CustomLogger(logging.Logger):
    """CustomLogger is a subclass of logging.Logger that configures itself using a Pydantic LoggerConfig.

    This logger loads its configuration from environment variables via the LoggerConfig model,
    which validates settings such as log directory, log level, verbosity, and file rotation parameters.
    It then attaches a console handler (with color-coded log levels) and a rotating file handler to itself.

    Args:
        name (str): The name of the logger instance.
    """

    def __init__(self, name: str, cfg: LoggerConfig) -> None:

        # Convert the log level string (already validated) to its numeric value.
        self.log_level = logging._nameToLevel.get(cfg.log_level, logging.INFO)
        # Create the log file path using the current date and time.
        self.log_file = cfg.log_dir / f"{datetime.now():%Y-%m-%d_%H%M%S}.log"
        self.verbose = cfg.log_verbose
        self.max_bytes = cfg.max_bytes
        self.backup_count = cfg.backup_count

        # Initialize the base Logger with the proper level.
        super().__init__(name, level=self.log_level)

        # Set up the console and file handlers on this logger instance.
        self._setup_logging()

        # Prevent log messages from propagating to the root logger (avoids duplicates).
        self.propagate = False

    def _setup_logging(self) -> None:
        """Configure this logger with console and rotating file handlers."""
        # Formatter for console logs (with colors).
        console_formatter = ColoredFormatter(
            "%(asctime)s [%(levelname_colored)s] %(name)s:%(lineno)d: %(message)s"
        )
        # Standard formatter for file logs.
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
        )

        # Create and configure the console handler.
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(console_formatter)

        # Create and configure the rotating file handler.
        file_handler = RotatingFileHandler(
            filename=str(self.log_file),
            mode="a",
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(file_formatter)

        # Attach the handlers to this logger instance.
        self.addHandler(console_handler)
        self.addHandler(file_handler)
