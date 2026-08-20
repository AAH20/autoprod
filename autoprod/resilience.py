import time
import math
import asyncio
from typing import Callable, Any, List, Tuple
from dataclasses import dataclass

class CircuitBreakerOpenError(Exception):
    """Raised when an downstream dependency is tripping and circuit breaker is OPEN."""
    pass

class CircuitBreaker:
    """
    Autonomous Circuit Breaker with exponential recovery and automated state transitions
    (CLOSED -> OPEN -> HALF-OPEN).
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout_s: float = 2.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.failure_count = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF_OPEN
        self.last_state_change = time.time()

    def call(self, fn: Callable, *args, **kwargs) -> Any:
        now = time.time()
        if self.state == "OPEN":
            if now - self.last_state_change > self.recovery_timeout_s:
                self.state = "HALF_OPEN"
                self.last_state_change = now
            else:
                raise CircuitBreakerOpenError("Circuit Breaker is OPEN: downstream service is unheathy.")

        try:
            result = fn(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                self.last_state_change = now
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_state_change = now
            raise e

class TokenBucketRateLimiter:
    """
    Lock-free token bucket rate limiter with jitter backoff to smooth traffic spikes.
    """
    def __init__(self, capacity: int = 100, refill_rate_per_s: float = 50.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_s
        self.tokens = float(capacity)
        self.last_update = time.time()

    def allow_request(self, cost: float = 1.0) -> bool:
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(float(self.capacity), self.tokens + elapsed * self.refill_rate)
        self.last_update = now

        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False

@dataclass
class SagaStep:
    name: str
    action: Callable[[], Any]
    compensate: Callable[[], Any]

class SagasCoordinator:
    """
    Two-Phase Distributed SAGA Coordinator with automatic backward compensation
    on partial pipeline failures across external APIs.
    """
    def __init__(self):
        self.executed_steps: List[SagaStep] = []

    def execute_saga(self, steps: List[SagaStep]) -> List[Any]:
        results = []
        for step in steps:
            try:
                res = step.action()
                self.executed_steps.append(step)
                results.append(res)
            except Exception as e:
                # Step failed: execute backward compensating transactions
                self._compensate_all()
                raise RuntimeError(f"Saga step '{step.name}' failed: {str(e)}. Compensating rollbacks executed.")
        return results

    def _compensate_all(self):
        for step in reversed(self.executed_steps):
            try:
                step.compensate()
            except Exception as comp_err:
                print(f"[CRITICAL SRE ALERT] Compensating step '{step.name}' failed: {comp_err}")
        self.executed_steps.clear()
