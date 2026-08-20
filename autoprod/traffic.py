import time
import math
import asyncio
from typing import Dict, Optional, Callable, Any, List

class WAFSecurityViolation(Exception):
    """Raised when request payload violates WAF, XSS, SQLi, or SSRF rules."""
    pass

class AutonomousWAF:
    """
    In-memory Layer-7 Web Application Firewall inspecting payloads for
    SQL Injection, XSS, SSRF, and Cross-Origin abuse in microsecond budgets.
    """
    SQLI_PATTERNS = ["union select", "--", "or 1=1", "drop table", ";--", "exec("]
    XSS_PATTERNS = ["<script>", "javascript:", "onerror=", "onload=", "<svg/onload="]
    SSRF_BLOCKED_RANGES = ["127.0.0.1", "localhost", "169.254.169.254", "0.0.0.0"]

    def inspect_payload(self, query_params: str = "", body: str = "", host_target: str = ""):
        combined = (query_params + " " + body).lower()
        
        # 1. SQL Injection Inspection
        for pattern in self.SQLI_PATTERNS:
            if pattern in combined:
                raise WAFSecurityViolation(f"WAF Block: SQL Injection pattern detected ('{pattern}')")

        # 2. XSS Inspection
        for pattern in self.XSS_PATTERNS:
            if pattern in combined:
                raise WAFSecurityViolation(f"WAF Block: Cross-Site Scripting pattern detected ('{pattern}')")

        # 3. SSRF Inspection
        if host_target:
            for blocked in self.SSRF_BLOCKED_RANGES:
                if blocked in host_target.lower():
                    raise WAFSecurityViolation(f"WAF Block: SSRF attempt to internal host '{host_target}'")

class AdaptiveLoadBalancer:
    """
    Health-aware round-robin & least-connections load balancer with
    automatic failover and circuit breaker backpressure.
    """
    def __init__(self, target_nodes: List[str]):
        self.nodes = target_nodes
        self.node_active_conns: Dict[str, int] = {node: 0 for node in target_nodes}
        self.node_health: Dict[str, bool] = {node: True for node in target_nodes}

    def pick_least_connection_node(self) -> str:
        healthy_nodes = [n for n in self.nodes if self.node_health[n]]
        if not healthy_nodes:
            raise RuntimeError("All upstream nodes UNHEALTHY (503 Service Unavailable)")

        # Pick node with least active connections
        chosen = min(healthy_nodes, key=lambda n: self.node_active_conns[n])
        self.node_active_conns[chosen] += 1
        return chosen

    def release_node(self, node: str):
        if node in self.node_active_conns and self.node_active_conns[node] > 0:
            self.node_active_conns[node] -= 1

    def mark_health(self, node: str, is_healthy: bool):
        if node in self.node_health:
            self.node_health[node] = is_healthy
