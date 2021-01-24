"""Tests for dht_node.py"""
# pylint: disable=protected-access
import logging
import time
from unittest.mock import Mock

import bencode
import pytest

from dht_node import DHTNode, dht_node, utils
from dht_node.data_structures import Node, Peer


class MockSocket:
    """Mock socket object, used in tests (only a few methods are supported)

    Args:
        messages - An optional list with received messages, they will be
        returned by "recvfrom" method one by one
    """

    def __init__(self, messages=None):
        """Called when the socket is created, sets its attributes"""
        self.closed = False
        self.messages = messages if messages else []
        self.sendto = Mock()

    def bind(self, *_args):
        """Noop"""

    def close(self):
        """Noop"""

    def recvfrom(self, *_args):
        """Return the predefined message and sender details. If there are no
        messages [left] - raise an OSError (timed out)
        """
        if self.messages:
            return self.messages.pop(), ("node_ip", 12345)

        raise OSError("timed out")

    def settimeout(self, *_args):
        """Noop"""


def test_add_message_handler(datadir, monkeypatch):
    """Try to add a message handler"""
    test_message = open(datadir["ping_request.krpc"], "rb").read()
    mock_socket = MockSocket(messages=[test_message])
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=mock_socket),
    )

    my_node = DHTNode(node_id="a" * 40)

    mock_handler = Mock()
    my_node.add_message_handler(mock_handler)

    my_node.start()
    time.sleep(1)
    my_node.stop()

    expected_message = {
        b"ip": b"b\x80\xb4n\xae\xfb",
        b"a": {b"id": b"2\xf5NisQ\xffJ\xec)\xcd\xba\xab\xf2\xfb\xe3F|\xc2g"},
        b"t": b"X\xd5\xe8w",
        b"q": b"ping",
        b"y": b"q",
    }
    expected_node = Node(
        id="32f54e697351ff4aec29cdbaabf2fbe3467cc267",
        ip="node_ip",
        port=12345,
    )
    mock_handler.assert_any_call(expected_message, expected_node)


def test_announce_peer_request(datadir, monkeypatch):
    """Try to process an incoming announce_peer message"""
    test_message = open(datadir["announce_peer_request.krpc"], "rb").read()
    info_hash = "8a02007babbfb08a7aeaffaf82902c948f679cfd"

    mock_socket = MockSocket(messages=[test_message])
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=mock_socket),
    )

    my_node = DHTNode(node_id="a" * 40)
    my_node.start()
    time.sleep(1)
    assert len(my_node._routing_table.get_peers(info_hash=info_hash)) == 1
    my_node.stop()

    expected_message = {
        b"t": b"\xc1a?\xcc;\xb1I\n",
        b"y": b"r",
        b"r": {b"id": bytes.fromhex("a" * 40)},
    }
    mock_socket.sendto.assert_any_call(
        bencode.encode(expected_message), ("node_ip", 12345)
    )


def test_blocked_node_too_close(monkeypatch):
    """Check that a node is blocked if it is too close"""
    invalid_node_id = "a" * 36 + "b" * 4
    test_message = bencode.encode(
        {
            b"a": {b"id": bytes.fromhex(invalid_node_id)},
            b"t": b"aa",
            b"q": b"ping",
            b"y": b"q",
        }
    )
    mock_socket = MockSocket(messages=[test_message])
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=mock_socket),
    )

    my_node = DHTNode(node_id="a" * 40)
    my_node.start()
    time.sleep(1)
    assert "node_ip" in my_node._blocked_ips
    my_node.stop()


def test_blocked_node_wrong_id(monkeypatch):
    """Check that a node is blocked if it has a wrong id"""
    invalid_node_id = "b" * 34
    test_message = bencode.encode(
        {
            b"a": {b"id": bytes.fromhex(invalid_node_id)},
            b"t": b"aa",
            b"q": b"ping",
            b"y": b"q",
        }
    )
    mock_socket = MockSocket(messages=[test_message])
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=mock_socket),
    )

    my_node = DHTNode(node_id="a" * 40)
    my_node.start()
    time.sleep(1)
    assert "node_ip" in my_node._blocked_ips
    my_node.stop()


def test_create_start_stop(capsys, monkeypatch):
    """Try to create/start/stop the node"""
    monkeypatch.setattr(
        dht_node.socket, "socket", Mock(return_value=MockSocket())
    )
    my_node = DHTNode()
    my_node.start()
    time.sleep(1)
    my_node.stop()
    time.sleep(1)
    assert "exception" not in capsys.readouterr().err.lower()


def test_find_node_request(datadir, monkeypatch):
    """Try to process an incoming find_node message"""
    test_message = open(datadir["find_node_request.krpc"], "rb").read()
    mock_socket = MockSocket(messages=[test_message])
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=mock_socket),
    )

    my_node = DHTNode(node_id="a" * 40)
    my_node.start()
    time.sleep(1)
    stored_node = my_node._routing_table.get_all_nodes()[0]
    my_node.stop()

    expected_message = {
        b"t": b"#\xca\xd1\xd1\xee\xab\x01\x03",
        b"y": b"r",
        b"r": {
            b"id": bytes.fromhex("a" * 40),
            b"nodes": stored_node.compact_info,
        },
    }
    mock_socket.sendto.assert_any_call(
        bencode.encode(expected_message), ("node_ip", 12345)
    )


