"""Tests for routing_table.py"""
from datetime import datetime, timedelta

from dht_node.data_structures import Node, Peer
from dht_node.routing_table import RoutingTable


def test_delete_unresponsive_nodes():
    """Test is_questionable and is_unresponsive node properties"""
    table = RoutingTable(base_id="abcd" + "0" * 36)
    node = Node(id="1234" + "0".zfill(36), ip="test_ip", port=1)

    # Newly added node should not be treated as questionable or unresponsive
    # (even though there is no communication time yet)
    table.save_node(node)
    table.delete_unresponsive_nodes()
    stored_node = table.get_all_nodes()[0]
    assert not stored_node.is_questionable
    assert not stored_node.is_unresponsive

    # The communication time is updated, it is less than 5 minutes ago
    time_minus_1 = datetime.now() - timedelta(minutes=1)
    table.save_node(node, communicated=time_minus_1)
    table.delete_unresponsive_nodes()
    stored_node = table.get_all_nodes()[0]
    assert not stored_node.is_questionable
    assert not stored_node.is_unresponsive

    # The communication time is updated, it is between 5 and 15 minutes ago
    time_minus_10 = datetime.now() - timedelta(minutes=10)
    table.save_node(node, communicated=time_minus_10)
    table.delete_unresponsive_nodes()
    stored_node = table.get_all_nodes()[0]
    assert stored_node.is_questionable
    assert not stored_node.is_unresponsive

    # The communication time is updated, it is more than 15 minutes ago
    time_minus_20 = datetime.now() - timedelta(minutes=20)
    table.save_node(node, communicated=time_minus_20)
    table.delete_unresponsive_nodes()
    assert len(table.get_all_nodes()) == 0


def test_get_closest_nodes():
    """Try to get closest nodes"""
    table = RoutingTable(base_id="abcd" + "0" * 36)

    # Add close nodes
    for i in range(7):
        table.save_node(
            Node(id="7777" + str(i).zfill(36), ip="test_ip", port=1)
        )

    # Add distant nodes
    for i in range(512):
        table.save_node(
            Node(id="0000" + str(i).zfill(36), ip="test_ip", port=1)
        )

    found_nodes = table.get_closest_nodes("7777" + "0" * 36)
    assert len(found_nodes) == 7
    assert [node.id.startswith("7777") for node in found_nodes]


def test_save_node_base():
    """Saving base node should not be possible"""
    # Create a routing table and add node with the same id as the base node
    table = RoutingTable(base_id="abcd" + "0" * 36)
    table.save_node(Node(id="abcd" + "0" * 36, ip="test_ip", port=1))

    # There should be no nodes in the routing table
    assert len(table.get_all_nodes()) == 0


def test_save_node_min():
    """Test saving node when the routing table is empty or small"""
    # Create a routing table and add 7 distant nodes to it
    table = RoutingTable(base_id="abcd" + "0" * 36)
    for i in range(7):
        table.save_node(Node(id="0000" + str(i) * 36, ip="test_ip", port=1))

    # There should be 7 nodes in the routing table
    assert len(table.get_all_nodes()) == 7

    # Try to add one more distant node to it
    table.save_node(Node(id="0000" + "a" * 36, ip="test_ip", port=1))

    # There should still be 7 nodes there
    assert len(table.get_all_nodes()) == 7


def test_save_node_max():
    """Test saving node when the routing table is large"""
    # Create a routing table and add 512 close nodes to it
    table = RoutingTable(base_id="abcd" + "a" * 36)
    for i in range(512):
        table.save_node(
            Node(id="abcd" + str(i).zfill(36), ip="test_ip", port=1)
        )

    # There should be 512 nodes in the routing table
    assert len(table.get_all_nodes()) == 512

    # Try to add one more distant node to it
    table.save_node(Node(id="1234" + "a" * 36, ip="test_ip", port=1))

    # There should still be 512 nodes there
    assert len(table.get_all_nodes()) == 512


def test_save_peer():
    """Test saving peer"""
    table = RoutingTable(base_id="abcd" + "0" * 36)

    node_id_1 = "1234" + "0".zfill(36)
    table.save_node(Node(id=node_id_1, ip="test_ip", port=1))

    node_id_2 = "5678" + "0".zfill(36)
    table.save_node(Node(id=node_id_2, ip="test_ip", port=1))

    peer_1 = Peer(info_hash="test_hash_1", ip="test", port=1)
    peer_2 = Peer(info_hash="test_hash_2", ip="test", port=1)
    table.save_peer(peer_1, node_id_2)
    table.save_peer(peer_1, node_id_2)
    table.save_peer(peer_2, node_id_2)
    table.save_peer(peer_2, "missing_node")

    for node in table.get_all_nodes():
        if node.id == node_id_2:
            assert len(node.peers) == 2

    assert table.get_peers("test_hash_1") == [peer_1]
