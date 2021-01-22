"""Setup file, used for building a Python package."""
from setuptools import setup

setup(
    install_requires=["cachetools", "modern-bencode"],
    name="simple-dht-node",
    packages=["dht_node"],
    package_data={"dht_node": ["py.typed"]},
    python_requires=">=3.7",
    version="1.0.0",
)
