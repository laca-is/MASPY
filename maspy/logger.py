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
    """Logging handler that saves records on a queue."""
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, *args, **kwargs) -> None:
        if not hasattr(self, "records"):
            super().__init__(*args, **kwargs)
            self.records: list[str] = []

    def emit(self, record: LogRecord) -> None:
        """
        Emit a record.

        Parameters
        ----------
            record : logging.LogRecord
                A record to emit
        """
        self.records.append(self.format(record))

    def get_records(self) -> list[str]:
        """
        Get the log records

        Returns
        -------
            list[str]
                A list of log records
        """
        logs = self.records[:]
        self.records.clear()
        return logs 

class MyJSONFormatter(Formatter):
    """ MASPY Custom JSON formatter """
    def __init__(self, *, fmt_keys: Dict[str, str] | None = None):
        super().__init__()
        self._start_time: float = perf_counter()
        self.fmt_keys: Dict[str, str] = fmt_keys if fmt_keys is not None else {}
    
    @override
    def format(self, record: LogRecord) -> str:
        with Lock():
            desc = self._prepare_log_dict(record)
            return dumps(desc, default=str)
    
    @staticmethod
    def _format_clock(elapsed: float) -> str:
        """
        Format the elapsed time in hours, minutes, seconds, and milliseconds

        Parameters
        ----------
            elapsed : float
                The elapsed time in seconds
        
        Returns
        -------
            str
                The elapsed time in hours, minutes, seconds, and milliseconds
        """
        hours, rem = divmod(elapsed, 3600)
        minutes, rem = divmod(rem, 60)
        seconds, millis = divmod(rem, 1)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{int(millis * 1000):03d}"
    
    def _sanitize(self, val: Any) -> Any:
        """Ensure a value is JSON-safe, stringify if not."""
        try:
            dumps(val)
            return val
        except (TypeError, ValueError):
            return str(val)
    
    def _prepare_log_dict(self, record: LogRecord) -> Dict[str, str | Any]:
        """ 
        Prepare the log dictionary
        
        Parameters
        ----------
            record : logging.LogRecord
                A record to prepare
        
        Returns
        -------
            Dict[str, str | Any]
                The prepared log dictionary
        """
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
                desc[key] = self._sanitize(val)
        
        return desc