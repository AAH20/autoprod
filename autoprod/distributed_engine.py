import time
import threading
import hashlib
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass

@dataclass
class DeadLetterMessage:
    msg_id: str
    payload: Any
    failure_reason: str
    timestamp: float

class DistributedEventQueue:
    """
    In-memory Pub/Sub and Dead-Letter Queue (DLQ) engine with exponential backoff,
    max retry bounds, and poison-pill message isolation.
    """
    def __init__(self, max_retries: int = 3):
        self.subscribers: Dict[str, List[Callable[[Any], None]]] = {}
        self.dlq: List[DeadLetterMessage] = []
        self.max_retries = max_retries
        self._lock = threading.Lock()

    def subscribe(self, topic: str, handler: Callable[[Any], None]):
        with self._lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            self.subscribers[topic].append(handler)

    def publish(self, topic: str, msg_id: str, payload: Any):
        with self._lock:
            handlers = list(self.subscribers.get(topic, []))

        for handler in handlers:
            success = False
            for attempt in range(self.max_retries):
                try:
                    handler(payload)
                    success = True
                    break
                except Exception as e:
                    time.sleep(0.001 * (2 ** attempt)) # exponential backoff
            
            if not success:
                # Push to Dead Letter Queue (DLQ)
                with self._lock:
                    self.dlq.append(DeadLetterMessage(
                        msg_id=msg_id,
                        payload=payload,
                        failure_reason=f"Exceeded {self.max_retries} retries",
                        timestamp=time.time()
                    ))

class ShardedConsistentHashRing:
    """
    Consistent Hash Ring for dynamic database sharding and partitioning,
    distributing keys across virtual nodes with minimal re-shuffling during scale-out.
    """
    def __init__(self, nodes: List[str], vnodes_per_node: int = 10):
        self.vnodes_per_node = vnodes_per_node
        self.ring: Dict[int, str] = {} # hash_val -> physical_node
        self.sorted_hashes: List[int] = []
        for node in nodes:
            self.add_node(node)

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)

    def add_node(self, node: str):
        for v in range(self.vnodes_per_node):
            v_key = f"{node}-vnode-{v}"
            h = self._hash(v_key)
            self.ring[h] = node
        self.sorted_hashes = sorted(self.ring.keys())

    def get_node(self, partition_key: str) -> str:
        if not self.ring:
            raise RuntimeError("No nodes in hash ring")
        h = self._hash(partition_key)
        
        # Binary search for the first node with hash >= h
        for ring_hash in self.sorted_hashes:
            if ring_hash >= h:
                return self.ring[ring_hash]
        # Wrap around to the first node
        return self.ring[self.sorted_hashes[0]]
