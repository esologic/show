"""Use this file to install devon_bray_portfolio as a module"""

from distutils.core import setup
from setuptools import find_packages
from typing import List


def prod_dependencies() -> List[str]:
    """
    Pull the dependencies from the requirements dir
    :return: Each of the newlines, strings of the dependencies
    """
    with open("./requirements/prod.txt", "r") as file:
        return file.read().splitlines()


setup(
    name="devon_bray_portfolio",
    version="1.0.1",
    description="Contains the content and server code that makes up my portfolio.",
    author="Devon Bray",
    author_email="dev@esologic.com",
    packages=find_packages(),
    install_requires=prod_dependencies(),
)
