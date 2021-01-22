"""Simple routing table for storing DHT nodes"""
import threading
from dataclasses import asdict
from datetime import datetime
from typing import List, Optional

from dht_node.data_structures import Node, Peer, StoredNode
from dht_node.utils import calculate_distance


class RoutingTable:
    """Simple routing table for storing DHT nodes."""

    def __init__(self, base_id):
        """Called when the routing table is created, sets its attributes"""
        self._base_id = base_id  # hex
        self._lock = threading.Lock()
        self._nodes = {}  # Dict[str, StoredNode]

    def delete_unresponsive_nodes(self) -> None:
        """Delete unresponsive nodes from the routing table"""
        with self._lock:
            self._nodes = {
                node_id: node_data
                for node_id, node_data in self._nodes.items()
                if not node_data.is_unresponsive
            }

    def get_all_nodes(self) -> List[StoredNode]:
        """Get all stored nodes"""
        with self._lock:
            return list(self._nodes.values())

    def get_closest_nodes(self, node_id: str) -> List[StoredNode]:
        """Get up to 7 closest nodes to the given node id"""
        with self._lock:
            return sorted(
                self._nodes.values(),
                key=lambda n: calculate_distance(node_id, n.id),
            )[:7]

    def get_peers(self, info_hash: str) -> List[Peer]:
        """Get all stored peers for the given info hash"""
        found_peers = []

        with self._lock:
            for node in self._nodes.values():
                for peer in node.peers:
                    if peer.info_hash == info_hash:
                        found_peers.append(peer)

        return found_peers

    def save_node(self, node: Node, communicated: Optional[datetime] = None):
        """Save node to the routing table"""
        with self._lock:
            # We want to process all nodes, except the base one
            if node.id != self._base_id:
                if node.id in self._nodes and communicated:
                    # Node is present - just update its communication time
                    self._nodes[node.id].communicated = communicated

                else:
                    # Node is absent - calculate the distance
                    distance = calculate_distance(self._base_id, node.id)

                    # Add the node if it belongs to the same XXXX
                    # namespace or the routing table is very small
                    if distance <= 36 or len(self._nodes) < 7:
                        self._nodes[node.id] = StoredNode(
                            added=datetime.now(),
                            communicated=communicated,
                            distance=distance,
                            peers=set(),
                            **asdict(node),
                        )

    def save_peer(self, peer: Peer, node_id: str) -> None:
        """Save peer to the routing table"""
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].peers.add(peer)
