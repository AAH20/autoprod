"""
AutoProd: small, tested, single-process Python building blocks for common
resilience and concurrency patterns (circuit breaker, rate limiter, SAGA
compensation, bounded connection pool, optimistic locking, consistent hash
sharding, canary rollout, in-process pub/sub with a DLQ).

None of these talk to a network, a database, or another process. They are
correct implementations of well-known patterns you wire into your own
infrastructure — not a runtime, not autonomous, and not a substitute for a
real WAF, message broker, or deployment platform.
"""

from .resilience import CircuitBreaker, TokenBucketRateLimiter, SagasCoordinator, SagaStep
from .concurrency import BoundedConnectionPool, OptimisticLockStore, OptimisticLockConflictError
from .sre_telemetry import SRETelemetryEngine
from .traffic import AutonomousWAF, WAFSecurityViolation, AdaptiveLoadBalancer
from .distributed_engine import DistributedEventQueue, ShardedConsistentHashRing, DeadLetterMessage
from .deployment import CanaryDeploymentManager

__version__ = "0.3.0"
__all__ = [
    "CircuitBreaker",
    "TokenBucketRateLimiter",
    "SagasCoordinator",
    "SagaStep",
    "BoundedConnectionPool",
    "OptimisticLockStore",
    "OptimisticLockConflictError",
    "SRETelemetryEngine",
    "AutonomousWAF",
    "WAFSecurityViolation",
    "AdaptiveLoadBalancer",
    "DistributedEventQueue",
    "ShardedConsistentHashRing",
    "DeadLetterMessage",
    "CanaryDeploymentManager",
]
