import contextvars
import logging
import sys
from urllib.parse import parse_qsl, urlencode

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="no-request-id"
)

SENSITIVE_KEYS: set[str] = {
    "password",
    "repeat_password",
    "token",
    "access_token",
    "jwt_secret_key",
    "secret",
    "authorization",
    "lambda_callback_secret",
}


# Inject request_id into log records
class RequestIDLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


# Mask sensitive query parameters in logs
def sanitize_query_string(query_string: str) -> str:
    if not query_string:
        return ""
    pairs = parse_qsl(query_string, keep_blank_values=True)
    sanitized: list[tuple[str, str]] = []
    for k, v in pairs:
        if k.lower() in SENSITIVE_KEYS:
            sanitized.append((k, "******"))
        else:
            sanitized.append((k, v))
    return urlencode(sanitized)


# Get logger with request_id formatting
def get_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(RequestIDLogFilter())
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
