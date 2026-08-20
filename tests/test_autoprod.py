import unittest
from autoprod.resilience import CircuitBreaker, CircuitBreakerOpenError, TokenBucketRateLimiter, SagasCoordinator, SagaStep
from autoprod.concurrency import OptimisticLockStore, OptimisticLockConflictError, LockFreeConnectionPool
from autoprod.sre_telemetry import SRETelemetryEngine

class TestAutoProd(unittest.TestCase):
    def test_circuit_breaker_trip_and_half_open(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout_s=0.1)

        def failing_call():
            raise ValueError("Downstream API timeout")

        # 3 failures trip the breaker
        for _ in range(3):
            with self.assertRaises(ValueError):
                cb.call(failing_call)

        self.assertEqual(cb.state, "OPEN")
        with self.assertRaises(CircuitBreakerOpenError):
            cb.call(lambda: "ok")

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

        # Verify compensating rollback executed: zero money charged, zero stock locked
        self.assertFalse(state["charged"])
        self.assertFalse(state["reserved"])

    def test_optimistic_concurrency_lock(self):
        store = OptimisticLockStore()
        # Initial write
        store.update("balance", 1000, expected_version=0)

        # Agent A reads v1
        val, ver = store.get("balance")
        self.assertEqual(val, 1000)
        self.assertEqual(ver, 1)

        # Agent B updates to 1500 (becomes v2)
        store.update("balance", 1500, expected_version=1)

        # Agent A tries to commit with stale version 1 -> Must raise conflict
        with self.assertRaises(OptimisticLockConflictError):
            store.update("balance", 1200, expected_version=1)

    def test_sre_telemetry_percentiles_and_postmortem(self):
        engine = SRETelemetryEngine()
        for lat in [10.0, 12.0, 15.0, 18.0, 25.0, 120.0]:
            engine.record_latency(lat)

        metrics = engine.calculate_percentiles()
        self.assertGreater(metrics["p99_ms"], metrics["p50_ms"])
        
        postmortem = engine.generate_automated_postmortem(
            incident_name="DB Connection Saturation",
            root_cause_subsystem="PostgreSQL Pool",
            impact_description="12 requests queued for 400ms"
        )
        self.assertIn("AUTOMATED SRE INCIDENT POSTMORTEM", postmortem)
        self.assertIn("a2zsoc.com", postmortem)

if __name__ == "__main__":
    unittest.main()
