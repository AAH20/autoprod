import time
from typing import Dict, List, Optional, Callable

class CanaryDeploymentManager:
    """
    Automated Canary & Blue-Green deployment controller with real-time
    SLO error budget evaluation and instant automated rollback.
    """
    def __init__(self, initial_version: str = "v1.0.0"):
        self.active_version = initial_version
        self.canary_version: Optional[str] = None
        self.canary_traffic_weight = 0.0 # 0.0 to 1.0 (e.g. 0.1 = 10%)
        self.error_count = 0
        self.total_requests = 0

    def start_canary(self, new_version: str, weight: float = 0.1):
        self.canary_version = new_version
        self.canary_traffic_weight = weight
        self.error_count = 0
        self.total_requests = 0

    def route_request(self, user_id: int) -> str:
        if not self.canary_version or self.canary_traffic_weight <= 0:
            return self.active_version

        # Deterministic hash routing based on user_id
        if (user_id % 100) < (self.canary_traffic_weight * 100):
            return self.canary_version
        return self.active_version

    def report_status(self, is_success: bool, max_error_rate_threshold: float = 0.05) -> bool:
        self.total_requests += 1
        if not is_success:
            self.error_count += 1

        # Evaluate Error Budget
        error_rate = self.error_count / max(self.total_requests, 1)
        if error_rate > max_error_rate_threshold and self.total_requests >= 10:
            # Automated Instant Rollback
            self.rollback(reason=f"Error rate {error_rate:.2%} exceeded threshold {max_error_rate_threshold:.2%}")
            return False
        return True

    def promote_canary(self):
        if self.canary_version:
            self.active_version = self.canary_version
            self.canary_version = None
            self.canary_traffic_weight = 0.0

    def rollback(self, reason: str):
        print(f"[CANARY SRE ROLLBACK TRIGGERED] Reverting to {self.active_version}. Reason: {reason}")
        self.canary_version = None
        self.canary_traffic_weight = 0.0
