"""Unit tests for structured JSON logging."""
import io
import json
import logging


def _make_logger(name: str, formatter) -> tuple[logging.Logger, io.StringIO]:
    """Create an isolated logger with a StringIO stream handler."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger, stream


def test_json_formatter_produces_valid_json():
    from app.core.logging_config import ApexJsonFormatter

    logger, stream = _make_logger("apex.test.valid_json", ApexJsonFormatter())
    logger.info("hello world")

    output = stream.getvalue().strip()
    assert output, "log output should not be empty"
    record = json.loads(output)
    assert record["message"] == "hello world"


def test_json_formatter_includes_timestamp_and_level():
    from app.core.logging_config import ApexJsonFormatter

    logger, stream = _make_logger("apex.test.fields", ApexJsonFormatter())
    logger.info("check fields")

    record = json.loads(stream.getvalue().strip())
    assert "timestamp" in record
    assert "level" in record
    assert record["level"] == "INFO"


def test_json_formatter_includes_logger_name():
    from app.core.logging_config import ApexJsonFormatter

    logger, stream = _make_logger("apex.test.name_field", ApexJsonFormatter())
    logger.warning("check name")

    record = json.loads(stream.getvalue().strip())
    assert record["logger"] == "apex.test.name_field"
    assert record["level"] == "WARNING"


def test_configure_logging_sets_root_level():
    from app.core.logging_config import configure_logging

    configure_logging(log_level="DEBUG", json_logs=False)
    assert logging.getLogger().level == logging.DEBUG

    # Reset to avoid affecting other tests
    configure_logging(log_level="WARNING", json_logs=False)
