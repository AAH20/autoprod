import threading
import time
from typing import Dict, Any, Optional, Tuple

class OptimisticLockConflictError(Exception):
    pass

class OptimisticLockStore:
    """
    Optimistic Concurrency Control (OCC) key-value store preventing silent
    checkpoint overwrites across concurrent agent threads.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._store: Dict[str, Tuple[Any, int]] = {} # key -> (val, version)

    def get(self, key: str) -> Tuple[Optional[Any], int]:
        with self._lock:
            return self._store.get(key, (None, 0))

    def update(self, key: str, new_val: Any, expected_version: int) -> int:
        with self._lock:
            current_val, current_ver = self._store.get(key, (None, 0))
            if current_ver != expected_version:
                raise OptimisticLockConflictError(
                    f"Optimistic lock conflict on key '{key}': expected v{expected_version}, found v{current_ver}"
                )
            new_ver = current_ver + 1
            self._store[key] = (new_val, new_ver)
            return new_ver

class LockFreeConnectionPool:
    """
    Bounded connection pool with token-bucket semaphore to prevent downstream
    database exhaustion under thundering-herd traffic spikes.
    """
    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self.active_connections = 0
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        with self._lock:
            if self.active_connections < self.max_connections:
                self.active_connections += 1
                return True
            return False

    def release(self):
        with self._lock:
            if self.active_connections > 0:
                self.active_connections -= 1
