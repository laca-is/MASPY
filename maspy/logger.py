from logging import Formatter, LogRecord, Handler
from json import dumps
from threading import Lock
from datetime import datetime, timezone
from typing import Dict, Any
from typing import override
from time import perf_counter

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

class QueueListener(Handler):
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, *args, **kwargs):
        if not hasattr(self, "records"):
            super().__init__(*args, **kwargs)
            self.records = []

    def emit(self, record):
        self.records.append(self.format(record))

    def get_records(self):
        logs = self.records[:]
        self.records.clear()
        return logs 

class MyJSONFormatter(Formatter):
    def __init__(self, *, fmt_keys: Dict[str, str] | None = None):
        super().__init__()
        self._start_time = perf_counter()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}
    
    @override
    def format(self, record: LogRecord) -> str:
        with Lock():
            desc = self._prepare_log_dict(record)
            return dumps(desc, default=str)
    
    @staticmethod
    def _format_clock(elapsed: float) -> str:
        hours, rem = divmod(elapsed, 3600)
        minutes, rem = divmod(rem, 60)
        seconds, millis = divmod(rem, 1)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{int(millis * 1000):03d}"
    
    def _prepare_log_dict(self, record: LogRecord) -> Dict[str, str | Any]:
        elapsed = perf_counter() - self._start_time
        clock = self._format_clock(elapsed)
        always_fields = {
            "desc": record.getMessage(),
            "system_time": clock,
            #"timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
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