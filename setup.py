"""Setup file, used for building a Python package."""
from setuptools import setup

with open("README.md", "r") as desc_file:
    long_description = desc_file.read()

setup(
    install_requires=["cachetools", "modern-bencode"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    name="simple-dht-node",
    packages=["dht_node"],
    package_data={"dht_node": ["py.typed"]},
    python_requires=">=3.7",
    setup_requires=["setuptools_scm"],
    url="https://github.com/retonato/simple-dht-node",
    use_scm_version=True,
)
