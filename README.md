# AutoProd (`autoprod`)

**Small, tested, single-process Python building blocks for common resilience and concurrency patterns.**

[![CI](https://github.com/AAH20/autoprod/actions/workflows/ci.yml/badge.svg)](https://github.com/AAH20/autoprod/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

---

## What this is

`AutoProd` is a small library of correct, independently testable
implementations of patterns most backend services eventually need:

- `CircuitBreaker` — CLOSED → OPEN → HALF-OPEN state machine with a timed
  recovery window.
- `TokenBucketRateLimiter` — thread-safe token bucket, refills continuously
  based on elapsed time.
- `SagasCoordinator` / `SagaStep` — runs an ordered sequence of
  (action, compensate) steps; on failure, runs compensate() for every
  already-executed step in reverse order.
- `BoundedConnectionPool` — caps concurrent connections with a lock-guarded
  counter (not lock-free — the name says what it actually does).
- `OptimisticLockStore` — versioned key/value store that rejects a write if
  the version has moved since it was read.
- `ShardedConsistentHashRing` — consistent hashing with configurable virtual
  nodes per physical node.
- `AutonomousWAF` — a literal keyword/pattern filter for a fixed list of
  known SQLi/XSS/SSRF strings. **Not a real WAF** — see the caveat below.
- `AdaptiveLoadBalancer` — least-connections routing with health-based
  failover.
- `DistributedEventQueue` — in-process pub/sub with retry backoff and a
  dead-letter queue. Despite the name, this does not cross process or
  machine boundaries — see the caveat below.
- `CanaryDeploymentManager` — routes a percentage of traffic to a new
  version and rolls back automatically if its error rate exceeds a
  threshold.
- `SRETelemetryEngine` — tracks latency samples, computes p50/p90/p99, and
  formats a postmortem Markdown document from percentiles it actually
  recorded plus facts the caller supplies (it does not invent a root cause).

## What this is not

- **Not autonomous, not a runtime, not a "substrate."** Every class here is
  a plain Python object you call directly. There is no agent, no
  orchestration layer, no background process.
- **`AutonomousWAF` is a denylist, not a firewall.** It matches a fixed list
  of lowercased literal strings. It has no encoding/obfuscation handling and
  is trivially bypassed by anyone who tries (mixed case with inline
  comments, URL/HTML-entity encoding, alternate SSRF host forms). Use it as
  a cheap first filter, not a security boundary — put a real WAF in front
  of anything internet-facing.
- **`DistributedEventQueue` is in-process.** Subscribers are Python
  callables held in memory; `publish()` calls them synchronously in the
  calling thread. It models the retry/DLQ contract a real broker (SQS,
  Kafka, RabbitMQ) would enforce — it does not replace one.
- **No I/O.** Nothing here talks to a network, disk, or database. It's pure
  in-memory Python, which is why it has zero dependencies and is easy to
  read end to end (~450 lines total across 6 files).

## Install

Not yet published to PyPI. Install from source:

```bash
git clone https://github.com/AAH20/autoprod.git
cd autoprod
pip install -e .
```

## Usage

```python
from autoprod import (
    CircuitBreaker,
    TokenBucketRateLimiter,
    SagasCoordinator,
    SagaStep,
    BoundedConnectionPool,
    ShardedConsistentHashRing,
    CanaryDeploymentManager,
)

# Circuit breaker around a flaky call
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout_s=2.0)
breaker.call(risky_function)

# Consistent hash sharding
ring = ShardedConsistentHashRing(["shard-1", "shard-2", "shard-3"])
target_shard = ring.get_node("user_account_98412")

# SAGA with compensating rollback
coordinator = SagasCoordinator()
coordinator.execute_saga([
    SagaStep("charge", lambda: charge_card(), lambda: refund_card()),
    SagaStep("ship", lambda: ship_order(), lambda: cancel_shipping()),
])

# Canary rollout with automatic rollback on error budget breach
canary = CanaryDeploymentManager(initial_version="v1.0.0")
canary.start_canary("v2.0.0", weight=0.1)
canary.report_status(is_success=True)
```

## Tests

```bash
python -m unittest discover tests -v
```

8/8 pass, and CI runs the same command on every push across Python 3.10–3.12
(see the badge above — it links to real workflow runs, not a static image).

## Architecture

```
autoprod/
├── autoprod/
│   ├── __init__.py            # exports
│   ├── traffic.py             # AutonomousWAF, AdaptiveLoadBalancer
│   ├── distributed_engine.py  # DistributedEventQueue, DeadLetterMessage, ShardedConsistentHashRing
│   ├── resilience.py          # CircuitBreaker, TokenBucketRateLimiter, SagasCoordinator
│   ├── concurrency.py         # OptimisticLockStore, BoundedConnectionPool
│   ├── deployment.py          # CanaryDeploymentManager
│   └── sre_telemetry.py       # SRETelemetryEngine
└── tests/
    └── test_autoprod.py
```

## License

Apache-2.0

## Author

**Ahmed Hassan**
* LinkedIn: [Ahmed Hassan](https://eg.linkedin.com/in/ahmed-hassan-f11)
* Platform: [A2Z SOC](https://a2zsoc.com)
