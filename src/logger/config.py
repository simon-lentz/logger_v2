from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


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


class LoggerConfig(BaseModel):
    """Pydantic model for logger configuration.

    Attributes:
        log_dir (Path): Directory where log files will be stored.
        log_level (str): Logging level (e.g., 'DEBUG', 'INFO').
        log_verbose (bool): Whether verbose logging is enabled.
        max_bytes (int): Maximum size (in bytes) for a log file before rotation.
        backup_count (int): Number of backup log files to keep.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        str_min_length=1,
    )

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

    def __init__(self, **data):
        """
        Initializes the configuration model with the provided data. If any validation error occurs
        during initialization, the Pydantic ValidationError is caught and re-raised as a LoggerConfigError.
        """
        try:
            super().__init__(**data)
        except ValidationError as e:
            raise LoggerConfigError(f"Invalid configuration: {e}") from e
