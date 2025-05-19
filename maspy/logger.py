from logging import Formatter, LogRecord
from json import dumps
from threading import Lock
from datetime import datetime, timezone
from typing import Dict, Any
from typing import override

LOG_RECORD_BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}

class MyJSONFormatter(Formatter):
    def __init__(self, *, fmt_keys: Dict[str, str] | None = None):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}
    
    @override
    def format(self, record: LogRecord) -> str:
        with Lock():
            desc = self._prepare_log_dict(record)
            return dumps(desc, default=str)
    
    def _prepare_log_dict(self, record: LogRecord) -> Dict[str, str | Any]:
        always_fields = {
            "desc": record.getMessage(),
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)
        
        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)
        
        desc = {
            key: msg_val 
            if (msg_val := always_fields.pop(val, None)) is not None
            else getattr(record, val)
            for key, val in self.fmt_keys.items()
        }
        desc.update(always_fields)
        
        for key, val in record.__dict__.items():
            if key not in LOG_RECORD_BUILTIN_ATTRS:
                desc[key] = val
        
        return desc