"""Small allowlisted JSON log format; never serialize request bodies or exceptions."""

import json
import logging


class RequestLogFormatter(logging.Formatter):
    def format(self, record):
        fields = {"event": record.getMessage(), "level": record.levelname}
        for key in ("request_id", "method", "path", "status", "duration_ms", "error_type"):
            value = getattr(record, key, None)
            if value is not None:
                fields[key] = value
        return json.dumps(fields, separators=(",", ":"))


def application_logger():
    logger = logging.getLogger("solarops")
    logger.setLevel(logging.INFO)
    logger.disabled = False
    if not any(isinstance(handler.formatter, RequestLogFormatter) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(RequestLogFormatter())
        logger.addHandler(handler)
    logger.propagate = False
    return logger
