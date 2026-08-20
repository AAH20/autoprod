"""
AutoProd: Autonomous Invariant-Driven Production Runtime & SRE Substrate.
"""

from .resilience import CircuitBreaker, TokenBucketRateLimiter, SagasCoordinator, SagaStep
from .concurrency import LockFreeConnectionPool, OptimisticLockStore, OptimisticLockConflictError
from .sre_telemetry import SRETelemetryEngine
from .traffic import AutonomousWAF, WAFSecurityViolation, AdaptiveLoadBalancer
from .distributed_engine import DistributedEventQueue, ShardedConsistentHashRing, DeadLetterMessage
from .deployment import CanaryDeploymentManager

__version__ = "0.2.0"
__all__ = [
    "CircuitBreaker",
    "TokenBucketRateLimiter",
    "SagasCoordinator",
    "SagaStep",
    "LockFreeConnectionPool",
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
