# src/utils/log.py
from __future__ import annotations

import threading
import atexit
from .logger import AsyncLogger, Label
# --- at top of file ---
from pathlib import Path
from datetime import datetime, timezone
import threading


_lock = threading.Lock()
_instance: AsyncLogger | None = None

def configure(**kwargs) -> AsyncLogger:
    """
    Create the global logger once (thread-safe). Subsequent calls are no-ops
    and return the same instance. Call this once in your main entrypoint.
    """
    global _instance

    with _lock:
        if _instance is None:
            _instance = AsyncLogger(**kwargs)
            atexit.register(_instance.close)  # write summary on process exit
        return _instance

def get() -> AsyncLogger:
    """Return the global logger (lazy-create with defaults if not configured)."""
    global _instance
    if _instance is None:
        return configure()  # default AsyncLogger()
    return _instance

def get_current_log_dir():
    return get().root

def shutdown(wait: bool = True) -> None:
    """Explicitly close and drop the global logger (optional)."""
    global _instance
    with _lock:
        if _instance is not None:
            _instance.close(wait=wait)
            _instance = None

class _Proxy:
    """For zero boilerplate: forwards attribute access to the singleton."""
    def __getattr__(self, name: str):
        return getattr(get(), name)

# Import this 'log' anywhere; no need to pass it around.
log = _Proxy()

# Re-export label enum for convenience
__all__ = ["log", "configure", "shutdown", "Label"]
