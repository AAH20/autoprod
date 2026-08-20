import unittest
from autoprod.resilience import CircuitBreaker, CircuitBreakerOpenError, TokenBucketRateLimiter, SagasCoordinator, SagaStep
from autoprod.concurrency import OptimisticLockStore, OptimisticLockConflictError, LockFreeConnectionPool
from autoprod.sre_telemetry import SRETelemetryEngine
from autoprod.traffic import AutonomousWAF, WAFSecurityViolation, AdaptiveLoadBalancer
from autoprod.distributed_engine import DistributedEventQueue, ShardedConsistentHashRing
from autoprod.deployment import CanaryDeploymentManager

class TestAutoProdComprehensive(unittest.TestCase):
    def test_waf_sqli_and_xss_blocking(self):
        waf = AutonomousWAF()
        # Normal request passes
        waf.inspect_payload(query_params="user=123", body="Hello world")
        
        # SQL Injection Blocked
        with self.assertRaises(WAFSecurityViolation):
            waf.inspect_payload(query_params="id=1; DROP TABLE users;--")

        # XSS Blocked
        with self.assertRaises(WAFSecurityViolation):
            waf.inspect_payload(body="<script>alert('pwned')</script>")

        # SSRF Blocked
        with self.assertRaises(WAFSecurityViolation):
            waf.inspect_payload(host_target="http://169.254.169.254/latest/meta-data/")

    def test_load_balancer_least_connections_and_failover(self):
        lb = AdaptiveLoadBalancer(["node-1", "node-2", "node-3"])
        
        # Pick node-1
        n1 = lb.pick_least_connection_node()
        self.assertEqual(n1, "node-1")
        
        # Next picks node-2
        n2 = lb.pick_least_connection_node()
        self.assertEqual(n2, "node-2")

        # Mark node-3 down and verify failover
        lb.mark_health("node-3", False)
        n3 = lb.pick_least_connection_node()
        self.assertIn(n3, ["node-1", "node-2"])

    def test_event_queue_and_dlq_poison_pill_isolation(self):
        eq = DistributedEventQueue(max_retries=2)
        received = []

        def failing_handler(payload):
            raise RuntimeError("Database connection down")

        eq.subscribe("payments", failing_handler)
        eq.publish("payments", msg_id="tx-999", payload={"amount": 500})

        # Message must end up in Dead Letter Queue (DLQ)
        self.assertEqual(len(eq.dlq), 1)
        self.assertEqual(eq.dlq[0].msg_id, "tx-999")

    def test_consistent_hash_sharding(self):
        ring = ShardedConsistentHashRing(["shard-1", "shard-2", "shard-3"], vnodes_per_node=20)
        shard_a = ring.get_node("user-1001")
        shard_b = ring.get_node("user-1002")
        self.assertIn(shard_a, ["shard-1", "shard-2", "shard-3"])
        self.assertIn(shard_b, ["shard-1", "shard-2", "shard-3"])

    def test_canary_deployment_and_auto_rollback(self):
        canary = CanaryDeploymentManager(initial_version="v1.0.0")
        canary.start_canary(new_version="v2.0.0", weight=0.2) # 20% traffic

        # Report 10 failed requests on canary
        for _ in range(12):
            canary.report_status(is_success=False)

        # Invariant: Canary must be rolled back automatically
        self.assertIsNone(canary.canary_version)
        self.assertEqual(canary.active_version, "v1.0.0")

    def test_saga_compensating_rollback(self):
        coordinator = SagasCoordinator()
        state = {"charged": False, "reserved": False}

        step1 = SagaStep(
            name="charge_card",
            action=lambda: state.update({"charged": True}),
            compensate=lambda: state.update({"charged": False})
        )
        step2 = SagaStep(
            name="reserve_inventory",
            action=lambda: state.update({"reserved": True}),
            compensate=lambda: state.update({"reserved": False})
        )
        step3 = SagaStep(
            name="failing_dispatch",
            action=lambda: (_ for _ in ()).throw(RuntimeError("FedEx Gateway Timeout")),
            compensate=lambda: None
        )

        with self.assertRaises(RuntimeError):
            coordinator.execute_saga([step1, step2, step3])

        self.assertFalse(state["charged"])
        self.assertFalse(state["reserved"])

if __name__ == "__main__":
    unittest.main()
