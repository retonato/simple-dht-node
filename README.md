# Simple Bittorent DHT node

A simple Bittorent DHT node.

## Installation
```
pip install simple-dht-node
```
The library requires Python >= 3.7

## Usage
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
    utils.log_stats(my_node)
    time.sleep(60)

my_node.stop()
```

## Bugs

Feel free to create an issue [here](https://github.com/retonato/simple-dht-node/issues)
if you find a bug or some error message is not clear enough.