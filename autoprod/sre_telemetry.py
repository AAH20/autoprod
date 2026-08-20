import time
import math
from typing import List, Dict, Any

class SRETelemetryEngine:
    """
    Latency percentile tracker and postmortem document formatter.

    generate_postmortem() formats a Markdown document from facts the caller
    supplies plus the percentiles this instance has actually recorded. It
    does not diagnose root cause, detect a trigger, or verify a mitigation —
    those must come from the caller (or an external incident-response
    process) as real inputs, not be invented by this class.
    """
    def __init__(self):
        self.latencies_ms: List[float] = []

    def record_latency(self, latency_ms: float):
        self.latencies_ms.append(latency_ms)

    def calculate_percentiles(self) -> Dict[str, float]:
        if not self.latencies_ms:
            return {"p50": 0.0, "p90": 0.0, "p99": 0.0, "tail_ratio": 1.0}

        sorted_lat = sorted(self.latencies_ms)
        n = len(sorted_lat)

        p50 = sorted_lat[int(0.50 * n)]
        p90 = sorted_lat[int(0.90 * n)]
        p99 = sorted_lat[min(int(0.99 * n), n - 1)]
        tail_ratio = p99 / max(p50, 0.001)

        return {
            "p50_ms": p50,
            "p90_ms": p90,
            "p99_ms": p99,
            "tail_stability_ratio": round(tail_ratio, 2)
        }

    def generate_postmortem(
        self,
        incident_name: str,
        root_cause_subsystem: str,
        impact_description: str,
        trigger: str,
        mitigation: str,
        resolution: str,
    ) -> str:
        """
        Format a postmortem Markdown document. `trigger`, `mitigation`, and
        `resolution` must describe what actually happened for this incident —
        the caller is responsible for their accuracy; this method only
        formats them alongside the latency percentiles this instance has
        recorded.
        """
        date_str = time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())
        percentiles = self.calculate_percentiles()
        return f"""# SRE Incident Postmortem

**Incident:** {incident_name}
**Timestamp:** {date_str}
**Root-Cause Subsystem:** `{root_cause_subsystem}`
**Impact:** {impact_description}

---

### 1. Recorded Latency ({len(self.latencies_ms)} samples)
* p50: {percentiles.get('p50_ms', 0.0)} ms
* p90: {percentiles.get('p90_ms', 0.0)} ms
* p99: {percentiles.get('p99_ms', 0.0)} ms

### 2. Incident Timeline
* **Trigger:** {trigger}
* **Mitigation:** {mitigation}
* **Resolution:** {resolution}
"""