def test_get_peers_request_absent(datadir, monkeypatch):
    """Try to process an incoming get_peers message (peers not found)"""
    test_message = open(datadir["get_peers_request.krpc"], "rb").read()
    mock_socket = MockSocket(messages=[test_message])
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=mock_socket),
    )

    my_node = DHTNode(node_id="a" * 40)
    my_node.start()
    time.sleep(1)
    stored_node = my_node._routing_table.get_all_nodes()[0]
    my_node.stop()

    expected_message = {
        b"t": b"\x9a*",
        b"y": b"r",
        b"r": {
            b"id": bytes.fromhex("a" * 40),
            b"nodes": stored_node.compact_info,
        },
    }
    mock_socket.sendto.assert_any_call(
        bencode.encode(expected_message), ("node_ip", 12345)
    )


def test_get_peers_request_present(datadir, monkeypatch):
    """Try to process an incoming get_peers message (peers found)"""
    test_message = open(datadir["get_peers_request.krpc"], "rb").read()
    mock_socket = MockSocket(messages=[test_message])
    monkeypatch.setattr(
        dht_node.os,
        "urandom",
        Mock(return_value=b"aa"),
    )
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=mock_socket),
    )

    my_node = DHTNode(node_id="a" * 40)
    other_node = Node(id="b" * 40, ip="other_ip", port=12345)
    other_peer = Peer(
        info_hash="861541c3faa16c9f52e1454a0b592bd308129c65",
        ip="peer_ip",
        port=23456,
    )
    my_node._routing_table.save_node(other_node)
    my_node._routing_table.save_peer(other_peer, other_node.id)
    my_node.start()
    time.sleep(1)
    my_node.stop()

    expected_message = {
        b"t": b"\x9a*",
        b"y": b"r",
        b"r": {
            b"id": bytes.fromhex("a" * 40),
            b"token": b"aa",
            b"values": [other_peer.compact_info],
        },
    }
    mock_socket.sendto.assert_any_call(
        bencode.encode(expected_message), ("node_ip", 12345)
    )


@pytest.mark.parametrize(
    "msg_name",
    [
        "announce_peer_request.krpc",
        "error.krpc",
        "find_node_request.krpc",
        "find_node_response.krpc",
        "get_peers_request.krpc",
        "ping_request.krpc",
        "ping_response.krpc",
        "vote.krpc",
    ],
)
def test_valid_messages(capsys, datadir, msg_name, monkeypatch):
    """Try to process some valid messages"""
    messages = [open(datadir[msg_name], "rb").read()]
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=MockSocket(messages=messages)),
    )

    my_node = DHTNode()
    my_node.start()
    time.sleep(1)
    my_node.stop()

    assert "exception" not in capsys.readouterr().err.lower()


@pytest.mark.parametrize(
    "msg_name,log_output",
    [
        ("invalid_message.krpc", "cannot decode"),
        ("unknown_request_type.krpc", "unexpected request type"),
        ("unknown_response_type.krpc", "unexpected response type"),
    ],
)
def test_invalid_messages(caplog, datadir, log_output, msg_name, monkeypatch):
    """Try to process some invalid messages"""
    caplog.set_level(logging.DEBUG)

    messages = [open(datadir[msg_name], "rb").read()]
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=MockSocket(messages=messages)),
    )

    my_node = DHTNode()
    my_node.start()
    time.sleep(1)
    my_node.stop()

    assert log_output in caplog.text.lower()


def test_log_stats(caplog, monkeypatch):
    """Try to log stats"""
    caplog.set_level(logging.INFO)

    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=MockSocket()),
    )

    my_node = DHTNode()
    my_node.start()
    time.sleep(1)
    utils.log_stats(my_node)
    my_node.stop()

    assert "1 nodes, 0 messages in, 1 messages out" in caplog.text


def test_ping_request(datadir, monkeypatch):
    """Try to process an incoming ping message"""
    test_message = open(datadir["ping_request.krpc"], "rb").read()
    mock_socket = MockSocket(messages=[test_message])
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=mock_socket),
    )

    my_node = DHTNode(node_id="a" * 40)
    my_node.start()
    time.sleep(1)
    my_node.stop()

    expected_message = {
        b"t": b"X\xd5\xe8w",
        b"y": b"r",
        b"r": {b"id": bytes.fromhex("a" * 40)},
    }
    mock_socket.sendto.assert_any_call(
        bencode.encode(expected_message), ("node_ip", 12345)
    )


def test_send_message(monkeypatch):
    """Try to send a message"""
    mock_socket = MockSocket()
    monkeypatch.setattr(
        dht_node.socket,
        "socket",
        Mock(return_value=mock_socket),
    )

    ping_message = {
        b"a": {b"id": bytes.fromhex("a" * 40)},
        b"t": b"aa",
        b"q": b"ping",
        b"y": b"q",
    }

    my_node = DHTNode(node_id="a" * 40)
    my_node.start()
    my_node.send_message(ping_message, node_ip="other_ip", node_port=5555)
    time.sleep(1)
    my_node.stop()

    mock_socket.sendto.assert_any_call(
        bencode.encode(ping_message), ("other_ip", 5555)
    )
