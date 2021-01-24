"""Util functions used by DHT node and routing table classes"""
import logging
import os
import struct
from ipaddress import ip_address
from typing import List, Optional

from .data_structures import Node, StoredNode


def calculate_distance(id_1: str, id_2: str) -> int:
    """Calculate the prefix distance between two node ids"""
    return 40 - len(os.path.commonprefix([id_1, id_2]))


def create_compact_node_info(nodes: List[StoredNode]) -> bytes:
    """Convert StoredNode objects to compact node info string (BEP 5)"""
    return b"".join(node.compact_info for node in nodes)


def get_message_type(message: dict) -> str:
    """TBA"""
    # pylint: disable=too-many-return-statements
    # Request messages
    if message.get(b"y") == b"q":
        if message.get(b"q") == b"announce_peer":
            return "announce_peer_request"
        if message.get(b"q") == b"find_node":
            return "find_node_request"
        if message.get(b"q") == b"get_peers":
            return "get_peers_request"
        if message.get(b"q") == b"ping":
            return "ping_request"
        if message.get(b"q") == b"sample_infohashes":
            return "sample_infohashes"
        if message.get(b"q") == b"vote":  # utorrent
            return "vote"

        logging.debug("Unexpected request type: %r", message)
        return "unknown"

    # Response messages
    if message.get(b"y") == b"r":
        if b"values" in message.get(b"r", {}):
            return "get_peers_response"
        if b"nodes" in message.get(b"r", {}):
            return "find_node_response"
        if set(message.get(b"r", {}).keys()) <= {b"id", b"ip", b"p"}:
            return "ping_response"

        logging.debug("Unexpected response type: %r", message)
        return "unknown"

    # Error messages
    if message.get(b"y") == b"e":
        return "error"

    logging.debug("Unexpected message type: %r", message)
    return "unknown"


def get_node_id(message: dict) -> Optional[str]:
    """Extract DHT node ID from DHT message."""
    if b"a" in message:
        return message[b"a"][b"id"].hex()
    if b"r" in message:
        return message[b"r"][b"id"].hex()
    return None


def is_valid_node(node: Node, base_id: str) -> bool:
    """TBA"""
    if node.ip == "0.0.0.0":
        logging.debug("Invalid node, ip %s", node.ip)
        return False
    if node.port == 0 or node.port > 65535:
        logging.debug("Invalid node, port %s", node.port)
        return False
    if len(node.id) != 40:
        logging.debug("Invalid node, id %s", node.id)
        return False

    if node.id != base_id:
        node_distance = calculate_distance(node.id, base_id)
        if node_distance < 30:
            logging.debug("Invalid node, distance %s", node_distance)
            return False

    return True


def log_stats(*nodes):
    """TBA"""
    # Log the progress
    logging.info(
        "%s nodes, %s messages in, %s messages out",
        len(nodes),
        sum(node.counters["messages_in"].value for node in nodes),
        sum(node.counters["messages_out"].value for node in nodes),
    )

    # Reset counters
    for node in nodes:
        for counter in node.counters.values():
            counter.reset()


def parse_compact_node_info(data: bytes) -> List[Node]:
    """Convert compact node info string (BEP 5) to Node objects"""
    result_nodes = []
    for node_index in range(len(data) // 26):
        current_data = data[26 * node_index : 26 * (node_index + 1)]  # noqa
        _id, _ip, port = struct.unpack("!20s4sH", current_data)
        result_nodes.append(
            Node(id=_id.hex(), ip=str(ip_address(_ip)), port=port)
        )
    return result_nodes
