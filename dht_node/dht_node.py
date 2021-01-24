"""Simple DHT node"""
import logging
import os
import random
import secrets
import socket
import threading
import time
from datetime import datetime
from typing import Callable, List, Optional

# noinspection PyPackageRequirements
import bencode
from cachetools import TTLCache

from dht_node import utils
from dht_node.data_structures import Counter, Node, Peer
from dht_node.routing_table import RoutingTable


class DHTNode:
    """Simple DHT node"""

    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        node_id: Optional[str] = None,  # hex
        node_port: Optional[int] = None,  # int
    ):
        """Called when the node is created, sets its attributes"""
        self.counters = {"messages_in": Counter(), "messages_out": Counter()}
        self.id = node_id or secrets.token_hex(20)  # pylint: disable=C0103
        self.port = node_port or random.randint(1025, 65535)

        self._blocked_ips: TTLCache = TTLCache(maxsize=1000, ttl=3600 * 24)
        self._handlers = {
            "all": (self._save_node,),
            "announce_peer_request": [self._on_announce_peer_request],
            "announce_peer_response": [],  # we don't expect responses here
            "error": [],  # no action here
            "find_node_request": [self._on_find_node_request],
            "find_node_response": [self._on_find_node_response],
            "get_peers_request": [self._on_get_peers_request],
            "get_peers_response": [],  # we don't expect responses here
            "ping_request": [self._on_ping_request],
            "ping_response": [],  # no action here
            "sample_infohashes": [],  # no action here
            "unknown": [],  # no action here
            "vote": [],  # no action here
        }
        self._lock = threading.Lock()
        self._routing_table = RoutingTable(base_id=self.id)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._stop_requested = threading.Event()
        self._threads: List[threading.Thread] = []

    def _process_messages(self):
        """Function, which processes incoming messages"""
        while not self._stop_requested.is_set():
            # Receive a new message from the socket
            try:
                msg_raw, (node_ip, node_port) = self._socket.recvfrom(65535)
                self.counters["messages_in"].increment()
            except OSError as err:
                if "timed out" not in str(err):
                    logging.error("Cannot receive message, error: %s", err)
                continue

            # Skip messages from blocked IPs
            if node_ip in self._blocked_ips:
                logging.debug("Ignoring message from blocked IP %s", node_ip)
                continue

            # Try to decode it
            try:
                message = bencode.decode(msg_raw)
            except ValueError as err:
                logging.debug(err)
                continue

            # Get the message type
            msg_type = utils.get_message_type(message)

            # Create a node object
            node_id = utils.get_node_id(message)
            if node_id:
                node = Node(node_id, node_ip, node_port)
            else:
                continue

            # Skip messages from invalid nodes
            if not utils.is_valid_node(node, self.id):
                self._blocked_ips[node.ip] = datetime.now()
                continue

            # Process the message
            for fn_ in [*self._handlers["all"], *self._handlers[msg_type]]:
                try:
                    fn_(message, node)
                except Exception as err:  # pylint: disable=broad-except
                    logging.debug(
                        "Cannot process message %r, error: %s",
                        message,
                        err,
                    )
                    continue

        # Close the socket
        self._socket.close()

    # Message handlers
    def _on_announce_peer_request(self, message: dict, node: Node):
        """TBA"""
        # Save peer to the routing table
        if message[b"a"].get(b"implied_port", 0):
            port = node.port
        else:
            port = message[b"a"][b"port"]

        self._routing_table.save_peer(
            Peer(
                info_hash=message[b"a"][b"info_hash"].hex(),
                ip=node.ip,
                port=port,
            ),
            node.id,
        )

        # Prepare and send the response
        self.send_message(
            {
                b"t": message[b"t"],
                b"y": b"r",
                b"r": {b"id": bytes.fromhex(self.id)},
            },
            node.ip,
            node.port,
        )

    def _on_get_peers_request(self, message: dict, node: Node):
        """TBA"""
        # Prepare and send the response
        peers = self._routing_table.get_peers(
            message[b"a"][b"info_hash"].hex()
        )
        if peers:
            self.send_message(
                {
                    b"t": message[b"t"],
                    b"y": b"r",
                    b"r": {
                        b"id": bytes.fromhex(self.id),
                        b"token": os.urandom(2),
                        b"values": [peer.compact_info for peer in peers],
                    },
                },
                node.ip,
                node.port,
            )
        else:
            # Just send the closest nodes
            closest_nodes = self._routing_table.get_closest_nodes(
                message[b"a"][b"info_hash"].hex()
            )
            self.send_message(
                {
                    b"t": message[b"t"],
                    b"y": b"r",
                    b"r": {
                        b"id": bytes.fromhex(self.id),
                        b"nodes": utils.create_compact_node_info(
                            closest_nodes
                        ),
                    },
                },
                node.ip,
                node.port,
            )

    def _on_find_node_request(self, message: dict, node: Node):
        """TBA"""
        # Prepare and send the response
        closest_nodes = self._routing_table.get_closest_nodes(
            message[b"a"][b"target"].hex()
        )
        self.send_message(
            {
                b"t": message[b"t"],
                b"y": b"r",
                b"r": {
                    b"id": bytes.fromhex(self.id),
                    b"nodes": utils.create_compact_node_info(closest_nodes),
                },
            },
            node.ip,
            node.port,
        )

    def _on_find_node_response(self, message: dict, _node: Node):
        """TBA"""
        for node in utils.parse_compact_node_info(message[b"r"][b"nodes"]):
            # Skip invalid nodes
            if not utils.is_valid_node(node, self.id):
                self._blocked_ips[node.ip] = datetime.now()
                continue

            # Add found node to the routing table
            self._routing_table.save_node(node)

    def _on_ping_request(self, message: dict, node: Node):
        """TBA"""
        # Prepare and send the response
        self.send_message(
            {
                b"t": message[b"t"],
                b"y": b"r",
                b"r": {b"id": bytes.fromhex(self.id)},
            },
            node.ip,
            node.port,
        )

    # Other
    def _maintain_routing_table(self):
        # Bootstrapping
        if not self._routing_table.get_all_nodes():
            self._routing_table.save_node(
                Node(
                    id="32f54e697351ff4aec29cdbaabf2fbe3467cc267",
                    ip="67.215.246.10",  # router.bittorrent.com
                    port=6881,
                )
            )

            # Send "find_node" requests to the closest nodes (10 times)
            for _ in range(10):
                if not self._stop_requested.is_set():
                    for node in self._routing_table.get_closest_nodes(self.id):
                        self.send_message(
                            {
                                b"t": os.urandom(2),
                                b"y": b"q",
                                b"q": b"find_node",
                                b"a": {
                                    b"id": bytes.fromhex(self.id),
                                    b"target": bytes.fromhex(self.id),
                                },
                            },
                            node.ip,
                            node.port,
                        )
                    self._stop_requested.wait(5)

        # Maintaining
        while not self._stop_requested.is_set():
            self._ping_questionable_nodes()
            self._routing_table.delete_unresponsive_nodes()
            self._stop_requested.wait(300)

    def _ping_questionable_nodes(self):
        """Send ping requests to all questionable nodes"""
        for node in self._routing_table.get_all_nodes():
            if node.is_questionable:
                self.send_message(
                    {
                        b"t": os.urandom(2),
                        b"y": b"q",
                        b"q": b"ping",
                        b"a": {b"id": bytes.fromhex(self.id)},
                    },
                    node.ip,
                    node.port,
                )

    def _save_node(self, _message: dict, node: Node):
        """TBA"""
        self._routing_table.save_node(node, communicated=datetime.now())

    # Public methods
    def add_message_handler(self, fn_: Callable) -> None:
        """TBA"""
        self._handlers["all"] = self._handlers["all"] + (fn_,)  # type: ignore

    def send_message(self, message: dict, node_ip: str, node_port: int):
        """TBA"""
        with self._lock:
            try:
                self._socket.sendto(
                    bencode.encode(message), (node_ip, node_port)
                )
                self.counters["messages_out"].increment()
            except (OSError, ValueError) as err:
                logging.error(
                    "Cannot send message %r to %s, error: %s",
                    message,
                    (node_ip, node_port),
                    err,
                )

    def start(self):
        """Start DHT node"""
        # Bind a socket
        logging.info("Starting node %s at port %s", self.id, self.port)
        self._socket.settimeout(1)
        self._socket.bind(("0.0.0.0", self.port))

        # Start a message processor
        pm_thread = threading.Thread(target=self._process_messages)
        self._threads.append(pm_thread)
        pm_thread.start()

        # Create and maintain a routing table
        mrt_thread = threading.Thread(target=self._maintain_routing_table)
        self._threads.append(mrt_thread)
        mrt_thread.start()

    def stop(self):
        """Stop DHT node"""
        # Notify all threads that they should finish
        logging.info("SIGINT received, stopping node %s", self.id)
        self._stop_requested.set()

        # Wait for all threads to finish
        while [t for t in self._threads if t.is_alive()]:
            logging.info("Waiting for node %s to finish", self.id)
            time.sleep(1)
