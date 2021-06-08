# Simple Bittorrent DHT node

A simple Bittorrent DHT node. I use it primarily for getting information from the DHT network, but it can be used for any related purpose. Just works.

## Installation
```
pip install simple-dht-node
```
The library requires Python >= 3.7

## Usage

Minimal working code (start a single DHT node with a random ID on a random port in 1025-65535 range, then stop it):

```python
from dht_node import DHTNode

my_node = DHTNode()
my_node.start()
my_node.stop()
```

You can specify an existing node ID (40 character hex string) and some port:

```python
from dht_node import DHTNode

my_node = DHTNode(
    node_id="cabda53168171c05adbbf1af50ebbe097a482850",
    node_port=15000
)
my_node.start()
my_node.stop()
```

You can start multiple nodes (a regular virtual server with 1 CPU and 1GB RAM can handle up to 25-50 nodes):

```python
from dht_node import DHTNode

my_nodes = []
for _ in range(5):
    node = DHTNode()
    node.start()
    my_nodes.append(node)

for node in my_nodes:
    node.stop()
```

You can log node statistics (number of active nodes, number of incoming messages, number of outgoing messages). Message number is set to 0 on each function call (so, if you call it every minute - you will receive data for the last minute, every 5 minutes - for the last 5 minutes, and so on):

```python
import logging
import time
from dht_node import DHTNode, utils

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)

my_node = DHTNode()
my_node.start()

for _ in range(5):
    utils.log_stats(my_node)  # or utils.log_stats(*my_nodes)
    time.sleep(60)

my_node.stop()
```

You can add one or more message handlers (for example to save some information from the messages). Those functions will be called on each incoming message (get 2 arguments, message and a sender node info):

```python
import time
from dht_node import DHTNode
from dht_node.data_structures import Node

def my_handler(message: dict, sending_node: Node):
    print(message)
    print(sending_node)

my_node = DHTNode()
my_node.add_message_handler(my_handler)
my_node.start()
time.sleep(30)
my_node.stop()
```

Finally, you can send messages (check [the source code](https://github.com/retonato/simple-dht-node/blob/master/dht_node/dht_node.py) and [BEP5](http://bittorrent.org/beps/bep_0005.html) for message format and examples):

```python
import os
from dht_node import DHTNode

my_node = DHTNode()
my_node.start()
my_node.send_message(
    message={
        b"t": os.urandom(2),  # message token
        b"y": b"q",  # message type (query)
        b"q": b"ping",  # query name (ping)
        b"a": {b"id": bytes.fromhex(my_node.id)},
    },
    node_ip="67.215.246.10",  # router.bittorrent.com
    node_port=6881,
)
my_node.stop()
```

## Common problems

Usually it takes up to 15-30 minutes for node to start receiving a stable stream of messages from other DHT nodes (that's just how DHT network works, it takes some time for other nodes to get information about your node).

It might take an additional day or so until the node is up-to-speed (=most nearby nodes in the DHT network have its info in their routing tables). You can expect a few hundred incoming messages per minute for each node.

If you started the node and there are no incoming messages at all - other nodes cannot reach you, you are either behind NAT or a firewall. If you are behind NAT - you need to enable port forwarding on your router. If you have a firewall enabled - you need to allow your node UDP port there.

## Bugs

Feel free to create an issue [here](https://github.com/retonato/simple-dht-node/issues) if you find a bug or some error message is not clear enough.