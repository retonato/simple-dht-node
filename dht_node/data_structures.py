"""Data structures used by DHT node and routing table"""
import struct
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Set


@dataclass
class Node:  # pylint: disable=invalid-name
    """Base data container for DHT nodes"""

    id: str  # hex
    ip: str
    port: int

    @property
    def compact_info(self):
        """Compact node info, as described in BEP 5"""
        return struct.pack(
            "!20s4sH",
            bytes.fromhex(self.id),
            self.ip.encode("ascii"),
            self.port,
        )


@dataclass
class Peer:
    """Data container for torrent peers / info hashes"""

    info_hash: str
    ip: str  # pylint: disable=invalid-name
    port: int

    def __hash__(self):
        return hash(self.info_hash + self.ip + str(self.port))

    @property
    def compact_info(self):
        """Compact peer info, as described in BEP 5"""
        return struct.pack("!4sH", self.ip.encode("ascii"), self.port)


@dataclass
class StoredNode(Node):
    """Data container for nodes, stored in the routing table"""

    added: datetime
    communicated: Optional[datetime]
    distance: int
    peers: Set[Peer]

    @property
    def is_questionable(self):
        """Nodes, which communicated > 5 minutes ago, are questionable"""
        start_time = self.communicated or self.added
        return datetime.now() > (start_time + timedelta(minutes=5))

    @property
    def is_unresponsive(self):
        """Nodes, which communicated > 15 minutes ago, are unresponsive"""
        start_time = self.communicated or self.added
        return datetime.now() > (start_time + timedelta(minutes=15))


# Other
class Counter:
    """Simple thread safe counter"""

    def __init__(self):
        """Called when the counter is created, sets its attributes"""
        self._lock = threading.Lock()
        self.value = 0

    def increment(self):
        """This method should be used instead of counter += 1"""
        with self._lock:
            self.value += 1

    def reset(self):
        """This method should be used instead of counter = 0"""
        with self._lock:
            self.value = 0
