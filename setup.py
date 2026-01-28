#!/usr/bin/env python3
"""Setup script for signal-export."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="signal-export",
    version="2.0.0",
    description="Export Signal chats to Markdown/HTML with attachments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Chris Arderne, Liroy van Hoewijk, and contributors",
    url="https://github.com/liroyvh/signal-export",
    py_modules=["sigexport"],
    python_requires=">=3.9",
    install_requires=[
        "beautifulsoup4>=4.14",
        "Click>=8.3",
        "Markdown>=3.10",
        "sqlcipher3>=0.5.3",
    ],
    entry_points={
        "console_scripts": [
            "signal-export=sigexport:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
